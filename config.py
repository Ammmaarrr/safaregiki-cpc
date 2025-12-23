from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Meta WhatsApp API
    meta_access_token: str
    phone_number_id: str
    verify_token: str
    
    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_key: str = ""  # For admin operations
    
    # OpenAI for RAG
    openai_api_key: str = ""
    
    # App
    app_url: str = "https://your-app-url.com"
    
    # Admin Configuration
    admin_phone_numbers: str = ""  # Comma-separated: "923001234567,923009876543"
    admin_secret_key: str = "your-secret-key-change-in-production"
    
    def get_admin_phones(self) -> List[str]:
        """Get list of admin phone numbers"""
        if not self.admin_phone_numbers:
            return []
        return [p.strip() for p in self.admin_phone_numbers.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()