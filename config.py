import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Путь к БД: в Docker используем /app/data, локально - текущую папку
DATA_DIR = Path(os.getenv("DATA_DIR", "."))
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = str(DATA_DIR / "database.db")
