from __future__ import annotations

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from .config import (
    MONGODB_DATABASE,
    MONGODB_MOVEMENTS_COLLECTION,
    MONGODB_THIRD_PARTIES_COLLECTION,
    MONGODB_URI,
)


class MongoDBManager:
    """Gestiona la conexión y los índices de la aplicación."""

    def __init__(self) -> None:
        if not MONGODB_URI:
            raise RuntimeError(
                "MONGODB_URI no está configurada. "
                "Crea un archivo .env a partir de .env.example."
            )

        self.client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=10_000,
            connectTimeoutMS=10_000,
        )
        self.database: Database = self.client[MONGODB_DATABASE]

    @property
    def movements(self) -> Collection:
        return self.database[MONGODB_MOVEMENTS_COLLECTION]

    @property
    def third_parties(self) -> Collection:
        return self.database[MONGODB_THIRD_PARTIES_COLLECTION]

    def ensure_indexes(self) -> None:
        self.movements.create_index(
            [
                ("identificacion", ASCENDING),
                ("fecha_elaboracion", ASCENDING),
            ],
            name="idx_identificacion_fecha",
        )
        self.movements.create_index(
            [
                ("identificacion", ASCENDING),
                ("anio", ASCENDING),
                ("codigo_contable", ASCENDING),
            ],
            name="idx_identificacion_anio_cuenta",
        )
        self.movements.create_index(
            [("movement_hash", ASCENDING)],
            unique=True,
            name="uq_movement_hash",
        )
        self.third_parties.create_index(
            [("identificacion", ASCENDING)],
            unique=True,
            name="uq_identificacion",
        )

    def ping(self) -> None:
        self.client.admin.command("ping")

    def close(self) -> None:
        self.client.close()
