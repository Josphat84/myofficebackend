# backend/app/supabase_client.py

from supabase import create_client, Client
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning(
        "SUPABASE_URL or SUPABASE_KEY environment variables are not set. "
        "Database operations will fail. Set them in your .env file or deployment environment."
    )

supabase: Client = create_client(SUPABASE_URL or "", SUPABASE_KEY or "")