from fastapi import FastAPI
from api.transactions.request_transaction import router

# Crear la aplicación FastAPI
app = FastAPI(
    title="Transaction API",
    description="API para gestionar transacciones financieras",
    version="1.0.0"
)

# Registrar las rutas de transacciones
app.include_router(router, prefix="/api/v1")

# Endpoint de health check (opcional)
@app.get("/health")
async def health_check():
    return {"status": "ok"}
