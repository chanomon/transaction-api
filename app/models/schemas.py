from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime, timezone
from typing import Literal
import uuid
## request_transaction.py will need this schema



class TransactionRequest(BaseModel):
    accountId: str = Field(..., example="acc-123456")
    type: str = Field(..., example="CREDIT")
    amount: float = Field(..., gt=1.0, example=1500.00) ##gt=1.0 the amounts shall be >1.00
    currency: Literal["MXN"] = Field(..., example="MXN")# Changed to this so now I dont need field_validator for currency#str = Field(..., min_length=3, max_length=3, example="MXN")
    description: Optional[str] = Field(None, example="Transferencia recibida")

    # Validation for the 'type' CREDIT o DEBIT
    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str: 
        allowed = ["CREDIT", "DEBIT"]
        if v not in allowed:
            raise ValueError(f"Tipo debe ser uno de: {allowed}")
        return v

    # Once I validated the values alone now I validate the relations between them
        # The debits amounts shall not surpass 10000.00
    @model_validator(mode="after")
    def validate_debit_limit(self) -> "TransactionRequest":
        if self.type == "DEBIT" and self.amount > 10000.00:
            raise ValueError("El monto máximo para débitos es 10000.00 MXN.")
        return self
#class TransactionResponse(BaseModel):
#    transactionId: str
#    accountId: str
#    type: str
#    amount: float
#    currency: str
#    status: str = "PENDING"
#    createdAt: str


class TransactionResponse(BaseModel):
    id: str
    accountId: str = Field(..., validation_alias="account_id")
    type: str
    amount: float
    currency: str
    description: Optional[str] = None
    status: str
    providerTransactionId: Optional[str] = Field(None, validation_alias="provider_transaction_id")
    balanceAfter: Optional[float] = Field(None, validation_alias="balance_after")
    createdAt: datetime = Field(None, validation_alias="created_at")
    executedAt: Optional[datetime] = Field(None, validation_alias="executed_at")
    errorCode: Optional[str] = Field(None, validation_alias="error_code")
    errorMessage: Optional[str] = Field(None, validation_alias="error_message")
## validation_alias (not alias) lets us read snake_case attributes from the ORM object
## while still serializing the response using the camelCase field names the spec requires.
    model_config = {"populate_by_name": True}

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, v):
        ## the ORM returns a uuid.UUID object; the API contract wants a plain string
        return str(v)
