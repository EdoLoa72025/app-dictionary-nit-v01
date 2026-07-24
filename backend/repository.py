from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo.errors import BulkWriteError

from .mongodb import MongoDBManager
from .normalization import normalize_identification


class MovementRepository:
    def __init__(self, mongo: MongoDBManager) -> None:
        self.mongo = mongo
        self.mongo.ping()
        self.mongo.ensure_indexes()

    @staticmethod
    def normalize_identification(value: str) -> str:
        return normalize_identification(value) or value.strip()

    def persist_batch(self, result: dict[str, Any]) -> dict[str, int]:
        movements = result["movements"]
        inserted = 0
        duplicates = 0

        if movements:
            try:
                response = self.mongo.movements.insert_many(
                    movements,
                    ordered=False,
                )
                inserted = len(response.inserted_ids)
            except BulkWriteError as exc:
                write_errors = exc.details.get("writeErrors", [])
                duplicates = sum(
                    1
                    for error in write_errors
                    if error.get("code") == 11000
                )
                inserted = len(movements) - len(write_errors)

        grouped: dict[str, dict[str, Any]] = {}

        for movement in movements:
            identification = movement["identificacion"]
            current = grouped.setdefault(
                identification,
                {
                    "identificacion": identification,
                    "nombre_tercero": movement.get("nombre_tercero"),
                    "total_movimientos": 0,
                    "total_debito": 0.0,
                    "total_credito": 0.0,
                    "total_saldo_movimiento": 0.0,
                    "anios": set(),
                    "cuentas": set(),
                },
            )

            current["total_movimientos"] += 1
            current["total_debito"] += movement["debito"]
            current["total_credito"] += movement["credito"]
            current["total_saldo_movimiento"] += movement[
                "saldo_movimiento"
            ]

            if movement.get("anio"):
                current["anios"].add(movement["anio"])

            if movement.get("codigo_contable"):
                current["cuentas"].add(movement["codigo_contable"])

        now = datetime.now(timezone.utc)

        for identification, summary in grouped.items():
            summary["anios"] = sorted(summary["anios"])
            summary["cuentas"] = sorted(summary["cuentas"])
            summary["fecha_ultima_actualizacion"] = now

            self.mongo.third_parties.update_one(
                {"identificacion": identification},
                {
                    "$set": summary,
                    "$setOnInsert": {
                        "fecha_primera_carga": now,
                    },
                },
                upsert=True,
            )

        return {
            "inserted": inserted,
            "duplicates": duplicates,
        }

    def get_third_party(self, identification: str) -> dict[str, Any] | None:
        return self.mongo.third_parties.find_one(
            {"identificacion": self.normalize_identification(identification)},
            {"_id": 0},
        )

    def get_movements(
        self,
        identification: str,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        cursor = (
            self.mongo.movements.find(
                {
                    "identificacion": self.normalize_identification(
                        identification
                    )
                },
                {"_id": 0},
            )
            .sort("fecha_elaboracion", 1)
            .limit(limit)
        )

        return list(cursor)
