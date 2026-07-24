# Auxiliar de terceros por NIT + MongoDB

Aplicación Streamlit para procesar múltiples archivos `.xlsx` de auxiliares contables y persistir movimientos normalizados en MongoDB.

## Qué reconoce

El reporte puede contener filas jerárquicas:

```text
Nombre del tercero: 1234567890 JUAN DE LOS PALOTES
Cuenta contable: 11050501 Caja general
1234567890 | 0 | JUAN DE LOS PALOTES | 11050501 | Caja general | RP-449-10 | 30/06/2025 | ... 
```

Reglas:

- `Nombre del tercero:` actualiza el tercero actual.
- `Cuenta contable:` actualiza la cuenta actual.
- Una fila con `Comprobante` y `Fecha elaboración` se considera movimiento real.
- Las filas resumen no se insertan como movimientos.
- Las identificaciones se mantienen como texto para evitar pérdida de precisión.
- Los movimientos se deduplican mediante `movement_hash`.

## Instalación

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Instalar:

```bash
pip install -e ".[dev]"
```

Crear configuración:

```bash
copy .env.example .env
```

o:

```bash
cp .env.example .env
```

Editar `.env` y colocar la URI real de MongoDB.

## Ejecutar

```bash
streamlit run app.py
```

## Tests

```bash
pytest
```

## Colecciones

### `movements`

Contiene movimientos individuales.

Índices:

- `identificacion + fecha_elaboracion`
- `identificacion + anio + codigo_contable`
- `movement_hash` único

### `third_parties`

Contiene un resumen agregado por identificación.

## Seguridad

No subas `.env` al repositorio. Usa variables de entorno o secrets del entorno de despliegue.

## Nota sobre archivos

El cargador utiliza `st.file_uploader(..., accept_multiple_files=True)`. El usuario puede seleccionar varios archivos `.xlsx`; `TipoExt` limita cuántos se procesan.
# app-dictionary-nit-v01
# app-dictionary-nit-v01
