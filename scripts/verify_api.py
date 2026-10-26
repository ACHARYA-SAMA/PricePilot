"""Execute API acceptance flow and save inspectable numerical/export artifacts."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from fastapi.testclient import TestClient
from app.main import app


def main():
    out = ROOT / 'output' / 'verification'
    out.mkdir(parents=True, exist_ok=True)
    client = TestClient(app)
    sample = client.get('/api/v1/sample-datasets/standard').json()
    rows = sample['rows']
    fit_response = client.post('/api/v1/regression/fit', json={'observations': rows})
    fit_response.raise_for_status()
    fit = fit_response.json()
    model = fit['recommended_model']
    body = dict(observations=rows, model_type=model,
                p_min=50, p_max=170, capacity=800,
                dataset_name=sample['name'], is_synthetic=True)
    optimization = client.post('/api/v1/optimization/run', json=body)
    optimization.raise_for_status()
    opt = optimization.json()
    assert 50 <= opt['optimal_price'] <= 170
    assert opt['optimal_realized_demand'] <= 800
    assert opt['scan_agrees']
    for endpoint, filename in [('reports/pdf','sample-report.pdf'),
        ('exports/analysis-json','sample-analysis.json'),
        ('exports/predictions-csv','sample-predictions.csv'),
        ('exports/cleaned-csv','sample-cleaned.csv'),
        ('exports/chart-svg','sample-curves.svg')]:
        response = client.post('/api/v1/' + endpoint, json=body)
        response.raise_for_status()
        (out / filename).write_bytes(response.content)
    reference = [dict(event_id=str(i),ticket_price=p,tickets_sold=500-2*p)
                 for i,p in enumerate(range(50,201,10))]
    response = client.post('/api/v1/optimization/run', json={
        'observations':reference,'p_min':50,'p_max':240})
    response.raise_for_status()
    exact = response.json()
    for key, expected in [('optimal_price',125),('optimal_realized_demand',250),
                           ('optimal_realized_revenue',31250)]:
        assert abs(exact[key]-expected) < 1e-7, (key,exact[key])
    summary = dict(sample_rows=len(rows), recommended_model=model,
        coefficients={k:fit[model][k] for k in ('a','b','c')},
        full_data_rmse=fit[model]['rmse'],
        holdout_rmse=fit[model+'_val']['rmse'],
        optimization=opt, linear_reference=exact,
        artifacts=[p.name for p in out.iterdir() if p.is_file()])
    (out/'api-evidence.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('optimization','linear_reference')},indent=2))
    print('Standard optimum:', opt['optimal_price'], opt['optimal_realized_revenue'])
    print('Linear reference:', exact['optimal_price'],exact['optimal_realized_demand'],exact['optimal_realized_revenue'])
    print('Artifacts:',out)


if __name__ == '__main__':
    main()
