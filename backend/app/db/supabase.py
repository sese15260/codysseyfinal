from app.core.config import (
    SUPABASE_SECRET_KEY,
    SUPABASE_URL,
)
from supabase import Client, create_client

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)
