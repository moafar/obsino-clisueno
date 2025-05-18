# Cloud Function: Upload to BigQuery (Transactional)

Esta función permite recibir datos JSON desde un cliente (por ejemplo, una hoja de cálculo de Google Sheets) y cargarlos en una tabla de BigQuery, aplicando validaciones y asegurando un comportamiento transaccional: **si alguna fila genera error, ninguna se inserta**.

Desplegar con:
gcloud functions deploy upload_to_bigquery   --runtime python310   --trigger-http   --allow-unauthenticated   --entry-point upload_to_bigquery   --source .   --project=observatorio-ino-1   --region=us-central1
---

## 🚀 Parámetros

La función debe ser llamada por HTTP y requiere los siguientes parámetros **en la URL**:

- `table`: nombre de la tabla destino en BigQuery (sin comillas).
- `date_field`: nombre del campo dentro del JSON que contiene la fecha para partición.

---

## 📦 Estructura esperada del JSON

La carga debe ser un array de objetos. Cada objeto representa una fila.  
Cada objeto debe incluir:

- `uuid`: identificador único por fila. Se usa para evitar duplicados.
- `<date_field>`: un campo con fecha en formato `YYYY-MM-DD`, usado para la partición.

Ejemplo:

```json
[
  {
    "uuid": "abc-123",
    "fecha_estudio": "2024-05-01",
    "empresa": "Colsanitas",
    "solicita": "Dra. Rivera"
  },
  ...
]
```

---

## ✅ Lógica de validación

1. **Verifica que `uuid` no esté ya en BigQuery.**
2. **Valida y formatea la fecha de partición.**
3. **Limpia los campos vacíos (los convierte a `null`).**
4. **Agrega un timestamp (`migrado`) a cada registro.**
5. Si todo es válido, **inserta todos los registros**.
6. Si ocurre un error en alguna fila, **no se inserta ninguna**.

---

## 🔄 Respuestas posibles

- `200 OK`: Registros insertados o ya existentes.
- `400 Error`: Faltan parámetros, datos inválidos o inserción fallida.
- `500 Error`: Excepción inesperada.

---

## 🧪 Uso típico desde Apps Script

```javascript
const url = "https://<region>-<project>.cloudfunctions.net/upload_to_bigquery?table=tbl_basal2&date_field=fecha_estudio";

const response = UrlFetchApp.fetch(url, {
  method: "post",
  contentType: "application/json",
  payload: JSON.stringify(datos),
  muteHttpExceptions: true
});
```

---

## 🛡️ Requisitos del esquema en BigQuery

La tabla debe contener los campos `uuid`, el campo de fecha (`DATE`) y cualquier otro campo esperado por los objetos JSON. También debe tener partición activada por el campo de fecha.