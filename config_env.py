
from pydantic import Field, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent



class Settings(BaseSettings):
    
    AZURE_OPENAI_API_KEY:  str = Field(..., validation_alias="AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT:  str = Field(..., validation_alias="AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT:  str = Field(..., validation_alias="AZURE_OPENAI_DEPLOYMENT")
    AZURE_OPENAI_API_VERSION:  str = Field(..., validation_alias="AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_EMBEDDING_MODEL:  str = Field(..., validation_alias="AZURE_OPENAI_EMBEDDING_MODEL")


        
    DATABASE_URL_NEON: str = None
    PRODUCT_CATALOG_URL: str = "https://api.kittchens.com/api/products?page=1&limit=1000"
    CATALOG_REFRESH_INTERVAL: int = 3600  # in seconds (1 hour)
    BASE_CATALOG_URL: str = "https://api.kittchens.com/api"

    GROQ_API_KEY: str  = "none"


    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )


settings = Settings()
