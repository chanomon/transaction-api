from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
#from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional

#from datetime import datetime, timezone
#from typing import Literal
#import uuid
from services.transaction_service import TransactionService
from models.schemas import TransactionRequest
from models.schemas import TransactionResponse
##Im not using this classes , they went to schemas.py
# --- 1. Definne the models of data with Pydantic ---

#class TransactionRequest(BaseModel):
#    accountId: str = Field(..., example="acc-123456")
#    type: str = Field(..., example="CREDIT")
#    amount: float = Field(..., ge=1.0, example=1500.00) #ge=1.0 means that the amount should be >=1.0  as intended in bussiness rules
#    currency: Literal["MXN"] = Field(..., example="MXN")# Changed to this so now I dont need field_validator for currency#str = Field(..., min_length=3, max_length=3, example="MXN")
#    description: Optional[str] = Field(None, example="Transferencia recibida")
#
#    # Validation for the 'type' CREDIT o DEBIT
#    @field_validator("type")
#    @classmethod
#    def validate_type(cls, v: str) -> str: 
#        allowed = ["CREDIT", "DEBIT"]
#        if v not in allowed:
#            raise ValueError(f"Tipo debe ser uno de: {allowed}")
#        return v
#
#    # Once I validated the values alone now I validate the relations between them
#        # The debits amounts shall not surpass 10000.00
#    @model_validator(mode="after")
#    def validate_debit_limit(self) -> "TransactionRequest":
#        if self.type == "DEBIT" and self.amount > 10000.00:
#            raise ValueError("El monto máximo para débitos es 10000.00 MXN.")
#        return self
####IM NOT GONNA USE THIS HERE ANYMORE; THIS IS GOING TO schemas.py
#class TransactionResponse(BaseModel):
#    transactionId: str
#    accountId: str
#    type: str
#    amount: float
#    currency: str
#    status: str = "PENDING"
#    createdAt: str

##config the routes
router = APIRouter( ##FastAPI organizes the routes in separeted modules
    prefix="/transactions",
    tags=["Transactions"]
)

##Enpoint POST /transactions 
@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(                ## defined as asyncronous func, reads body of POST and parse as JSON and validetes with TransactionRequest model
        request: TransactionRequest,
        db: Session = Depends(get_db)
):
    service = TransactionService(db)
    result = service.process_transaction(request)
    ## The result is already a dict with expected structure
    return result


######## IM NOT USING THIS ANYMORE, THIS WAS TO CREATE THE RESPONSE IN THE ENDPOINT ITSELF AS TEST
#    # Generates unique ID for transaction
#    transaction_id = f"txn-{uuid.uuid4().hex[:8]}"
#    
#    # Obtener fecha actual en UTC (formato ISO 8601)
#    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") ##Format from  response
#    # Construir la respuesta
#    response = TransactionResponse(
#        transactionId=transaction_id,
#        accountId=request.accountId,
#        type=request.type,
#            amount=request.amount,
#        currency=request.currency,
#        createdAt=created_at
#    )
#    
#    # En el futuro, aquí se llamaría al proveedor externo y se guardaría en BD
#    return response

## Endpoint GET /transactions
@router.get("/", response_model=list[TransactionResponse])
def list_transactions(
    accountId: Optional[str] = Query(None, description="Filtrar por ID de cuenta"),
    status: Optional[str] = Query(None, description="Filtrar por estado (APPROVED/REJECTED)"),
    type: Optional[str] = Query(None, description="Filtrar por tipo (CREDIT/DEBIT)"),
    page: int = Query(1, ge=1, description="Número de página (empieza en 1)"),
    limit: int = Query(20, ge=1, le=100, description="Resultados por página"),
    db: Session = Depends(get_db)
):
    ## Security validations, avoids not expected values.
    if status and status not in ["APPROVED", "REJECTED"]:
        HTTPException(status_code=400, detail="status debe ser APPROVED o REJECTED")
    if type and type not in ["CREDIT", "DEBIT"]:
        HTTPException(status_code=400, detail="type debe ser CREDIT o DEBIT")
    service = TransactionService(db)
    ## Build dict with not None filters (more simple than the previous one)
    filters = {        
        "accountId": accountId,
        "status": status,
        "type": type
    }
    ##Remove None filters so the cannot reach query
    filters = {k: v for k, v in filters.items() if v is not None}
    #if accountId is not None:
    #    filters["account_id"] = accountId
    #if status is not None:
    #    filters["status"] = status
    #if type is not None:
    #    filters["type"] = type
    
    ## Passing page/limit so results come back paginated instead of the whole table
    transactions = service.get_transactions(filters, page=page, limit=limit)
    return transactions
