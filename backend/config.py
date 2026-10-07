import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "smart-electric-bill-analyzer-super-secret-key-2026")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-electricity-secret-key-998822")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_EXPIRE_HOURS", 24)))
    
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/electricity_analyzer")
    DB_NAME = os.getenv("DB_NAME", "electricity_analyzer")
    
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
    
    # OCR / Tesseract path override if available on Windows
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
