from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DATABASE = os.getenv(
    "MONGODB_DATABASE",
    "app_dictionary_nit_v01",
)
MONGODB_MOVEMENTS_COLLECTION = os.getenv(
    "MONGODB_MOVEMENTS_COLLECTION",
    "movements",
)
MONGODB_THIRD_PARTIES_COLLECTION = os.getenv(
    "MONGODB_THIRD_PARTIES_COLLECTION",
    "third_parties",
)

ALLOWED_EXTENSIONS = ["xlsx"]
UPLOADER_LABEL = "Selecciona uno o varios archivos XLSX"

TIPO_EXT_LIMITS = {
    "1": 1,
    "5": 5,
    "10": 10,
    "25": 25,
    "50": 50,
    "100": 100,
}
