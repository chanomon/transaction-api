from models.schemas import TransactionRequest
from repositories.transaction_repository import TransactionRepository
from clients.provider_client import ProviderClient
from sqlalchemy.orm import Session
import httpx

class TransactionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TransactionRepository(db)
        self.provider = ProviderClient()

    def process_transaction(self, request: TransactionRequest) -> dict:
        ## Create transaction in DB pending
        new_tx = self.repo.create(request)
        
        try:
            ##Call the provider (Wiremock)
            provider_response = self.provider.execute(request)
            
            #Evaluate provider reponse
            ## is success if "APPROVED"
            is_success = provider_response.get("status") == "APPROVED"#evaluate response, is status approved, then its true, otherwise its false
            
            #Update the transaction
            updated_tx = self.repo.update_after_provider(
                tx_id=new_tx.id,
                provider_response=provider_response,
                is_success=is_success
            )
            # Return the updated transaction, as Pydantic model 

            return {
                "id": str(updated_tx.id),
                "accountId": updated_tx.account_id,
                "type": updated_tx.type,
                "amount": float(updated_tx.amount),
                "currency": updated_tx.currency,
                "description": updated_tx.description,
                "status": updated_tx.status,
                "providerTransactionId": updated_tx.provider_transaction_id,
                "balanceAfter": float(updated_tx.balance_after) if updated_tx.balance_after is not None else None,
                "createdAt": updated_tx.created_at.isoformat(),
                #"executedAt": updated_tx.executed_at.isoformat() if updated_tx.executed_at else None, # i'm not using this
                "errorCode": updated_tx.error_code,
                "errorMessage": updated_tx.error_message
            }
            
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
            ## If providers fails, then produce REJECTED with code and describing error
            error_response = {
                "code": "PROVIDER_UNAVAILABLE",
                "message": f"Error al contactar al proveedor: {str(e)}"
            }
            updated_tx = self.repo.update_after_provider(
                tx_id=new_tx.id,
                provider_response=error_response,
                is_success=False
            )
            ## Fill the response with error
            return {
                "id": str(updated_tx.id),
                "accountId": updated_tx.account_id,
                "type": updated_tx.type,
                "amount": float(updated_tx.amount),
                "currency": updated_tx.currency,
                "description": updated_tx.description,
                "status": updated_tx.status,
                "providerTransactionId": None,
                "balanceAfter": None,
                "createdAt": updated_tx.created_at.isoformat(),
                #"executedAt": None,
                "errorCode": updated_tx.error_code,
                "errorMessage": updated_tx.error_message
            }

#    async def get_transactions(self, filters: dict) -> list[dict]:
#        ##Get filtered transactions and converts to dict for response
#        transactions = await self.repo.list_transactions(filters)
#        return [
#            {
#                "id": str(tx.id),
#                "accountId": tx.account_id,
#                "type": tx.type,
#                "amount": float(tx.amount),
#                "currency": tx.currency,
#                "description": tx.description,
#                "status": tx.status,
#                "providerTransactionId": tx.provider_transaction_id,
#                "balanceAfter": float(tx.balance_after) if tx.balance_after is not None else None,
#                "createdAt": tx.created_at.isoformat(),
#                "executedAt": tx.executed_at.isoformat() if tx.executed_at else None,
#                "errorCode": tx.error_code,
#                "errorMessage": tx.error_message
#            }
#            for tx in transactions
#        ]
    ## This implementation is shorter
    def get_transactions(self, filters: dict, page: int = 1, limit: int = 20) -> list[dict]:
        """Obtiene transacciones y las convierte a diccionario."""
        ## Get transactions and parse them to dict
        transactions = self.repo.list_transactions(filters, page=page, limit=limit)
        ## We use scheme TransactionResponse to serilisate
        from models.schemas import TransactionResponse
        ##return [TransactionResponse.model_validate(tx).model_dump() for tx in transactions]
        ##Had bug here, now Pydantic can read atributes from Trnasaction object
        return [TransactionResponse.model_validate(tx, from_attributes=True).model_dump(by_alias=True) for tx in transactions]#This by_alias=True allows to JSON use the names in camelCase 
