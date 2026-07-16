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
    amount: float = Field(..., ge=1.0, example=1500.00) #ge=1.0 means that the amount should be >=1.0  as intended in bussiness rules
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
    accountId: str
    type: str
    amount: float
    currency: str
    description: Optional[str] = None
    status: str
    providerTransactionId: Optional[str] = None
    balanceAfter: Optional[float] = None
    createdAt: datetime
    executedAt: Optional[datetime] = None
    errorCode: Optional[str] = None
    errorMessage: Optional[str] = None
