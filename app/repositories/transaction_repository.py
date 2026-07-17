#from errno import errorcode

from sqlalchemy.orm import Session#ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models.db_models import Transaction
from models.schemas import TransactionRequest
from datetime import datetime, timezone
from uuid import uuid4
## To isolate the logc between service and data base, 
## here I make abstraction of my services,
##as my service does not know if im using SQL, mongo or whatever, 


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, request: TransactionRequest) -> Transaction:
        ##Receives the request data and creates a new transaction in DB with PENDING state
        new_tx = Transaction(
            id=uuid4(),
            account_id=request.accountId,
            type=request.type,
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            status="PENDING"
        )
        self.db.add(new_tx)
        self.db.commit()
        self.db.refresh(new_tx)
        return new_tx#return new transaction

    def update_after_provider(
        self,
        tx_id: str,
        provider_response: dict,
        is_success: bool
    ) -> Transaction:
        """
        Actualiza la transacción con la respuesta del proveedor.
        - is_success True: estado APPROVED, guarda balance, tx_id del proveedor, executed_at.
        - is_success False: estado REJECTED, guarda error_code y error_message.
        """
        stmt = update(Transaction).where(Transaction.id == tx_id).values(
            status="APPROVED" if is_success else "REJECTED",
            provider_transaction_id=provider_response.get("transactionId") if is_success else None,
            balance_after=provider_response.get("balance") if is_success else None,
            #executed_at=datetime.fromisoformat(provider_response["executedAt"].replace('Z', '+00:00')) if is_success and "executedAt" in provider_response else None, # I'm not using executed_at
            error_code=provider_response.get("code") if not is_success else None,
            error_message=provider_response.get("message") if not is_success else None,
            #updated_at=datetime.now(timezone.utc) Iḿ not using updated_at
        ).returning(Transaction)
        
        result = self.db.execute(stmt)
        self.db.commit()
        # Devolver la transacción actualizada (si se necesita)
        updated_tx = result.scalar_one()#returns only on row of DB if returns 0 or more than 1 launches gives NoResultFound or MultipleResultsFound
        return updated_tx

    def list_transactions(self, filters: dict, page: int = 1, limit: int = 20) -> list[Transaction]:
        ## Returns a list of filtered transactions by account_it, status, or type, it is ordered by created_at
        query = select(Transaction).order_by(Transaction.created_at.desc())

        if "accountId" in filters and filters["accountId"] is not None:
            query = query.where(Transaction.account_id == filters["accountId"])
        if "status" in filters and filters["status"] is not None:
            query = query.where(Transaction.status == filters["status"])
        if "type" in filters and filters["type"] is not None:
            query = query.where(Transaction.type == filters["type"])
        ## Pagination: skip the previous pages' rows, then cap the page size
        query = query.offset((page - 1) * limit).limit(limit)
        result = self.db.execute(query)
        return result.scalars().all()
