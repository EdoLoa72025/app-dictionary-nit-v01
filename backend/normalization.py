from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any

import pandas as pd


def normalize_column_name(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


COLUMN_ALIASES = {
    "identificación": "identificacion",
    "identificacion": "identificacion",
    "sucursal": "sucursal",
    "nombre tercero": "nombre_tercero",
    "nombre del tercero": "nombre_tercero",
    "código contable": "codigo_contable",
    "codigo contable": "codigo_contable",
    "cuenta contable": "cuenta_contable",
    "comprobante": "comprobante",
    "fecha elaboración": "fecha_elaboracion",
    "fecha elaboracion": "fecha_elaboracion",
    "saldo inicial": "saldo_inicial",
    "débito": "debito",
    "debito": "debito",
    "crédito": "credito",
    "credito": "credito",
    "saldo movimiento": "saldo_movimiento",
}

REQUIRED_COLUMNS = {
    "identificacion",
    "sucursal",
    "nombre_tercero",
    "codigo_contable",
    "cuenta_contable",
    "comprobante",
    "fecha_elaboracion",
    "saldo_inicial",
    "debito",
    "credito",
    "saldo_movimiento",
}


def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for column in df.columns:
        normalized = normalize_column_name(column)
        rename_map[column] = COLUMN_ALIASES.get(normalized, normalized)

    result = df.rename(columns=rename_map).copy()

    for column in REQUIRED_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA

    return result


def clean_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    return text or None


def normalize_identification(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None

    return re.sub(r"\D", "", text) or text


def parse_number(value: Any) -> float:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(" ", "")

    # Soporta formatos comunes: 1.234.567,89 y 1234567.89.
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")

    return float(text)


def parse_date(value: Any) -> datetime | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None

    if isinstance(value, datetime):
        return value

    parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        return None

    return parsed.to_pydatetime()
