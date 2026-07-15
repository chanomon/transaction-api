import pytest
from pydantic import ValidationError
from app.api.transactions.request_transaction import TransactionRequest

def test_valid_transaction_credit():
    data = {
        "accountId": "acc-123",
        "type": "CREDIT",
        "amount": 1500.0,
        "currency": "MXN",
        "description": "Test"
    }
    tx = TransactionRequest(**data) ##two asterisk to unpackage data
    assert tx.amount == 1500.0
    assert tx.type == "CREDIT"

def test_invalid_debit_limit():
    data = {
        "accountId": "acc-123",
        "type": "DEBIT",
        "amount": 15000.0,
        "currency": "MXN"
    }
    with pytest.raises(ValidationError) as excinfo:
        TransactionRequest(**data)
    assert "10000.00" in str(excinfo.value)
