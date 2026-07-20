from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
#from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional

#from datetime import datetime, timezone
#from typing import Literal
#import uuid
from services.transaction_service import TransactionService, ProviderUnreachableError
from models.schemas import TransactionRequest
from models.schemas import TransactionResponse
from core.security import verify_api_key
##config the routes
router = APIRouter( ##FastAPI organizes the routes in separeted modules
    prefix="/transactions",
    tags=["Transactions"],
    dependencies=[Depends(verify_api_key)]#this line is to hook dependency in router level so now I dont need to repeat in POST and GET
)

##Enpoint POST /transactions 
@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(                ## defined as asyncronous func, reads body of POST and parse as JSON and validetes with TransactionRequest model
        request: TransactionRequest,
        db: Session = Depends(get_db)
):
    service = TransactionService(db)
    try:
        result = service.process_transaction(request)
    except ProviderUnreachableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El proveedor no está disponible, intenta de nuevo más tarde"
        )
    ## The result is already a dict with expected structure
    return result


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
        raise HTTPException(status_code=400, detail="status debe ser APPROVED o REJECTED")
    if type and type not in ["CREDIT", "DEBIT"]:
        raise HTTPException(status_code=400, detail="type debe ser CREDIT o DEBIT")
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
