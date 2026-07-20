#from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker##declarative_base
from core.config import settings
## This script is the configuration so the app speaks to the database 
## The engin admins the conection with the DB
## So first it receives URL to know what SQL dialect to use and what driver (psycopg2to use)
## The engine creates the fist conection when the first query is made
## Then it mantains the connection and do posterior queries throgh sessions.
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  ##True to see SQL in logs, usefull in debug.
    future=True, ##API "2.0" style, modern version
)

#AsyncSessionLocal = async_sessionmaker(
#    engine,
#    class_=AsyncSession,
#    expire_on_commit=False
#)
SessionLocal = sessionmaker( ##The session uses a connection from the enginde pool and returns the connection when it finishes 
    autocommit=False,
    autoflush=False,
    bind=engine,
)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()## returns the connection to the engines pool.

## This function is only called once, when app is created, so it assures that the table exists before it arrives the first query        
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
