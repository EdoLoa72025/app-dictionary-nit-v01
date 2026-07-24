from __future__ import annotations

import hashlib
import io
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .normalization import (
    clean_text,
    normalize_dataframe_columns,
    normalize_identification,
    parse_date,
    parse_integer_like_text,
    parse_number,
)
from .parser import (
    ParserContext,
    classify_row,
    parse_account_header,
    parse_third_party_header,
)


def _hash_movement(movement: dict[str, Any]) -> str:
    stable_fields = [
        movement.get("identificacion"),
        movement.get("sucursal"),
        movement.get("codigo_contable"),
        movement.get("comprobante"),
        movement.get("fecha_elaboracion"),
        movement.get("saldo_inicial"),
        movement.get("debito"),
        movement.get("credito"),
        movement.get("saldo_movimiento"),
    ]
    payload = "|".join("" if value is None else str(value) for value in stable_fields)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_excel_file(uploaded_file: Any) -> list[tuple[str, pd.DataFrame]]:
    content = uploaded_file.getvalue()
    workbook = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
    return [
        (
            sheet_name,
            pd.read_excel(
                io.BytesIO(content),
                sheet_name=sheet_name,
                dtype={"Identificación": "string"},
                engine="openpyxl",
            ),
        )
        for sheet_name in workbook.sheet_names
    ]


def _build_movement(
    row: dict[str, Any],
    context: ParserContext,
    source_file: str,
    source_sheet: str,
) -> dict[str, Any] | None:
    identification = normalize_identification(row.get("identificacion"))
    identification = identification or context.identificacion

    if not identification:
        return None

    date_value = parse_date(row.get("fecha_elaboracion"))
    movement = {
        "identificacion": identification,
        "nombre_tercero": clean_text(row.get("nombre_tercero"))
        or context.nombre_tercero,
        "sucursal": parse_integer_like_text(row.get("sucursal")),
        "codigo_contable": parse_integer_like_text(row.get("codigo_contable"))
        or context.codigo_contable,
        "cuenta_contable": clean_text(row.get("cuenta_contable"))
        or context.cuenta_contable,
        "comprobante": clean_text(row.get("comprobante")),
        "fecha_elaboracion": date_value,
        "anio": date_value.year if date_value else None,
        "saldo_inicial": round(parse_number(row.get("saldo_inicial")), 2),
        "debito": round(parse_number(row.get("debito")), 2),
        "credito": round(parse_number(row.get("credito")), 2),
        "saldo_movimiento": round(parse_number(row.get("saldo_movimiento")),2,),
        "archivo_origen": source_file,
        "hoja_origen": source_sheet,
        "fecha_carga": datetime.now(timezone.utc),
    }
    movement["movement_hash"] = _hash_movement(movement)
    return movement


def process_uploaded_files(uploaded_files: list[Any]) -> dict[str, Any]:
    movements: list[dict[str, Any]] = []
    third_parties: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    rows_read = 0

    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name

        try:
            sheets = _read_excel_file(uploaded_file)
        except Exception as exc:
            warnings.append(f"{file_name}: no se pudo leer ({exc}).")
            continue

        for sheet_name, raw_df in sheets:
            if raw_df.empty:
                continue

            rows_read += len(raw_df)
            df = normalize_dataframe_columns(raw_df)
            context = ParserContext()

            for row in df.to_dict(orient="records"):
                row_type = classify_row(row)

                if row_type == "third_party_summary":
                    identification, name = parse_third_party_header(
                        row.get("identificacion")
                    )
                    context.identificacion = identification
                    context.nombre_tercero = name

                    if identification:
                        third_parties.setdefault(
                            identification,
                            {
                                "identificacion": identification,
                                "nombre_tercero": name,
                            },
                        )
                    continue

                if row_type == "account_summary":
                    code, name = parse_account_header(
                        row.get("identificacion")
                    )
                    context.codigo_contable = code
                    context.cuenta_contable = name
                    continue

                if row_type != "movement":
                    continue

                movement = _build_movement(
                    row=row,
                    context=context,
                    source_file=file_name,
                    source_sheet=sheet_name,
                )

                if not movement:
                    warnings.append(
                        f"{file_name}/{sheet_name}: movimiento sin identificación."
                    )
                    continue

                movements.append(movement)

                identification = movement["identificacion"]
                third_parties.setdefault(
                    identification,
                    {
                        "identificacion": identification,
                        "nombre_tercero": movement["nombre_tercero"],
                    },
                )

    return {
        "files_processed": len(uploaded_files),
        "rows_read": rows_read,
        "movements": movements,
        "third_parties": list(third_parties.values()),
        "warnings": warnings,
    }
