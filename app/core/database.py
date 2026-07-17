#from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker##declarative_base
from core.config import settings
## This script is the configuration so the app speaks to the database asyncronously
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  #True to see SQL in logs
    future=True,
)

#AsyncSessionLocal = async_sessionmaker(
#    engine,
#    class_=AsyncSession,
#    expire_on_commit=False
#)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from models.db_models import Base
    Base.metadata.create_all(engine)

#async def get_db() -> AsyncSession:
#    ## Dependency of FastAPI to inject the DB session
#    async with AsyncSessionLocal() as session:
#        yield session
#
#        # to create tables, only used in dev
#async def init_db():
#    ## Here I pull the model for the database
#    print("🔄 Creando tablas...")
#    from models.db_models import Base
#    async with engine.begin() as conn:
#        await conn.run_sync(Base.metadata.create_all)
#    print("✅ Tablas creadas (o ya existían).")
