"""Additional specification contracts for diagnostics and scenario exports."""
import csv
import io

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def rows():
    return [dict(event_id=str(i), ticket_price=p, tickets_sold=500-2*p)
            for i,p in enumerate(range(50,201,10))]


def test_hypothetical_multiplier_and_difference_are_computed_backend():
    response = client.post('/api/v1/scenarios/evaluate',json={
        'observations':rows(),'prices':[100,125],'baseline_price':100,
        'recommended_price':125,'demand_multiplier':1.2})
    assert response.status_code == 200,response.text
    point = response.json()['scenarios'][1]
    assert point['predicted_demand'] == pytest.approx(300)
    assert point['realized_revenue'] == pytest.approx(37500)
    assert point['revenue_vs_baseline'] == pytest.approx(1500)
    assert point['difference_from_recommended_price'] == pytest.approx(0)
    assert 'hypothetical' in point['notes'].lower()


def test_diagnostics_supply_actual_histogram_and_diagonal():
    response = client.post('/api/v1/diagnostics/evaluate',json={'observations':rows(),'model_type':'linear'})
    assert response.status_code == 200,response.text
    result = response.json()
    assert len(result['actual_vs_predicted']) == 16
    assert sum(b['count'] for b in result['histogram']) == 16
    assert len(result['diagonal']) == 2
    assert all(p['actual'] == pytest.approx(p['predicted']) for p in result['actual_vs_predicted'])


@pytest.mark.parametrize('kind', ['residuals-csv','scenarios-csv','chart-png'])
def test_additional_exports_are_real_and_consistent(kind):
    response = client.post('/api/v1/exports/'+kind,json={
        'observations':rows(),'model_type':'linear','p_min':50,'p_max':200,
        'scenario_prices':[100,125,150],'demand_multiplier':1.2})
    assert response.status_code == 200,response.text[:200]
    if kind == 'chart-png':
        assert response.content.startswith(b'\x89PNG\r\n\x1a\n')
        return
    result = list(csv.DictReader(io.StringIO(response.text)))
    if kind == 'residuals-csv':
        assert len(result) == 16
        assert all(float(row['linear_residual']) == pytest.approx(0,abs=1e-8) for row in result)
    else:
        assert len(result) == 3
        assert float(result[1]['price']) == 125
        assert float(result[1]['realized_revenue']) == pytest.approx(37500)


def test_grouped_holdout_has_no_event_leakage():
    records = [dict(event_id=f'G{i//4}',ticket_price=50+i%4*20+i//4,tickets_sold=500-2*(50+i%4*20+i//4)) for i in range(40)]
    response = client.post('/api/v1/regression/fit',json={'observations':records})
    assert response.status_code == 200,response.text
    result = response.json()
    assert result['split_strategy'] == 'random_groups'
    train = {records[i]['event_id'] for i in result['train_indices']}
    validation = {records[i]['event_id'] for i in result['val_indices']}
    assert not train.intersection(validation)
