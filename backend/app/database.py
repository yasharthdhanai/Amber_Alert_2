import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL or SUPABASE_KEY is missing in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def init_db():
    # Since we are using Supabase Postgres, tables are managed on the cloud.
    # Initialization is just a pass-through here to maintain FastAPI startup compatibility.
    pass

async def get_db_connection():
    # We no longer need an aiosqlite connection generator. 
    # Calling functions will import `supabase` directly.
    return None
