"""
Cloud Function HTTP que recibe un arreglo JSON desde un cliente (como Google Apps Script),
valida su contenido y lo inserta en una tabla de BigQuery. El comportamiento es transaccional:
si alguna fila presenta errores al insertarse, ninguna fila es escrita.

Funcionamiento principal:
- Recibe el cuerpo de la petición como JSON.
- Requiere parámetros en la URL:
    - table: nombre de la tabla destino en BigQuery.
    - date_field: nombre del campo que contiene la fecha de partición.
- Verifica que los registros no estén ya en BigQuery (según su UUID).
- Detecta duplicados dentro del lote y los rechaza.
- Valida que el campo de fecha sea válido y lo formatea a YYYY-MM-DD.
- Elimina campos vacíos y agrega marca de tiempo ('migrado').
- Inserta solo si **todos** los registros son nuevos y válidos.
- Si hay errores de inserción o registros ya existentes, no guarda ninguno.

Uso típico desde Google Sheets:
- Convertir cada fila en un objeto con encabezados como claves.
- Validar previamente las fechas y UUIDs.
- Enviar el arreglo JSON por POST a la URL pública de la función.
- La columna "migrado" **no debe estar presente en la hoja**, ya que se calcula internamente.
"""

import functions_framework # type: ignore
from flask import jsonify, request # type: ignore
from google.cloud import bigquery
from datetime import datetime, timezone, date
import re
from collections import Counter

@functions_framework.http
def upload_to_bigquery(request):
    try:
        data = request.get_json()
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

        uuids_recibidos = []
        fechas_unicas = set()
        for item in data:
            uuid = item.get("uuid")
            fecha_raw = item.get(campo_fecha)
            if uuid and fecha_raw:
                uuids_recibidos.append(uuid)
                try:
                    fecha = date.fromisoformat(str(fecha_raw)[:10])
                    fechas_unicas.add(fecha.isoformat())
                except ValueError:
                    return jsonify({"status": "error", "message": f"'{campo_fecha}' inválida en UUID {uuid}"}), 400

        if not uuids_recibidos:
            return jsonify({"status": "skip", "message": "No se recibieron UUIDs válidos"}), 200

        contador = Counter(uuids_recibidos)
        duplicados_lote = [uuid for uuid, count in contador.items() if count > 1]
        if duplicados_lote:
            return jsonify({
                "status": "error",
                "message": "UUIDs duplicados dentro del lote recibido",
                "duplicados": duplicados_lote[:10],
                "detalle": f"Se encontraron {len(duplicados_lote)} UUIDs duplicados en el lote. La operación fue cancelada."
            }), 400

        fechas_clause = " OR ".join([f"{campo_fecha} = '{f}'" for f in fechas_unicas])
        uuids_clause = ", ".join([f"'{u}'" for u in uuids_recibidos])

        query = f"""
            SELECT uuid FROM `{table_id}`
            WHERE ({fechas_clause}) AND uuid IN ({uuids_clause})
        """
        result = client.query(query).result()
        existentes = {row["uuid"] for row in result}

        if existentes:
            return jsonify({
                "status": "error",
                "message": "Se encontraron UUIDs ya existentes en BigQuery. La operación fue cancelada.",
                "existentes": list(existentes)[:10]
            }), 400

        for item in data:
            fecha_raw = item.get(campo_fecha)
            fecha = date.fromisoformat(str(fecha_raw)[:10])
            item[campo_fecha] = fecha.isoformat()
            for k, v in item.items():
                if v == "":
                    item[k] = None
            item['migrado'] = now

        errors = client.insert_rows_json(table_id, data)
        if errors:
            return jsonify({
                "status": "error",
                "message": "Error al insertar. Ningún registro fue guardado.",
                "details": errors
            }), 400

        return jsonify({
            "status": "success",
            "rows_inserted": len(data)
        })

    except Exception as e:
        return jsonify({"status": "exception", "details": str(e)}), 500
