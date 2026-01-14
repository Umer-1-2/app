import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Explicit absolute path to .env
env_path = Path(__file__).parent / ".env"
print("Loading .env from:", env_path)

load_dotenv(dotenv_path=env_path, override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

print("DATABASE_URL value is:")
print(DATABASE_URL)

if DATABASE_URL is None:
    raise Exception("DATABASE_URL is NOT loaded")

engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"}
)

engine.connect()
print("DATABASE CONNECTED SUCCESSFULLY")
