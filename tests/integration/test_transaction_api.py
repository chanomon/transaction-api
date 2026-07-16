import pytest
from httpx import AsyncClient
from models.schemas import TransactionRequest
## These are the schemas to test
@pytest.mark.integration
async def test_success_transaction(client: AsyncClient):
    payload = {
        "accountId": "acc-success",
        "type": "CREDIT",
        "amount": 1500,
        "currency": "MXN",
        "description": "Test"
    }
    response = await client.post("/api/v1/transactions/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "APPROVED"
    assert data["balanceAfter"] == 5500.0
    assert data["providerTransactionId"] == "txn-789"

@pytest.mark.integration
async def test_fail_insufficient_funds(client: AsyncClient):
    payload = {
        "accountId": "acc-fail",
        "type": "DEBIT",
        "amount": 500,
        "currency": "MXN"
    }
    response = await client.post("/api/v1/transactions/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "REJECTED"
    assert data["errorCode"] == "INSUFFICIENT_FUNDS"

@pytest.mark.integration
async def test_debit_limit_validator(client: AsyncClient):
    payload = {
        "accountId": "acc-123",
        "type": "DEBIT",
        "amount": 15000,
        "currency": "MXN"
    }
    response = await client.post("/api/v1/transactions/", json=payload)
    assert response.status_code == 422
    assert "10000" in response.text
