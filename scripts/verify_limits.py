"""Execute the documented upload/row limits; timings are observations, not benchmarks."""
import io
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
records = [dict(event_id=str(i),ticket_price=50+i%191,tickets_sold=500-2*(50+i%191)) for i in range(10000)]
text = 'event_id,ticket_price,tickets_sold\n' + '\n'.join(f"{r['event_id']},{r['ticket_price']},{r['tickets_sold']}" for r in records)
start = time.perf_counter()
validation = client.post('/api/v1/datasets/validate',files={'file':('limit.csv',text,'text/csv')})
validation.raise_for_status()
assert validation.json()['valid_rows'] == 10000
validation_seconds = time.perf_counter()-start
start = time.perf_counter()
regression = client.post('/api/v1/regression/fit',json={'observations':records})
regression.raise_for_status()
assert regression.json()['linear']['n_samples'] == 10000
regression_seconds = time.perf_counter()-start
too_many = client.post('/api/v1/regression/fit',json={'observations':records+[records[0]]})
assert too_many.status_code == 422
large = client.post('/api/v1/datasets/validate',files={'file':('large.csv',b'x'*(5*1024*1024+1),'text/csv')})
large.raise_for_status()
assert large.json()['valid_rows']==0
assert any('limit' in issue['message'].lower() for issue in large.json()['issues'])
result = dict(rows=10000,validation_seconds=validation_seconds,regression_seconds=regression_seconds,
    row_overflow_status=too_many.status_code,file_overflow_issues=large.json()['issues'],
    note='One local TestClient run, not a general performance benchmark or load test.')
out = ROOT/'output/verification/limits-evidence.json'
out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
