from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .normalization import clean_text, normalize_identification

THIRD_PARTY_RE = re.compile(
    r"^\s*Nombre\s+del\s+tercero\s*:\s*(\d+)\s*(.*?)\s*$",
    re.IGNORECASE,
)

ACCOUNT_RE = re.compile(
    r"^\s*Cuenta\s+contable\s*:\s*(\d+)\s*(.*?)\s*$",
    re.IGNORECASE,
)


@dataclass
class ParserContext:
    identificacion: str | None = None
    nombre_tercero: str | None = None
    codigo_contable: str | None = None
    cuenta_contable: str | None = None


def parse_third_party_header(value: Any) -> tuple[str | None, str | None]:
    text = clean_text(value)
    if not text:
        return None, None

    match = THIRD_PARTY_RE.match(text)
    if not match:
        return None, None

    return normalize_identification(match.group(1)), clean_text(match.group(2))


def parse_account_header(value: Any) -> tuple[str | None, str | None]:
    text = clean_text(value)
    if not text:
        return None, None

    match = ACCOUNT_RE.match(text)
    if not match:
        return None, None

    return clean_text(match.group(1)), clean_text(match.group(2))


def classify_row(row: dict[str, Any]) -> str:
    identification = clean_text(row.get("identificacion"))

    if identification:
        if THIRD_PARTY_RE.match(identification):
            return "third_party_summary"

        if ACCOUNT_RE.match(identification):
            return "account_summary"

    # Un movimiento real debe tener comprobante y fecha.
    if clean_text(row.get("comprobante")) and clean_text(
        row.get("fecha_elaboracion")
    ):
        return "movement"

    return "other"
