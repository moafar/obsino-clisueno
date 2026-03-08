"""Carga manual de Excel a BigQuery para la capa load.

Esta versión integrada reemplaza el enfoque HTTP de Cloud Function por ejecución
manual en consola, conservando validaciones clave:
- Duplicados dentro del lote
- Duplicados entre lote y tabla destino en BigQuery
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from google.cloud import bigquery


# =======================
# Utilidades base de consola y validación
# =======================
LOGGER: logging.Logger | None = None
LOG_FILE_PATH: Path | None = None


def setup_logging(flow_name: str) -> Path:
    # Configura logging en consola y archivo para trazabilidad operativa.
    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    normalized_flow = (flow_name or "load").strip().lower().replace(" ", "_")
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file_path = logs_dir / f"load_{normalized_flow}_{timestamp}.log"

    logger = logging.getLogger("3_load")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s $$ %(levelname)s $$ %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    global LOGGER, LOG_FILE_PATH
    LOGGER = logger
    LOG_FILE_PATH = log_file_path

    LOGGER.info("Inicio del proceso 3_load")
    LOGGER.info("Log file: %s", log_file_path)
    return log_file_path


def log(message: str) -> None:
    if LOGGER:
        LOGGER.info(message)
        return
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def die(message: str) -> None:
    raise RuntimeError(message)


def validate_identifier(name: str, label: str) -> None:
    # Evita inyección o nombres inválidos al construir identificadores SQL.
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        die(f"{label} no válido: {name}")


@dataclass(frozen=True)
class LoaderConfig:
    # Configuración declarativa de una ejecución manual de carga.
    project_id: str
    dataset_id: str
    table_id: str
    write_disposition: str
    service_account_json: Path
    source_excel_path: Path
    source_sheet_name: str
    schema_yaml_path: Path
    schema_path_in_yaml: str
    schema_description: str | None
    uuid_field: str
    date_field: str | None
    migrated_field: str | None

    @property
    def table_fqn(self) -> str:
        return f"{self.project_id}.{self.dataset_id}.{self.table_id}"


# Estructura aplanada: este script vive en 3_load/, y usa configuración por flujo.
BASE_DIR = Path(__file__).resolve().parents[1]
FLOW_CONFIG_PATHS: dict[str, Path] = {
    "psg": BASE_DIR / "3_load" / "config" / "psg.yaml",
    "xpap": BASE_DIR / "3_load" / "config" / "xpap.yaml",
}
SUPPORTED_INPUT_EXTENSIONS = {".xlsx", ".xls", ".csv"}
STAGING_DIR = BASE_DIR / "staging"


def _transformed_prefix(flow: str) -> str:
    return f"extract_{flow}_"


def _is_flow_transformed_file(path: Path, flow: str) -> bool:
    if not path.is_file() or path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        return False

    stem = path.stem
    return stem.startswith(_transformed_prefix(flow)) and stem.endswith("_transformed")


def _discover_latest_input(flow: str) -> Path:
    source_dir = STAGING_DIR
    if not source_dir.exists():
        die(
            "No se especifico --input y no existe el directorio de staging esperado: "
            f"{source_dir}"
        )

    candidates = [
        path
        for path in source_dir.iterdir()
        if _is_flow_transformed_file(path, flow)
    ]
    if not candidates:
        die(
            "No se especifico --input y no hay archivos candidatos para el flow en: "
            f"{source_dir}. Se esperaba un archivo con formato extract_<flow>_*_transformed"
        )

    # Se usa el archivo mas recientemente modificado para evitar ambiguedad operativa.
    return max(candidates, key=lambda item: item.stat().st_mtime)


def _resolve_input_path(raw_input_path: str) -> Path:
    input_path = Path(raw_input_path).expanduser()
    if not input_path.is_absolute():
        input_path = BASE_DIR / input_path
    return input_path.resolve()


def _validate_input_in_staging(flow: str, input_path: Path) -> None:
    expected_dir = STAGING_DIR.resolve()
    try:
        input_path.resolve().relative_to(expected_dir)
    except ValueError:
        die(
            "La entrada de 3_load debe venir desde staging del flow. "
            f"Directorio esperado: {expected_dir}. Archivo recibido: {input_path}"
        )

    if not input_path.exists():
        die(
            "El archivo de entrada no existe en staging. "
            f"Archivo recibido: {input_path}"
        )
    if not input_path.is_file():
        die(
            "La ruta de entrada no es un archivo válido. "
            f"Archivo recibido: {input_path}"
        )

    if not _is_flow_transformed_file(input_path, flow):
        die(
            "El archivo de entrada no cumple la convención esperada para este flow. "
            f"Se esperaba 'extract_{flow}_..._transformed' y se recibió: {input_path.name}"
        )


def parse_cli_args() -> tuple[str, Path]:
    # Selecciona flujo y ruta de entrada desde CLI.
    parser = argparse.ArgumentParser(description="Carga manual a BigQuery")
    parser.add_argument(
        "input_positional",
        nargs="?",
        help="Ruta del Excel a cargar (argumento posicional)",
    )
    parser.add_argument(
        "--flow",
        required=True,
        choices=sorted(FLOW_CONFIG_PATHS.keys()),
        help="Flujo a ejecutar (define el YAML de configuración fijo)",
    )
    parser.add_argument(
        "--input",
        required=False,
        help=(
            "Ruta del Excel a cargar (relativa a la raiz del proyecto o absoluta). "
            "Si se omite, usa autodiscovery en staging/ filtrando por extract_<flow>_*_transformed."
        ),
    )
    args = parser.parse_args()
    raw_input = args.input or args.input_positional

    selected_flow = str(args.flow)

    if raw_input:
        resolved_input = _resolve_input_path(str(raw_input))
    else:
        resolved_input = _discover_latest_input(selected_flow)

    _validate_input_in_staging(selected_flow, resolved_input)

    return selected_flow, resolved_input


def resolve_config_yaml_path(flow: str) -> Path:
    config_yaml_path = FLOW_CONFIG_PATHS.get(flow)
    if not config_yaml_path:
        available_flows = ", ".join(sorted(FLOW_CONFIG_PATHS.keys()))
        die(f"Flujo no soportado: {flow}. Flujos válidos: {available_flows}")
    return config_yaml_path


def load_runtime_config(config_yaml_path: Path, source_excel_path: Path) -> LoaderConfig:
    # Carga configuración declarativa equivalente a la "sección 1" del script manual.
    if not config_yaml_path.exists():
        die(f"No existe el archivo de configuración: {config_yaml_path}")

    with config_yaml_path.open("r", encoding="utf-8") as file_handle:
        raw_config = yaml.safe_load(file_handle)

    if not isinstance(raw_config, dict) or not raw_config:
        die("El YAML de configuración debe ser un diccionario con claves de configuración")

    required_keys = [
        "project_id",
        "dataset_id",
        "table_id",
        "write_disposition",
        "service_account_json",
        "source_sheet_name",
    ]
    if "schema_yaml_path" not in raw_config and "shared_schema_yaml_path" not in raw_config:
        die("Debe definir 'schema_yaml_path' o 'shared_schema_yaml_path' en el YAML de configuración")
    missing = [key for key in required_keys if key not in raw_config]
    if missing:
        die(f"Faltan claves requeridas en YAML de configuración: {', '.join(missing)}")

    write_disposition = str(raw_config["write_disposition"]).strip().upper()
    if write_disposition not in {"WRITE_APPEND", "WRITE_TRUNCATE"}:
        die("'write_disposition' debe ser WRITE_APPEND o WRITE_TRUNCATE")

    raw_schema_path = raw_config.get("shared_schema_yaml_path", raw_config.get("schema_yaml_path", ""))

    return LoaderConfig(
        project_id=str(raw_config["project_id"]).strip(),
        dataset_id=str(raw_config["dataset_id"]).strip(),
        table_id=str(raw_config["table_id"]).strip(),
        write_disposition=write_disposition,
        service_account_json=BASE_DIR / str(raw_config["service_account_json"]).strip(),
        source_excel_path=source_excel_path,
        source_sheet_name=str(raw_config["source_sheet_name"]).strip(),
        schema_yaml_path=BASE_DIR / str(raw_schema_path).strip(),
        schema_path_in_yaml=str(raw_config.get("schema_path_in_yaml", "")).strip(),
        schema_description=(
            str(raw_config["schema_description"]).strip()
            if raw_config.get("schema_description") not in (None, "")
            else None
        ),
        uuid_field=str(raw_config.get("uuid_field", "basal_uuid")).strip(),
        date_field=(
            str(raw_config["date_field"]).strip()
            if raw_config.get("date_field") not in (None, "")
            else None
        ),
        migrated_field=(
            str(raw_config["migrated_field"]).strip()
            if raw_config.get("migrated_field") not in (None, "")
            else None
        ),
    )


TYPE_MAP = {
    "STRING": "STRING",
    "FLOAT": "FLOAT64",
    "FLOAT64": "FLOAT64",
    "INTEGER": "INT64",
    "INT": "INT64",
    "INT64": "INT64",
    "DATETIME": "DATETIME",
    "TIMESTAMP": "TIMESTAMP",
    "BOOLEAN": "BOOL",
    "BOOL": "BOOL",
}


# =======================
# UI de consola: mostrar configuración y pedir confirmación
# =======================
def show_configuration(config: LoaderConfig) -> None:
    print("\nCONFIGURACIÓN DE EJECUCIÓN")
    print("-" * 90)
    print("Proyecto           :", config.project_id)
    print("Dataset            :", config.dataset_id)
    print("Tabla              :", config.table_id)
    print("Archivo origen     :", str(config.source_excel_path))
    print("Hoja Excel         :", config.source_sheet_name)
    print("Schema YAML        :", str(config.schema_yaml_path))
    print("Schema path YAML   :", config.schema_path_in_yaml or "(raíz)")
    print("Schema origen      :", config.schema_description or "(local)")
    print("Service Account    :", str(config.service_account_json))
    print("Campo UUID         :", config.uuid_field)
    print("Campo fecha        :", config.date_field or "(sin validación de fecha)")
    print("Campo migrado      :", config.migrated_field or "(sin marca de migración)")
    print("-" * 90)

    print("\n>> DESTINO BQ")
    print(f"   {config.table_fqn}")

    print("\n>> WRITE_DISPOSITION")
    print(f"   {config.write_disposition}")

    if config.write_disposition == "WRITE_TRUNCATE":
        print("\n⚠️  ATENCIÓN: WRITE_TRUNCATE BORRA COMPLETAMENTE la tabla antes de cargar.")
    else:
        print("\nWRITE_APPEND agrega filas sin borrar datos existentes.")


def confirm_execution() -> None:
    user_input = input("Digite 1 para continuar, cualquier otra tecla para abortar: ")
    if user_input != "1":
        die("Carga abortada por usuario")


def validate_paths(config: LoaderConfig) -> None:
    # Verifica que todos los insumos físicos existan antes de autenticar/cargar.
    if not config.service_account_json.exists():
        die(f"No existe el JSON de la Service Account: {config.service_account_json}")
    if not config.source_excel_path.exists():
        die(f"No existe el Excel de origen: {config.source_excel_path}")
    if not config.schema_yaml_path.exists():
        die(f"No existe el archivo de schema YAML: {config.schema_yaml_path}")


def authenticate_bigquery(config: LoaderConfig) -> bigquery.Client:
    # Configura credenciales y valida conectividad mínima con un SELECT 1.
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(config.service_account_json)
    client = bigquery.Client(project=config.project_id)
    client.query("SELECT 1").result()
    return client


def _resolve_nested_path(payload: Any, dotted_path: str) -> Any:
    current = payload
    for segment in [part.strip() for part in dotted_path.split(".") if part.strip()]:
        if not isinstance(current, dict) or segment not in current:
            die(f"No existe la ruta de schema '{dotted_path}' en el YAML")
        current = current[segment]
    return current


def _coerce_schema_mapping(schema_payload: Any) -> dict[str, str]:
    if not isinstance(schema_payload, dict) or not schema_payload:
        die("El schema resuelto debe ser un diccionario no vacío de variable: tipo")

    normalized: dict[str, str] = {}
    for column, field_type in schema_payload.items():
        normalized[str(column)] = str(field_type).upper().strip()
    return normalized


def load_schema(schema_yaml_path: Path, schema_path_in_yaml: str) -> dict[str, str]:
    # Lee el YAML y normaliza tipos para simplificar el procesamiento posterior.
    with schema_yaml_path.open("r", encoding="utf-8") as file_handle:
        schema_yaml = yaml.safe_load(file_handle)

    if schema_path_in_yaml:
        schema_payload = _resolve_nested_path(schema_yaml, schema_path_in_yaml)
        return _coerce_schema_mapping(schema_payload)

    # Compatibilidad: formato plano variable: tipo y auto-detección de formato transform.
    if isinstance(schema_yaml, dict) and "schema" in schema_yaml:
        schema_payload = _resolve_nested_path(schema_yaml, "schema.output.columns")
        return _coerce_schema_mapping(schema_payload)

    return _coerce_schema_mapping(schema_yaml)


def build_bq_schema(schema_yaml: dict[str, str]) -> list[bigquery.SchemaField]:
    # Convierte el schema declarativo (YAML) al formato requerido por BigQuery.
    bq_schema: list[bigquery.SchemaField] = []
    for column, field_type in schema_yaml.items():
        if field_type not in TYPE_MAP:
            die(f"Tipo no soportado en schema YAML: {column}: {field_type}")
        bq_schema.append(bigquery.SchemaField(column, TYPE_MAP[field_type]))
    return bq_schema


def read_source_dataset(config: LoaderConfig, expected_columns: list[str]) -> pd.DataFrame:
    # Carga dataset de entrada y fuerza estructura esperada (rechaza faltantes, ignora extras).
    source_suffix = config.source_excel_path.suffix.lower()
    if source_suffix == ".csv":
        dataframe = pd.read_csv(config.source_excel_path)
    elif source_suffix in {".xlsx", ".xls"}:
        dataframe = pd.read_excel(config.source_excel_path, sheet_name=config.source_sheet_name)
    else:
        die(
            "Extensión de archivo no soportada para carga. "
            f"Extensión recibida: {config.source_excel_path.suffix}"
        )

    missing_columns = [column for column in expected_columns if column not in dataframe.columns]
    extra_columns = [column for column in dataframe.columns if column not in expected_columns]

    if missing_columns:
        print("\nERROR: faltan columnas requeridas:")
        for column in missing_columns:
            print(" -", column)
        die("Carga abortada por columnas faltantes")

    if extra_columns:
        log("Aviso: columnas extra serán ignoradas")
        for column in extra_columns:
            print(" -", column)

    return dataframe[expected_columns].copy()


def cast_dataframe(dataframe: pd.DataFrame, schema_yaml: dict[str, str]) -> pd.DataFrame:
    # Aplica coerción de tipos columna a columna según el schema YAML.
    for column, field_type in schema_yaml.items():
        if field_type in ("FLOAT", "FLOAT64"):
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")
        elif field_type in ("INTEGER", "INT", "INT64"):
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce").astype("Int64")
        elif field_type == "DATETIME":
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")
        elif field_type == "TIMESTAMP":
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce", utc=True)
        elif field_type == "STRING":
            dataframe[column] = dataframe[column].astype("string")
        elif field_type in ("BOOLEAN", "BOOL"):
            dataframe[column] = dataframe[column].astype("boolean")
    return dataframe


def validate_date_field(dataframe: pd.DataFrame, date_field: str | None) -> pd.DataFrame:
    # Valida y normaliza DATETIME al formato estándar esperado por BQ.
    if not date_field:
        return dataframe
    if date_field not in dataframe.columns:
        die(f"El campo de fecha configurado no existe en el lote: {date_field}")

    parsed = pd.to_datetime(dataframe[date_field], errors="coerce")
    invalid_mask = dataframe[date_field].notna() & parsed.isna()
    if invalid_mask.any():
        invalid_index = invalid_mask[invalid_mask].index[0]
        invalid_value = dataframe.loc[invalid_index, date_field]
        die(f"'{date_field}' inválida en fila {invalid_index}: {invalid_value}")

    # Mantener datetime64 evita degradar la columna a object y romper pyarrow.
    dataframe[date_field] = parsed
    return dataframe


def extract_uuid_values(dataframe: pd.DataFrame, uuid_field: str) -> list[str]:
    # Extrae UUID válidos no vacíos para validaciones de unicidad.
    if uuid_field not in dataframe.columns:
        die(f"El campo UUID configurado no existe en el lote: {uuid_field}")

    uuid_values: list[str] = []
    for value in dataframe[uuid_field].tolist():
        if pd.isna(value):
            continue
        value_str = str(value).strip()
        if value_str:
            uuid_values.append(value_str)
    return uuid_values


def validate_batch_duplicates(uuid_values: list[str], uuid_field: str) -> None:
    # Cancela el proceso si hay duplicados dentro del lote local.
    if not uuid_values:
        die(f"No se recibieron valores válidos en {uuid_field}")

    counts = Counter(uuid_values)
    duplicated_values = sorted(uuid for uuid, count in counts.items() if count > 1)
    if duplicated_values:
        log_detail_message = (
            f"ver detalle de UUID repetidos en el log: "
            f"{LOG_FILE_PATH if LOG_FILE_PATH else '(log no disponible)'}"
        )
        log(
            f"Rechazo por duplicados en lote: {len(duplicated_values)} UUID repetidos "
            f"en el campo {uuid_field}"
        )
        log("Detalle completo de UUID duplicados detectados en el lote:")
        for duplicated_uuid in duplicated_values:
            log(f"UUID_REPETIDO [LOTE]: {duplicated_uuid}")

        print("\nERROR: se encontraron duplicados dentro del lote:")
        for uuid in duplicated_values[:10]:
            print(" -", uuid)
        print(log_detail_message)
        die(
            f"Se encontraron {len(duplicated_values)} valores duplicados en '{uuid_field}'. "
            f"La operación fue cancelada; {log_detail_message}."
        )


def find_existing_uuids(
    client: bigquery.Client,
    table_fqn: str,
    uuid_field: str,
    uuid_values: list[str],
    chunk_size: int = 5000,
) -> set[str]:
    # Consulta la tabla destino en bloques para detectar UUID ya existentes.
    existing_uuids: set[str] = set()
    for index in range(0, len(uuid_values), chunk_size):
        chunk_values = uuid_values[index : index + chunk_size]
        query = f"""
            SELECT {uuid_field}
            FROM `{table_fqn}`
            WHERE {uuid_field} IN UNNEST(@uuids)
        """
        query_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ArrayQueryParameter("uuids", "STRING", chunk_values)]
        )
        query_result = client.query(query, job_config=query_config).result()
        existing_uuids.update(str(row[uuid_field]) for row in query_result)
    return existing_uuids


def add_migration_mark(dataframe: pd.DataFrame, migrated_field: str | None) -> pd.DataFrame:
    # Agrega timestamp UTC de migración si la columna existe en el lote.
    if not migrated_field or migrated_field not in dataframe.columns:
        return dataframe
    current_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    dataframe[migrated_field] = current_utc
    return dataframe


def normalize_empty_values(dataframe: pd.DataFrame, schema_yaml: dict[str, str]) -> pd.DataFrame:
    # Normaliza vacíos de forma tipada para preservar dtypes compatibles con pyarrow.
    for column, field_type in schema_yaml.items():
        if field_type == "STRING":
            dataframe[column] = dataframe[column].replace(r"^\s*$", pd.NA, regex=True).astype("string")
        elif field_type in ("FLOAT", "FLOAT64"):
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")
        elif field_type in ("INTEGER", "INT", "INT64"):
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce").astype("Int64")
        elif field_type == "DATETIME":
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")
        elif field_type == "TIMESTAMP":
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce", utc=True)
        elif field_type in ("BOOLEAN", "BOOL"):
            dataframe[column] = dataframe[column].astype("boolean")
    return dataframe


def move_loaded_input_file(source_path: Path, _flow: str) -> Path:
    # Mueve el archivo cargado exitosamente en staging con sufijo _loaded.
    destination_dir = STAGING_DIR
    destination_dir.mkdir(parents=True, exist_ok=True)

    base_name = source_path.stem
    extension = source_path.suffix
    destination_path = destination_dir / f"{base_name}_loaded{extension}"

    # Evita sobrescribir archivos previos si ya existe un nombre igual.
    if destination_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination_path = destination_dir / f"{base_name}_loaded_{timestamp}{extension}"

    shutil.move(str(source_path), str(destination_path))

    if not destination_path.exists():
        die(f"No se pudo confirmar el archivo movido en destino: {destination_path}")

    if source_path.exists():
        # Salvaguarda: si el origen persiste tras el move, se elimina para evitar reprocesos.
        source_path.unlink()
        log(f"Se eliminó archivo remanente en input tras mover: {source_path}")

    return destination_path


def run(config: LoaderConfig, flow: str) -> None:
    log("Iniciando carga manual a BigQuery")

    # 1) Validaciones tempranas de nombres de identificadores.
    validate_identifier(config.dataset_id, "Dataset")
    validate_identifier(config.table_id, "Tabla")
    validate_identifier(config.uuid_field, "Campo UUID")
    if config.date_field:
        validate_identifier(config.date_field, "Campo fecha")
    if config.migrated_field:
        validate_identifier(config.migrated_field, "Campo migrado")

    # 2) Transparencia operativa: mostrar configuración y pedir confirmación humana.
    show_configuration(config)
    confirm_execution()
    validate_paths(config)

    # 3) Autenticación y verificación de acceso a BigQuery.
    log("Configurando autenticación con Service Account")
    client = authenticate_bigquery(config)
    log("Autenticación BigQuery verificada")

    # 4) Cargar definición de esquema declarativo desde YAML.
    log("Cargando esquema desde YAML")
    schema_yaml = load_schema(config.schema_yaml_path, config.schema_path_in_yaml)
    expected_columns = list(schema_yaml.keys())
    bq_schema = build_bq_schema(schema_yaml)
    log(f"Esquema leído con {len(expected_columns)} campos")

    # 5) Ingestar Excel con control estricto de columnas.
    log("Leyendo archivo Excel")
    dataframe = read_source_dataset(config, expected_columns)
    log(f"Excel leído: {len(dataframe)} filas, {len(dataframe.columns)} columnas")

    # 6) Estandarizar y limpiar datos previo a validaciones de unicidad.
    log("Aplicando casting y validaciones de formato")
    dataframe = cast_dataframe(dataframe, schema_yaml)
    dataframe = validate_date_field(dataframe, config.date_field)
    dataframe = add_migration_mark(dataframe, config.migrated_field)
    dataframe = normalize_empty_values(dataframe, schema_yaml)

    # 7) Evitar duplicados dentro del lote recibido.
    log("Validando duplicados en el lote")
    uuid_values = extract_uuid_values(dataframe, config.uuid_field)
    validate_batch_duplicates(uuid_values, config.uuid_field)

    # 8) Evitar duplicados contra la tabla destino (solo en modo APPEND).
    if config.write_disposition == "WRITE_APPEND":
        log("Validando duplicados entre lote y BigQuery")
        existing_uuids = find_existing_uuids(client, config.table_fqn, config.uuid_field, uuid_values)
        if existing_uuids:
            sorted_existing_uuids = sorted(existing_uuids)
            log_detail_message = (
                f"ver detalle de UUID repetidos en el log: "
                f"{LOG_FILE_PATH if LOG_FILE_PATH else '(log no disponible)'}"
            )
            log(
                f"Rechazo por duplicados en BigQuery: {len(sorted_existing_uuids)} UUID ya existen "
                f"en {config.table_fqn}"
            )
            log("Detalle completo de UUID duplicados detectados en BigQuery:")
            for duplicated_uuid in sorted_existing_uuids:
                log(f"UUID_REPETIDO [BQ]: {duplicated_uuid}")

            print("\nERROR: se encontraron UUID ya existentes en BigQuery:")
            for uuid in sorted_existing_uuids[:10]:
                print(" -", uuid)
            print(log_detail_message)
            die(
                f"Se encontraron {len(sorted_existing_uuids)} UUID ya existentes en la tabla destino. "
                f"La operación fue cancelada; {log_detail_message}."
            )
    else:
        log("WRITE_TRUNCATE: se omite validación contra existentes en BigQuery")

    # 9) Ejecutar carga final en BigQuery.
    log("Iniciando carga a BigQuery")
    job_config = bigquery.LoadJobConfig(
        schema=bq_schema,
        write_disposition=config.write_disposition,
    )
    load_job = client.load_table_from_dataframe(dataframe, config.table_fqn, job_config=job_config)
    load_job.result()

    log(f"Carga finalizada: {load_job.output_rows} filas en {config.table_fqn}")

    moved_path = move_loaded_input_file(config.source_excel_path, flow)
    log(f"Archivo de entrada movido a: {moved_path}")


if __name__ == "__main__":
    try:
        selected_flow, selected_input_path = parse_cli_args()
        setup_logging(selected_flow)
        selected_config_path = resolve_config_yaml_path(selected_flow)
        log(f"Flujo seleccionado: {selected_flow}")
        log(f"Excel de entrada: {selected_input_path}")
        log(f"YAML de configuración: {selected_config_path}")
        runtime_config = load_runtime_config(selected_config_path, selected_input_path)
        run(runtime_config, selected_flow)
    except Exception as error:
        if LOGGER:
            LOGGER.exception("ERROR: %s", error)
        else:
            log(f"ERROR: {error}")
        raise
