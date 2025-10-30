# Supabase client
## This module initializes and provides access to the Supabase client
## File: backend/app/supabase_client.py


from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Use service_role key for backend

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
