from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(

    url=DATABASE_URL,
    echo=False,
    connect_args={"ssl": True},
    pool_pre_ping=True
)

local_session = async_sessionmaker(

    bind=engine,
    expire_on_commit=False
)

async def Get_DB():
    async with local_session() as session:
        yield session
