import os
from dotenv import load_dotenv

# Load environment variables (.env must be in the root directory)
_base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_base_dir, ".env"))

class Config:
    # Application
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_secret')
    PORT = int(os.environ.get('PORT', 5000))
    ENV = os.environ.get('FLASK_ENV', 'production')
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*')  # For CORS
    
    # MongoDB Atlas
    # MONGO_URI format for Atlas:

    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/AnimeDescriptor')
    DB_NAME = os.environ.get('DB_NAME', 'AnimeDescriptor')
    
    # OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    EMBEDDING_MODEL = "text-embedding-3-large"
    
    # BERT Model (Local Sentence Transformers)
    # Se utiliza directamente "Prashasst/anime-recommendation-model" ya que su rendimiento base
    BERT_MODEL = os.environ.get("BERT_MODEL", "Prashasst/anime-recommendation-model")
    BERT_RERANK_THRESHOLD = float(os.environ.get("BERT_RERANK_THRESHOLD", 60.0))
    
    # PayPal
    PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET")
    PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox")
    PAYPAL_API = "https://api-m.sandbox.paypal.com" if PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"
    PREMIUM_PRICE = os.environ.get("PREMIUM_PRICE", "3.00")
    
    # Email (SendGrid API)
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
    EMAIL_FROM = os.environ.get("EMAIL_FROM", "otakudescriptor@gmail.com")
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    # Search Limits (per day)
    FREE_DAILY_LIMIT = 10
    PREMIUM_DAILY_LIMIT = 200
    
    # Legacy names for backward compatibility
    FREE_HOURLY_LIMIT = FREE_DAILY_LIMIT
    PREMIUM_HOURLY_LIMIT = PREMIUM_DAILY_LIMIT
