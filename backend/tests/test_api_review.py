"""Independent review regressions for truthful evidence and mapping recovery."""
import json

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def constant_sales():
    return [dict(event_id=str(i), ticket_price=50+i*10, tickets_sold=300) for i in range(20)]


def test_undefined_newton_division_is_null_in_api_and_export():
    payload = dict(observations=constant_sales(), model_type="linear", p_min=50, p_max=200)
    response = client.post("/api/v1/optimization/run", json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["newton_status"] == "failed_zero_derivative"
    assert not result["newton_converged"]
    assert result["iterations"][0]["correction"] is None
    assert result["iterations"][0]["next_price"] is None
    assert result["iterations"][0]["abs_error"] is None
    exported = client.post("/api/v1/exports/analysis-json", json=payload)
    assert exported.status_code == 200, exported.text
    assert exported.json()["optimization"]["iterations"][0]["next_price"] is None


def test_explicit_mapping_resolves_an_ambiguous_alias_without_renaming_other_columns():
    content = "event,price,cost,sales\nA,100,30,300\nB,125,30,250\nC,150,30,200\n"
    result = client.post("/api/v1/datasets/validate",
        files={"file": ("sales.csv", content, "text/csv")},
        data={"column_mapping": json.dumps({"event":"event_id", "price":"ticket_price", "sales":"tickets_sold"})})
    assert result.status_code == 200, result.text
    assert result.json()["valid_rows"] == 3
    assert not any(i["code"] == "AMBIGUOUS_COLUMN" for i in result.json()["issues"])


def test_rejected_rows_preserve_source_row_and_only_their_own_errors():
    content = "event_id,ticket_price,tickets_sold\nA,100,300\nB,-5,250\nC,150,1.5\n"
    response = client.post("/api/v1/datasets/validate",
        files={"file": ("sales.csv", content, "text/csv")})
    assert response.status_code == 200, response.text
    rejected = response.json()["rejected_rows_data"]
    assert [r["_source_row"] for r in rejected] == [3, 4]
    assert "ticket_price" in rejected[0]["_errors"]
    assert "tickets_sold" not in rejected[0]["_errors"]
    assert "tickets_sold" in rejected[1]["_errors"]
    assert "ticket_price" not in rejected[1]["_errors"]


def test_raw_json_nan_is_rejected_with_json_error_instead_of_server_exception():
    content = '{"observations":[{"event_id":"a","ticket_price":NaN,"tickets_sold":100},{"event_id":"b","ticket_price":100,"tickets_sold":150}]}'
    response = client.post("/api/v1/regression/fit", content=content,
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["detail"]
