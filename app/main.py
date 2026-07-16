from fastapi import FastAPI
from api.transactions.request_transaction import router
from core.database import init_db  # <--- Importa la función

# Crear la aplicación FastAPI
app = FastAPI(
    title="Transaction API",
    description="API para gestionar transacciones financieras",
    version="1.0.0"
)
## Event that executes when app starts
@app.on_event("startup")
async def startup():
    ##creates tables defined in db_models if they dont exist
    await init_db()
    print("✅ DB initialiazed and tables created.")

# Registrar las rutas de transacciones
app.include_router(router, prefix="/api/v1")

# Endpoint de health check (opcional)
@app.get("/health")
async def health_check():
    return {"status": "ok"}
