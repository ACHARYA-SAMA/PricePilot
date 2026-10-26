"""API acceptance checks use actual engines and inspect exported files."""
import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def observations(n=20):
    return [dict(event_id=f'E{i}', ticket_price=50 + i * 5,
                 tickets_sold=500 - 2 * (50 + i * 5)) for i in range(n)]


def test_health_and_sample_workflow():
    assert client.get('/api/v1/health').json()['status'] == 'ok'
    catalog = client.get('/api/v1/sample-datasets').json()
    assert len(catalog) >= 3
    sample = client.get('/api/v1/sample-datasets/' + catalog[0]['id']).json()
    rows = sample['rows']
    assert len(rows) == catalog[0]['n_rows']
    result = client.post('/api/v1/regression/fit', json={'observations': rows})
    assert result.status_code == 200, result.text
    assert result.json()['linear']['n_samples'] == len(rows)


@pytest.mark.parametrize('field,value', [('ticket_price', 0), ('tickets_sold', -1),
    ('tickets_sold', 1.5), ('ticket_price', 'NaN'), ('tickets_sold', 'Infinity'),
    ('venue_capacity', -3), ('event_id', '   ')])
def test_invalid_observations_rejected_on_every_calculation(field, value):
    rows = observations()
    rows[0][field] = value
    for endpoint, extra in [('/regression/fit', {}), ('/optimization/run', {}),
                            ('/scenarios/evaluate', {'prices': [125]})]:
        response = client.post('/api/v1' + endpoint, json={'observations': rows, **extra})
        assert response.status_code == 422, (endpoint, field, response.text)


def test_constant_prices_not_recommended_and_cannot_optimize():
    rows = [dict(event_id=str(i), ticket_price=100, tickets_sold=100+i) for i in range(8)]
    fit = client.post('/api/v1/regression/fit', json={'observations': rows})
    assert fit.status_code == 422 or fit.json()['recommended_model'] == 'none'
    assert client.post('/api/v1/optimization/run', json={'observations': rows}).status_code == 422


def test_reference_optimizer_and_scenario():
    body = {'observations': observations(), 'p_min': 50, 'p_max': 240}
    response = client.post('/api/v1/optimization/run', json=body)
    assert response.status_code == 200, response.text
    optimum = response.json()
    assert optimum['optimal_price'] == pytest.approx(125)
    assert optimum['optimal_realized_demand'] == pytest.approx(250)
    assert optimum['optimal_realized_revenue'] == pytest.approx(31250)
    sim = client.post('/api/v1/scenarios/evaluate', json={
        'observations': observations(), 'prices': [100, 125], 'baseline_price': 100}).json()
    assert sim['scenarios'][1]['realized_revenue'] == pytest.approx(31250)
    assert sim['scenarios'][1]['revenue_vs_baseline'] == pytest.approx(1250)


@pytest.mark.parametrize('extra', [{'p_min': 200, 'p_max': 100},
    {'p_min': 'Infinity'}, {'capacity': 'NaN'}, {'price_increment': 0}, {'p0': 'Infinity'}])
def test_bad_optimization_configuration(extra):
    assert client.post('/api/v1/optimization/run', json={
        'observations': observations(), **extra}).status_code == 422


def test_bad_scenario_price():
    for prices in [[], [-5], ['NaN'], ['Infinity']]:
        assert client.post('/api/v1/scenarios/evaluate', json={
            'observations': observations(), 'prices': prices}).status_code == 422


def test_csv_validation_mapping_and_recovery():
    content = 'identifier,fee,count\nA,100,300\nB,-1,200\nC,125,250\nD,150,200\n'
    response = client.post('/api/v1/datasets/validate',
        files={'file': ('records.csv', content, 'text/csv')},
        data={'column_mapping': json.dumps({'identifier':'event_id','fee':'ticket_price','count':'tickets_sold'})})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['valid_rows'] == 3
    assert result['rejected_rows'] == 1
    assert result['valid_rows_data'][0]['observed_revenue'] == 30000
    assert result['issues']
    assert client.post('/api/v1/datasets/validate', files={'file':('bad.txt',content)}).status_code == 400


def test_prediction_csv_contains_all_rows_with_correct_residuals():
    response = client.post('/api/v1/exports/predictions-csv', json={'observations':observations()})
    assert response.status_code == 200, response.text
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 20
    for row in rows:
        assert float(row['linear_predicted']) == pytest.approx(float(row['actual_demand']))
        assert float(row['linear_residual']) == pytest.approx(0, abs=1e-8)


def test_analysis_export_preserves_active_configuration():
    body = {'observations': observations(), 'model_type':'linear', 'p_min':60,
            'p_max':110, 'capacity':200, 'dataset_name':'Synthetic reference', 'is_synthetic':True}
    response = client.post('/api/v1/exports/analysis-json', json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['configuration']['p_max'] == 110
    assert result['configuration']['capacity'] == 200
    assert result['optimization']['optimal_price'] == pytest.approx(110)
    assert result['optimization']['optimal_realized_revenue'] == pytest.approx(22000)
    assert len(result['observations']) == 20
    assert result['provenance']['is_synthetic'] is True


def test_clean_csv_escapes_formula_text_and_retains_metadata():
    rows = observations()
    rows[0].update(event_id='=SUM(1,2)', event_category='Music', event_name='<Event>')
    response = client.post('/api/v1/exports/cleaned-csv', json={'observations': rows})
    assert response.status_code == 200
    result = list(csv.DictReader(io.StringIO(response.text)))
    assert result[0]['event_id'].startswith("'=")
    assert result[0]['event_category'] == 'Music'
    assert float(result[0]['observed_revenue']) == 20000


def test_pdf_and_chart_are_actual_files():
    body = {'observations': observations(), 'p_min':60, 'p_max':110, 'capacity':200,
            'model_type':'linear', 'dataset_name':'A < B & C', 'is_synthetic':True}
    pdf = client.post('/api/v1/reports/pdf', json=body)
    assert pdf.status_code == 200, pdf.text[:500]
    assert pdf.content.startswith(b'%PDF-')
    assert len(pdf.content) > 8000
    chart = client.post('/api/v1/exports/chart-svg', json=body)
    assert chart.status_code == 200
    assert '<svg' in chart.text
    assert 'Revenue' in chart.text


def test_untrusted_cors_origin_is_not_allowed():
    response = client.get('/api/v1/health', headers={'Origin':'https://untrusted.example'})
    assert response.headers.get('access-control-allow-origin') is None


def test_raw_nonfinite_json_returns_validation_error_without_server_failure():
    response = client.post('/api/v1/regression/fit', content='{"observations":[{"event_id":"A","ticket_price":NaN,"tickets_sold":2},{"event_id":"B","ticket_price":1,"tickets_sold":3}]}', headers={'Content-Type':'application/json'})
    assert response.status_code == 422
    assert 'detail' in response.json()


def test_valid_and_rejected_rows_retain_original_csv_positions():
    text = 'event_id,ticket_price,tickets_sold\nA,100,20\nB,0,30\nC,150,10\nD,200,0\n'
    result = client.post('/api/v1/datasets/validate', files={'file':('order.csv',text,'text/csv')}).json()
    assert [row['_source_row'] for row in result['valid_rows_data']] == [2,4,5]
    assert result['rejected_rows_data'][0]['_source_row'] == 3
