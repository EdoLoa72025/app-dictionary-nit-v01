from __future__ import annotations

import streamlit as st
import pandas as pd

from backend.config import ALLOWED_EXTENSIONS, TIPO_EXT_LIMITS, UPLOADER_LABEL
from backend.ingestion import process_uploaded_files
from backend.mongodb import MongoDBManager
from backend.normalization import format_decimal_es
from backend.repository import MovementRepository

st.set_page_config(
    page_title="Auxiliar de terceros",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Auxiliar de terceros por NIT")
st.caption("Carga, normaliza y consulta movimientos auxiliares contables en MongoDB.")

@st.cache_resource
def get_repository() -> MovementRepository:
    return MovementRepository(MongoDBManager())

with st.sidebar:
    st.header("📂 Carga de archivos")

    tipo_ext = st.selectbox(
        label="TipoExt",
        options=list(TIPO_EXT_LIMITS.keys()),
        format_func=lambda option: (
            f"TipoExt={option} ({TIPO_EXT_LIMITS[option]} archivos)"
        ),
        help="Define cuántos archivos XLSX como máximo se procesarán en esta carga.",
    )

    uploaded_files = st.file_uploader(
        label=UPLOADER_LABEL,
        type=ALLOWED_EXTENSIONS,
        accept_multiple_files=True,
        help="Solo se aceptan archivos con extensión .xlsx",
    )

    st.caption(
        "Puedes arrastrar uno o varios archivos XLSX. "
        "Si subes más archivos que el límite del TipoExt elegido, "
        "solo se procesarán los primeros permitidos."
    )

    process_button = st.button(
        "🚀 Procesar y guardar",
        type="primary",
        use_container_width=True,
        disabled=not uploaded_files,
    )

if process_button and uploaded_files:
    limit = TIPO_EXT_LIMITS[tipo_ext]
    files_to_process = uploaded_files[:limit]
    ignored_files = uploaded_files[limit:]

    if ignored_files:
        st.warning(
            f"Se recibieron {len(uploaded_files)} archivos. "
            f"El límite de {tipo_ext} permite procesar {limit}; "
            f"se ignorarán {len(ignored_files)}."
        )

    with st.spinner("Procesando archivos y guardando en MongoDB..."):
        try:
            result = process_uploaded_files(files_to_process)
            repository = get_repository()
            persistence = repository.persist_batch(result)

            st.session_state["last_result"] = {
                "processing": result,
                "persistence": persistence,
            }
            st.success("Procesamiento completado.")
        except Exception as exc:
            st.error(f"No fue posible procesar la carga: {exc}")

if "last_result" in st.session_state:
    processing = st.session_state["last_result"]["processing"]
    persistence = st.session_state["last_result"]["persistence"]

    st.subheader("Resultado de la última carga")

    cols = st.columns(6)
    cols[0].metric("Archivos", processing["files_processed"])
    cols[1].metric("Filas leídas", processing["rows_read"])
    cols[2].metric("Movimientos detectados", len(processing["movements"]))
    cols[3].metric("Terceros", len(processing["third_parties"]))
    cols[4].metric("Insertados", persistence["inserted"])
    cols[5].metric("Duplicados", persistence["duplicates"])

    if persistence["inserted"] == 0 and len(processing["movements"]) > 0:
        st.warning(
            "MongoDB respondió correctamente, pero no se insertaron movimientos "
            "nuevos. La carga probablemente ya existía y fue detectada como "
            "duplicada por `movement_hash`."
        )

    if processing["warnings"]:
        with st.expander("⚠️ Advertencias"):
            for warning in processing["warnings"]:
                st.write(f"- {warning}")

st.divider()
st.header("🔎 Consultas")

repository = get_repository()

try:
    query_type = st.selectbox(
        "Consultar por",
        options=[
            "Identificación / NIT",
            "Código contable",
            "Cuenta contable",
        ],
    )

    search_value = st.text_input(
        "Valor de búsqueda",
        placeholder="Ejemplo: 1234567890 / 11050501 / Caja general",
    ).strip()

    if search_value:
        if query_type == "Identificación / NIT":
            normalized = repository.normalize_identification(search_value)
            summary = repository.get_third_party(normalized)

            if not summary:
                st.info("No se encontró información para esa identificación.")
            else:
                st.subheader(summary.get("nombre_tercero") or normalized)

                metrics1 = st.columns(2)
                metrics1[0].metric("Identificación", normalized)
                metrics1[1].metric(
                    "Movimientos",
                    summary.get("total_movimientos", 0),
                )
                metrics2 = st.columns(2)
                metrics2[0].metric(
                    "Débito",
                    f"{summary.get('total_debito', 0):,.2f}",
                )
                metrics2[1].metric(
                    "Crédito",
                    f"{summary.get('total_credito', 0):,.2f}",
                )

                movements = repository.get_movements(normalized)
                if movements:
                    st.dataframe(
                        movements,
                        use_container_width=True,
                        hide_index=True,
                    )

        elif query_type == "Código contable":
            summary = repository.get_account_by_code(search_value)

            if not summary:
                st.info("No se encontró información para ese código contable.")
            else:
                st.subheader(f"Código contable: {summary['codigo_contable']}")

                metrics3 = st.columns(3)
                metrics3[0].metric(
                    "Código",
                    summary["codigo_contable"],
                )
                metrics3[1].metric(
                    "Movimientos",
                    summary.get("total_movimientos", 0),
                )
                metrics3[2].metric(
                    "Terceros",
                    summary.get("total_terceros", 0),
                )
                metrics4 = st.columns(2)
                metrics4[0].metric(
                    "Débito",
                    f"{summary.get('total_debito', 0):,.2f}",
                )
                metrics4[1].metric(
                    "Crédito",
                    f"{summary.get('total_credito', 0):,.2f}",
                )

                if summary.get("cuentas_contables"):
                    st.caption(
                        "Cuentas contables asociadas: "
                        + ", ".join(summary["cuentas_contables"])
                    )

                movements = repository.get_movements_by_account_code(search_value)
                if movements:
                    st.dataframe(
                        movements,
                        use_container_width=True,
                        hide_index=True,
                    )

        else:
            summary = repository.get_account_by_name(search_value)

            if not summary:
                st.info("No se encontró información para esa cuenta contable.")
            else:
                st.subheader(
                    f"Cuenta contable: {summary['cuenta_contable']}"
                )

                metrics5 = st.columns(3)
                metrics5[0].metric(
                    "Cuenta",
                    summary["cuenta_contable"],
                )
                metrics5[1].metric(
                    "Movimientos",
                    summary.get("total_movimientos", 0),
                )
                metrics5[2].metric(
                    "Terceros",
                    summary.get("total_terceros", 0),
                )
                metrics6 = st.columns(1)
                metrics6[0].metric(
                    "Débito",
                    f"{summary.get('total_debito', 0):,.2f}",
                )
                metrics6[1].metric(
                    "Crédito",
                    f"{summary.get('total_credito', 0):,.2f}",
                )

                if summary.get("codigos_contables"):
                    st.caption(
                        "Códigos contables asociados: "
                        + ", ".join(summary["codigos_contables"])
                    )

                movements = repository.get_movements_by_account_name(search_value)
                if movements:
                    st.dataframe(
                        movements,
                        use_container_width=True,
                        hide_index=True,
                    )
except Exception as exc:
    st.warning(
        "No se pudo consultar MongoDB. Verifica MONGODB_URI y la conectividad."
    )
    st.caption(str(exc))



st.divider()
st.header("📘 Reporte general por código contable")

try:
    account_report = repository.get_account_code_report()

    if not account_report:
        st.info("No hay información disponible para el reporte general.")
    else:
        report_df = pd.DataFrame(account_report).rename(
            columns={
                "codigo_contable": "Código contable",
                "cuenta_contable": "Cuenta contable",
                "total_movimientos": "Movimientos",
                "total_terceros": "Terceros",
                "total_debito": "Débito",
                "total_credito": "Crédito",
                "total_saldo_movimiento": "Saldo movimiento",
            }
        )

        for column in ["Débito", "Crédito", "Saldo movimiento"]:
            report_df[column] = report_df[column].apply(format_decimal_es)

        st.dataframe(
            report_df,
            use_container_width=True,
            hide_index=True,
        )
except Exception as exc:
    st.warning(
        "No se pudo construir el reporte general por código contable."
    )
    st.caption(str(exc))