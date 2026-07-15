from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime, timezone
from typing import Literal
import uuid

# --- 1. Definne the models of data with Pydantic ---

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

class TransactionResponse(BaseModel):
    transactionId: str
    accountId: str
    type: str
    amount: float
    currency: str
    status: str = "PENDING"
    createdAt: str

# --- 2. Configurar el enrutador ---

router = APIRouter( ##FastAPI organizes the rutes in separeted modules
    prefix="/transactions",
    tags=["Transactions"]
)

# --- 3. Endpoint POST /transactions (asíncrono) ---

@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(request: TransactionRequest): ## define as asyncronous func, read body of 
                                                           ##POST and parse as JSON and validetes with TransactionRequest model 
    """
    Endpoint para crear una nueva transacción.
    - Valida que el tipo sea CREDIT o DEBIT.
    - Genera un ID único y devuelve una respuesta simulada.
    """
    # Generar un ID único para la transacción
    transaction_id = f"txn-{uuid.uuid4().hex[:8]}"
    
    # Obtener fecha actual en UTC (formato ISO 8601)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") ##Format from  response
    # Construir la respuesta
    response = TransactionResponse(
        transactionId=transaction_id,
        accountId=request.accountId,
        type=request.type,
            amount=request.amount,
        currency=request.currency,
        createdAt=created_at
    )
    
    # En el futuro, aquí se llamaría al proveedor externo y se guardaría en BD
    return response
