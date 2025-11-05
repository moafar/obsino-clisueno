"""
Cloud Function HTTP que recibe un arreglo JSON desde un cliente (por ejemplo, Google Apps Script),
valida su contenido y lo inserta en una tabla de BigQuery.

Notas:
- Usa 'basal_uuid' como identificador.
- 'date_field' se espera como DATETIME ('YYYY-MM-DD HH:MM:SS').
- La verificación de existentes se hace por basal_uuid (y por la fecha si se provee).
- insert_rows_json no es atómico: puede haber inserciones parciales.
"""

import functions_framework  # type: ignore
from flask import jsonify, request  # type: ignore
from google.cloud import bigquery
from datetime import datetime, timezone
import re
from collections import Counter

@functions_framework.http
def upload_to_bigquery(request):
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, list):
            return jsonify({"status": "error", "message": "El cuerpo debe ser un arreglo JSON"}), 400

        now = datetime.now(timezone.utc).isoformat()

        client = bigquery.Client()
        project_id = "observatorio-ino-1"
        dataset_id = "clinica_sueno"

        tabla_destino = request.args.get("table")
        if not tabla_destino:
            return jsonify({"status": "error", "message": "Parámetro 'table' requerido"}), 400
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", tabla_destino):
            return jsonify({"status": "error", "message": "Nombre de tabla no válido"}), 400

        campo_fecha = request.args.get("date_field")
        if not campo_fecha:
            return jsonify({"status": "error", "message": "Parámetro 'date_field' requerido"}), 400
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", campo_fecha):
            return jsonify({"status": "error", "message": "Nombre de campo de fecha no válido"}), 400

        table_id = f"{project_id}.{dataset_id}.{tabla_destino}"
        UUID_FIELD = "basal_uuid"

        # Recolecta uuids y fechas (como DATE para el filtro)
        uuids_recibidos = []
        fechas_unicas = set()
        for item in data:
            uuid = item.get(UUID_FIELD)
            fecha_raw = item.get(campo_fecha)
            if uuid:
                uuids_recibidos.append(uuid)
            if fecha_raw:
                # fecha_raw esperado como 'YYYY-MM-DD HH:MM:SS' (DATETIME)
                try:
                    dt = datetime.strptime(str(fecha_raw), "%Y-%m-%d %H:%M:%S")
                    fechas_unicas.add(dt.date().isoformat())
                except ValueError:
                    return jsonify({"status": "error",
                                    "message": f"'{campo_fecha}' inválida en {UUID_FIELD} {uuid} (esperado 'YYYY-MM-DD HH:MM:SS')"}), 400

        if not uuids_recibidos:
            return jsonify({"status": "skip", "message": f"No se recibieron {UUID_FIELD} válidos"}), 200

        # Duplicados en el lote
        contador = Counter(uuids_recibidos)
        duplicados_lote = [u for u, c in contador.items() if c > 1]
        if duplicados_lote:
            return jsonify({
                "status": "error",
                "message": f"{UUID_FIELD} duplicados dentro del lote recibido",
                "duplicados": duplicados_lote[:10],
                "detalle": f"Se encontraron {len(duplicados_lote)} duplicados en el lote. La operación fue cancelada."
            }), 400

        # Consulta de existentes en BQ
        # Si hay fechas, filtra por DATE(campo_fecha); si no, omite el filtro de fecha.
        fechas_clause = " OR ".join([f"DATE({campo_fecha}) = '{f}'" for f in sorted(fechas_unicas)]) if fechas_unicas else "TRUE"
        uuids_clause = ", ".join([f"'{u}'" for u in uuids_recibidos]) or "''"

        query = f"""
            SELECT {UUID_FIELD}
            FROM `{table_id}`
            WHERE ({fechas_clause}) AND {UUID_FIELD} IN ({uuids_clause})
        """
        result = client.query(query).result()
        existentes = {row[UUID_FIELD] for row in result}

        if existentes:
            return jsonify({
                "status": "error",
                "message": f"Se encontraron {UUID_FIELD} ya existentes en BigQuery. La operación fue cancelada.",
                "existentes": list(existentes)[:10]
            }), 400

        # Transformación final: normaliza DATETIME y vacíos
        for item in data:
            # Normaliza datetime si viene
            fecha_raw = item.get(campo_fecha)
            if fecha_raw:
                try:
                    dt = datetime.strptime(str(fecha_raw), "%Y-%m-%d %H:%M:%S")
                    item[campo_fecha] = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return jsonify({"status": "error",
                                    "message": f"'{campo_fecha}' inválida en {UUID_FIELD} {item.get(UUID_FIELD)}"}), 400
            # "" -> None
            for k, v in list(item.items()):
                if v == "":
                    item[k] = None
            # marca de migración (requiere columna en BQ si quieres conservarla)
            item["basal_migrado"] = now

        # Inserción
        errors = client.insert_rows_json(table_id, data)
        if errors:
            return jsonify({
                "status": "error",
                "message": "Error al insertar (el streaming puede ser parcial). Revisa 'details'.",
                "details": errors
            }), 400

        return jsonify({"status": "success", "rows_inserted": len(data)})

    except Exception as e:
        return jsonify({"status": "exception", "details": str(e)}), 500
