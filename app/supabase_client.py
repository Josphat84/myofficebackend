# app/supabase_client.py

from supabase import create_client, Client
import os
from dotenv import load_dotenv

#Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")   #Use service role key for backend operations

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)