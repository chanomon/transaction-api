from models.schemas import TransactionRequest
from repositories.transaction_repository import TransactionRepository
from clients.provider_client import ProviderClient
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TransactionRepository(db)
        self.provider = ProviderClient()

    async def process_transaction(self, request: TransactionRequest) -> dict:
        ## Create transaction in DB pending
        new_tx = await self.repo.create(request)
        
        try:
            ##Call the provider (Wiremock)
            provider_response = await self.provider.execute(request)
            
            #Evaluate provider reponse
            ## is success if "APPROVED"
            is_success = provider_response.get("status") == "APPROVED"#this can be True or False
            
            #Update the transaction
            updated_tx = await self.repo.update_after_provider(
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
            updated_tx = await self.repo.update_after_provider(
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
