from __future__ import annotations

import re
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
        if not movements:
            return {
                "inserted": 0,
                "duplicates": 0,
            }

        inserted = 0
        duplicates = 0

        try:
            response = self.mongo.movements.insert_many(
                movements,
                ordered=False,
            )
            inserted = len(response.inserted_ids)
        except BulkWriteError as exc:
            write_errors = exc.details.get("writeErrors", [])
            failed_indexes = {error["index"] for error in write_errors}
            duplicate_indexes = {
                error["index"]
                for error in write_errors
                if error.get("code") == 11000
            }

            if failed_indexes != duplicate_indexes:
                raise

            duplicates = len(duplicate_indexes)
            inserted = len(movements) - len(failed_indexes)

        identifications = {
            movement["identificacion"]
            for movement in movements
            if movement.get("identificacion")
        }
        self._refresh_third_party_summaries(identifications)

        return {
            "inserted": inserted,
            "duplicates": duplicates,
        }

    def _refresh_third_party_summaries(
        self,
        identifications: set[str],
    ) -> None:
        if not identifications:
            return

        pipeline = [
            {
                "$match": {
                    "identificacion": {
                        "$in": sorted(identifications),
                    }
                }
            },
            {
                "$sort": {
                    "fecha_carga": 1,
                    "fecha_elaboracion": 1,
                }
            },
            {
                "$group": {
                    "_id": "$identificacion",
                    "nombre_tercero": {"$last": "$nombre_tercero"},
                    "total_movimientos": {"$sum": 1},
                    "total_debito": {"$sum": "$debito"},
                    "total_credito": {"$sum": "$credito"},
                    "total_saldo_movimiento": {"$sum": "$saldo_movimiento"},
                    "anios": {"$addToSet": "$anio"},
                    "cuentas": {"$addToSet": "$codigo_contable"},
                    "fecha_primera_carga": {"$min": "$fecha_carga"},
                }
            },
        ]

        now = datetime.now(timezone.utc)

        for summary in self.mongo.movements.aggregate(pipeline):
            identification = summary["_id"]

            self.mongo.third_parties.update_one(
                {"identificacion": identification},
                {
                    "$set": {
                        "identificacion": identification,
                        "nombre_tercero": summary.get("nombre_tercero"),
                        "total_movimientos": summary.get("total_movimientos", 0),
                        "total_debito": summary.get("total_debito", 0.0),
                        "total_credito": summary.get("total_credito", 0.0),
                        "total_saldo_movimiento": summary.get(
                            "total_saldo_movimiento",
                            0.0,
                        ),
                        "anios": sorted(
                            year
                            for year in summary.get("anios", [])
                            if year is not None
                        ),
                        "cuentas": sorted(
                            account
                            for account in summary.get("cuentas", [])
                            if account
                        ),
                        "fecha_primera_carga": summary.get("fecha_primera_carga"),
                        "fecha_ultima_actualizacion": now,
                    }
                },
                upsert=True,
            )

    def get_third_party(self, identification: str) -> dict[str, Any] | None:
        return self.mongo.third_parties.find_one(
            {"identificacion": self.normalize_identification(identification)},
            {"_id": 0},
        )

    # METODOS PARA OBTENER cONSULTAS POR CUENTA CONTABLES
    
    def get_account_by_code(
        self,
        codigo_contable: str,
    ) -> dict[str, Any] | None:
        normalized_code = (codigo_contable or "").strip()
        if not normalized_code:
            return None

        pipeline = [
            {
                "$match": {
                    "codigo_contable": normalized_code,
                }
            },
            {
                "$group": {
                    "_id": "$codigo_contable",
                    "cuentas_contables": {"$addToSet": "$cuenta_contable"},
                    "total_movimientos": {"$sum": 1},
                    "total_debito": {"$sum": "$debito"},
                    "total_credito": {"$sum": "$credito"},
                    "total_saldo_movimiento": {
                        "$sum": "$saldo_movimiento"
                    },
                    "terceros": {"$addToSet": "$identificacion"},
                }
            },
        ]

        results = list(self.mongo.movements.aggregate(pipeline))
        if not results:
            return None

        summary = results[0]
        return {
            "codigo_contable": summary["_id"],
            "cuentas_contables": sorted(
                value for value in summary.get("cuentas_contables", []) if value
            ),
            "total_movimientos": summary.get("total_movimientos", 0),
            "total_debito": summary.get("total_debito", 0.0),
            "total_credito": summary.get("total_credito", 0.0),
            "total_saldo_movimiento": summary.get(
                "total_saldo_movimiento",
                0.0,
            ),
            "total_terceros": len(
                [value for value in summary.get("terceros", []) if value]
            ),
        }

    def get_account_by_name(
        self,
        cuenta_contable: str,
    ) -> dict[str, Any] | None:
        normalized_name = (cuenta_contable or "").strip()
        if not normalized_name:
            return None

        pipeline = [
            {
                "$match": {
                    "cuenta_contable": {
                        "$regex": f"^{re.escape(normalized_name)}$",
                        "$options": "i",
                    }
                }
            },
            {
                "$group": {
                    "_id": "$cuenta_contable",
                    "codigos_contables": {"$addToSet": "$codigo_contable"},
                    "total_movimientos": {"$sum": 1},
                    "total_debito": {"$sum": "$debito"},
                    "total_credito": {"$sum": "$credito"},
                    "total_saldo_movimiento": {
                        "$sum": "$saldo_movimiento"
                    },
                    "terceros": {"$addToSet": "$identificacion"},
                }
            },
        ]

        results = list(self.mongo.movements.aggregate(pipeline))
        if not results:
            return None

        summary = results[0]
        return {
            "cuenta_contable": summary["_id"],
            "codigos_contables": sorted(
                value for value in summary.get("codigos_contables", []) if value
            ),
            "total_movimientos": summary.get("total_movimientos", 0),
            "total_debito": summary.get("total_debito", 0.0),
            "total_credito": summary.get("total_credito", 0.0),
            "total_saldo_movimiento": summary.get(
                "total_saldo_movimiento",
                0.0,
            ),
            "total_terceros": len(
                [value for value in summary.get("terceros", []) if value]
            ),
        }

    def get_movements_by_account_code(
        self,
        codigo_contable: str,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        normalized_code = (codigo_contable or "").strip()
        if not normalized_code:
            return []

        cursor = (
            self.mongo.movements.find(
                {"codigo_contable": normalized_code},
                {"_id": 0},
            )
            .sort("fecha_elaboracion", 1)
            .limit(limit)
        )

        return list(cursor)

    def get_movements_by_account_name(
        self,
        cuenta_contable: str,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        normalized_name = (cuenta_contable or "").strip()
        if not normalized_name:
            return []

        cursor = (
            self.mongo.movements.find(
                {
                    "cuenta_contable": {
                        "$regex": f"^{re.escape(normalized_name)}$",
                        "$options": "i",
                    }
                },
                {"_id": 0},
            )
            .sort("fecha_elaboracion", 1)
            .limit(limit)
        )

        return list(cursor)  
    
    # **********************************
    
    # Reporte General de cuenta_contable *****
    
    def get_account_code_report(
        self,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "codigo_contable": "$codigo_contable",
                        "cuenta_contable": "$cuenta_contable",
                    },
                    "total_movimientos": {"$sum": 1},
                    "total_debito": {"$sum": "$debito"},
                    "total_credito": {"$sum": "$credito"},
                    "total_saldo_movimiento": {
                        "$sum": "$saldo_movimiento"
                    },
                    "terceros": {"$addToSet": "$identificacion"},
                }
            },
            {
                "$sort": {
                    "_id.codigo_contable": 1,
                    "_id.cuenta_contable": 1,
                }
            },
            {
                "$limit": limit,
            },
        ]

        results = list(self.mongo.movements.aggregate(pipeline))

        report: list[dict[str, Any]] = []
        for item in results:
            report.append(
                {
                    "codigo_contable": item["_id"].get("codigo_contable"),
                    "cuenta_contable": item["_id"].get("cuenta_contable"),
                    "total_movimientos": item.get("total_movimientos", 0),
                    "total_terceros": len(
                        [
                            value
                            for value in item.get("terceros", [])
                            if value
                        ]
                    ),
                    "total_debito": item.get("total_debito", 0.0),
                    "total_credito": item.get("total_credito", 0.0),
                    "total_saldo_movimiento": item.get(
                        "total_saldo_movimiento",
                        0.0,
                    ),
                }
            )

        return report
    
    
    
    
    # ****************************
    
    
    
    
    
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