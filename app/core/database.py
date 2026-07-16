from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from core.config import settings
## This script is the configuration so the app speaks to the database asyncronously
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  #True to see SQL in logs
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    ## Dependency of FastAPI to inject the DB session
    async with AsyncSessionLocal() as session:
        yield session

        # to create tables, only used in dev
async def init_db():
    ## Here I pull the model for the database
    from models.db_models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
