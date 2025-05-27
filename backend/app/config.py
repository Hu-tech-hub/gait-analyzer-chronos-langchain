import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
    
    # Chronos
    CHRONOS_MODEL = os.getenv("CHRONOS_MODEL", "amazon/chronos-bolt-tiny")
    DEVICE = os.getenv("DEVICE", "cpu")
    
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))

settings = Settings()
