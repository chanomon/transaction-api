from sqlalchemy import Column, String, Numeric, DateTime, Enum, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(String(50), nullable=False, index=True)
    type = Column(Enum("CREDIT", "DEBIT", name="transaction_type"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)##12 digits in total and 2 decimals
    currency = Column(String(3), nullable=False, default="MXN")
    description = Column(String(255), nullable=True)
    
    status = Column(Enum("PENDING", "APPROVED", "REJECTED", name="transaction_status"), nullable=False, default="PENDING")
    provider_transaction_id = Column(String(50), nullable=True)
    balance_after = Column(Numeric(12, 2), nullable=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(String(255), nullable=True)
    
    executed_at = Column(DateTime(timezone=True), nullable=True) ##I belive that I dont need this and updated_at 
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    #updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    # Índice adicional (opcional, porque ya pusimos index=True en account_id)
    __table_args__ = (
        Index("ix_transactions_account_id_status", "account_id", "status"),
    )

    def __repr__(self):
        return f"<Transaction {self.id} account={self.account_id} status={self.status}>"
