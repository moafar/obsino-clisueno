# PT07 — Validación, integración y preparación del despliegue PSG

**Base revisada:** `5d5388c65a9faf1f5d73b50dcb06517b4bb634c4`, rama `integration/psg-evoluciones`, más los cambios locales de PT07 descritos aquí. Fecha: 2026-11-28. Marcador conservado: **v5.0.1**, cabecera de `CHANGELOG.md`; no existe un archivo VERSION independiente.

**Alcance:** E27 se valida localmente. E28 y E30 se preparan para ejecución posterior autorizada. E29 tiene revisión técnica completada y cierre formal pendiente. No se han usado documentos reales, BigQuery ni PRD. Los comandos de las secciones 5 y 7 son procedimientos futuros: **no se han ejecutado**. E24 continúa como deuda técnica; no se retiran CSV ni journals. No se implementan PT08/PT09.

## 1. Revisión integral y contratos

| Frontera / control | Resultado de revisión |
|---|---|
| Documentos → extracción/auditoría | DOC y RTF; identificación basal, rechazo individual normalizado y contabilizado una vez. Inventario, archivado y conciliación bloqueantes; calidad clínica numérica tolerada es advertencia. Auditoría integrada, sin MD5 de archivados o duplicados. |
| CSV crudo → transformación | 159 campos en nombre y orden del YAML; lectura como texto. UUID canónico y metadatos técnicos bloqueantes, incluso en filas descartadas. E19 conserva primera aparición en el orden de filas y, cuando se seleccionan varios CSV, orden lexicográfico de nombres. |
| Transformación → Parquet | 158 campos: 13 STRING, 31 INT, 113 FLOAT y 1 DATE lógico. PyArrow/Snappy, `string`, `Int64`, `Float64`, `datetime64[ns]`; Arrow `string`, `int64`, `double`, `timestamp[ns]`. Validación exacta antes de publicar sin reemplazo. |
| Parquet → BigQuery | Nombres, orden y tipos físicos estrictos. `load_table_from_dataframe()` con esquema YAML; DATE se convierte explícitamente mediante el esquema del cliente. UUID, ceros iniciales, NULL y JSON se conservan. Esquema físico esperado: 158 columnas NULLABLE, sin particionamiento por columna ni clustering (E21, evidencia declarada por el responsable; no consultada ahora). |
| Completitud | 124 indicadores lógicos DOC / 129 RTF, edad como un indicador. Cero presente. La medida sigue siendo de presencia extraída, no de validez clínica tras transformar. No hay umbral mínimo; el indicador técnico debe estar presente, ser finito y estar en 0–100. |
| Incidencias | Solo el transformador genera `meta_incidencias_calidad`; el auditor clasifica según campo sin modificar datos ni depender de ese JSON. Ausencia admitida de ID/fecha y conversiones toleradas siguen E16–E20. No se inventan identificadores ni fechas. |
| Idempotencia/carga | E23: UUID existentes omitidos, WRITE_APPEND, recibidos = omitidos + enviados, enviados = output_rows = insertados; sin trabajo cuando enviados = 0. E26 persiste identidad/plan antes de enviar y consulta trabajos inciertos. |
| Concurrencia/recuperación | Bloqueo global compartido por seis CLI, heredado por hijos, más bloqueos de archivado/tabla. READY reserva el destino y reconsulta UUID; prioridad determinista entre READY heredados. SUBMITTED/PENDING/UNKNOWN no se reenvían. Etapas confirmadas se verifican y omiten; inconsistencia deja `recovery_blocked`. |
| Persistencia | JSON por reemplazo sincronizado; Parquet por temporal validado/enlace sin reemplazo; journal documental previo al movimiento; cierre postcarga por enlace/retirada. Los artefactos y estados necesarios permanecen. |
| XPAP | Conserva XLSX, reglas y carga actuales; se incluyen regresiones de lectura, transformación y carga. Las modificaciones históricas de imports por separación de paquetes se distinguen de cambios de lógica. |

Se reutilizaron E05, E06–E07, E23, E34–E36 y E25–E26. No se repitieron benchmarks. Las garantías demostradas son locales y con BigQuery simulado; no equivalen a una validación operativa real.

## 2. Pruebas y entorno observado

Entorno DEV observado: Python 3.12.3, pandas 2.3.3, PyArrow 23.0.1, google-cloud-bigquery 3.40.1, openpyxl 3.1.5, striprtf 0.0.29 y PyYAML 6.0.3. `catdoc` disponible en `/usr/bin/catdoc`. `pip check`: **No broken requirements found**. No se instalaron dependencias. Los requirements se mantienen por capa; no fijan todas las versiones transitivas, por lo que otra instalación debe volver a verificarse.

Se ejecuta una sola batería con cuatro procesos, evitando colisiones entre módulos de prueba homónimos de extracción y carga:

```bash
PYTHONPATH=1_extract .venv/bin/python -m unittest discover -s 1_extract/tests
PYTHONPATH=1_extract:2_transform .venv/bin/python -m unittest discover -s 2_transform/tests
PYTHONPATH=1_extract:2_transform .venv/bin/python -m unittest discover -s 3_load/tests
.venv/bin/python -m unittest discover -s scripts/tests
```

| Suite | Casos | Resultado | Tiempo informado por unittest |
|---|---:|---|---:|
| Extracción / auditoría / archivado | 78 | OK | 4,825 s |
| Transformación, incluida XPAP | 21 | OK | 23,033 s |
| Carga / recuperación, incluida XPAP | 36 | OK | 17,370 s |
| Scripts / CLI / integración / concurrencia | 21 | OK | 13,279 s |
| **Total** | **156** | **Todos satisfactorios** | Procesos concurrentes; no sumar como duración total |

Batería ejecutada una sola vez, después de las correcciones descritas; no fue necesario repetir pruebas. `git diff --check` pasa en los archivos de PT07. Los procedimientos se comprobaron además con `bash -n` y `ast.parse`, sin ejecutarlos. La incidencia de espacios preexistente en `docs/refactoring-proposal.md` permanece ajena al alcance.

La cobertura incluye el caso PT07 con RTF sintético, CLI reales de extracción/transformación, Parquet y recuperación de una carga confirmada cuya respuesta se pierde; el montaje y BigQuery se simulan. Comprende también contratos/diccionario, rechazos, lotes vacíos, incidencias, completitud por formato/sección, UUID, primera aparición, Parquet exacto, colisiones, fallos de escritura, consulta parametrizada, primera carga, repetición total/parcial, JSON/NULL, carga confirmada seguida de fallo local, resultado remoto pendiente/desconocido, READY obsoleto, estados inválidos, SIGKILL, bloqueo heredado y bloqueo persistente de reanudación. Incluye integración sintética CSV → transformación → Parquet → carga simulada y CLI real de extracción/auditoría sobre un lote vacío. No prueba conversión de una colección real DOC/RTF ni el servicio remoto.

## 3. Defectos demostrados y correcciones

1. **Carga aceptaba UUID malformados.** Reproducción local previa: `validate_psg_uuids()` devolvía `['not-a-uuid']`. Se exige el mismo formato canónico `[0-9a-f]{32}` que en transformación, sin corregir silenciosamente el valor. Fixtures PSG actualizados a UUID sintéticos válidos; XPAP conserva sus identificadores.
2. **Carga aceptaba completitud NULL.** Reproducción previa: `validate_psg_values()` retornaba normalmente con una serie Float64 nula. E05 lo considera bloqueante técnico. Se rechaza antes de deduplicar o cargar; 0 % continúa siendo válido e informativo. La nulabilidad física de BigQuery no sustituye estas reglas del ETL.
3. **El fallback T90 imponía coherencia matemática clínica.** Un caso sintético con 11 minutos y TST 10 se rechazaba con `No se puede derivar oxi_t90_pct…`. Se eliminan las comparaciones de signo/rango entre variables clínicas. Se conserva la fórmula, los valores reportados y los operandos; denominador cero deja el derivado NULL. La prueba que exigía rechazo por relación clínica se sustituye por comprobaciones explícitas de preservación y ausencia de esa barrera, conforme a E05.
4. **Instrucciones operativas obsoletas.** README raíz/de capas/de declaraciones todavía mencionaban rutas de config retiradas, PSG XLSX, colisiones con sufijo temporal y una batería pytest conjunta que colisiona por módulos homónimos. Se corrigen a contrato compartido, PSG Parquet, journal determinista y procesos de pruebas separados. Se conserva el historial de CHANGELOG y el marcador v5.0.1.

Archivos funcionales: `3_load/main.py` y `2_transform/psg/core/transforms.py`; regresiones en sus suites y fixtures PSG, e integración nueva `scripts/tests/test_pt07_pipeline.py`. Documentación: README raíz/de capas/de declaraciones, TODO y este único informe consolidado. Cambios funcionales limitados a esos dos controles del cargador y al fallback T90. No se añaden reglas clínicas, columnas, dependencias ni mecanismos de compatibilidad.

## 4. Riesgos y decisiones pendientes

- **Rutas de operación:** los defaults históricos `/mnt/e/RESULTADOS` y `/mnt/e/RESULTADOS/RESULTADOS_OBSERVATORIO` están anidados. El preflight aprobado del orquestador exige directorios disjuntos. No se ha escogido otra ruta ni movido documentación: antes de E30 el responsable debe aprobar un origen real disjunto del archivo existente, o un destino NTFS distinto y su transición. No desplegar confiando en esos defaults para la orquestación.
- **PR12 sigue abierta:** cierre formal pendiente; no volver a fusionar su rama. Véase sección 6.
- **E28 pendiente:** diferencias con los 9.080 UUID/9.083 filas históricos no están conciliadas. Esa referencia no es una expectativa universal: hay tres filas adicionales de procedencia no verificada y las poblaciones pueden ser distintas.
- WSL2, NTFS documental y ext4 intermedio son requisitos de operación. El preflight comprueba montaje real/acceso, pero no certifica por sí solo que el volumen Windows sea NTFS ni su disponibilidad futura.
- No hay unicidad global frente a escritores externos ni transacción entre BigQuery y disco. Pérdida eléctrica, reinicio WSL, caída del kernel y restauración de copias con inode distinto no están demostrados. Las pruebas E26 de fallo y SIGKILL son de software local.
- Una extracción sin checkpoint final no puede tratarse como inventario completo: se recuperan movimientos demostrados y se detiene para revisión. Estados anteriores a E26 pueden carecer de huellas/identidad suficientes; no hay migración automática. `recovery_blocked` no se levanta repitiendo el comando.
- E24 permanece aplazada: el historial CSV es necesario para UUID y archivados fallidos. Su volumen y los journals crecen; no se aplica limpieza ni SQLite.
- Faltan volumen diario, ventana operativa y disponibilidad/tiempo máximo aprobados. No se inventa un SLO: medir en E28 y aprobar antes de programación E32. Este PT07 no instala programación.
- Se preservan cambios locales ajenos: un espacio final en `docs/refactoring-proposal.md`, `TODO.md:Zone.Identifier` y `logs/` sin seguimiento. No incluirlos en la entrega ni inspeccionar sus posibles datos clínicos.

## 5. E28 — Protocolo operativo preparado, todavía no ejecutado

### 5.1 Autorización, aislamiento y parámetros

Responsable: designar ejecutor y revisor. Requiere autorización separada para documentos reales y BigQuery **de prueba**. El proveedor entrega una copia de referencia inmutable de documentos 2024 y, si existe, una referencia local de UUID históricos. Nunca usar un origen de PRD como entrada del pipeline. Exigir muestra con DOC y RTF cuando ambos estén disponibles; documentar ausencias de formato.

Los siguientes parámetros son obligatorios y deben registrarse en evidencia restringida; no son valores existentes ni aprobados por este informe. `PSG_CANDIDATE_SHA` será el commit revisado que incluya PT07, una vez se autorice su creación. No usar únicamente `5d5388c`, que no contiene estas correcciones.

```bash
set -euo pipefail
unset PYTHONOPTIMIZE PSG_EXTRA_RUN_JSONS PSG_CHECK_SUFFIXES
export PSG_REVIEW_REPO=/home/rom/obsino/clisueno
: "${PSG_CANDIDATE_SHA:?SHA candidato autorizado}"
: "${PSG_REFERENCE_2024:?copia de referencia autorizada e inmutable}"
: "${PSG_DOC_MOUNT:?montaje NTFS de laboratorio, distinto de /}"
: "${PSG_COPY_ROOT:?directorio NUEVO de copias bajo ese montaje}"
: "${PSG_TEST_PROJECT:?proyecto de prueba distinto de observatorio-ino-1}"
: "${PSG_TEST_DATASET:?dataset independiente con prefijo pt07_}"
: "${PSG_TEST_TABLE:?tabla nueva con prefijo pt07_psg_}"
: "${PSG_BQ_LOCATION:?región aprobada para el dataset de prueba}"
: "${PSG_TEST_KEY:?JSON de cuenta exclusiva de pruebas, sin acceso a PRD}"
export PSG_EVAL_ROOT="$(mktemp -d "$HOME/pt07-psg.XXXXXXXX")"
export PSG_CODE="$PSG_EVAL_ROOT/code"
export PSG_EVIDENCE="$PSG_EVAL_ROOT/evidence"
umask 077
mkdir "$PSG_CODE" "$PSG_EVIDENCE"
git -C "$PSG_REVIEW_REPO" archive --format=tar "$PSG_CANDIDATE_SHA" > "$PSG_EVAL_ROOT/code.tar"
tar -xf "$PSG_EVAL_ROOT/code.tar" -C "$PSG_CODE"
printf '%s\n' "$PSG_CANDIDATE_SHA" > "$PSG_EVIDENCE/candidate.sha"
python3 -m venv "$PSG_CODE/.venv"
"$PSG_REVIEW_REPO/.venv/bin/python" -m pip freeze > "$PSG_EVIDENCE/requirements-dev.txt"
# Revisar que el snapshot no contenga rutas locales no portables ni URLs con secretos.
"$PSG_CODE/.venv/bin/python" -m pip install -r "$PSG_EVIDENCE/requirements-dev.txt"
"$PSG_CODE/.venv/bin/python" -m pip check
cd "$PSG_CODE"
mkdir staging logs
```

El responsable debe verificar también los permisos/ACL de las copias NTFS y el acceso restringido a logs/estados. La cuenta necesita crear trabajos en el proyecto de prueba y leer/escribir únicamente el dataset de prueba; nunca reutilizar la clave productiva. Verificar esas restricciones con el administrador. Confirmar WSL2 (`uname -r`), montaje (`mountpoint "$PSG_DOC_MOUNT"`, `findmnt -T "$PSG_DOC_MOUNT"`) y ext4 nativo (`findmnt -T "$PSG_CODE/staging"`). Confirmar NTFS en Windows: DrvFs puede presentarse como 9p. Si el snapshot de dependencias no se reproduce, detenerse y volver a validar ese entorno antes de usar documentos.

Configurar **solo el YAML del código aislado**, preservando el YAML DEV/PRD:

```bash
.venv/bin/python - <<'PY'
import os,re
from pathlib import Path
import yaml
p=Path('0_declarations/psg.yaml'); c=yaml.safe_load(p.read_text())
e=os.environ; mount=Path(e['PSG_DOC_MOUNT']).resolve(); root=Path(e['PSG_COPY_ROOT']).resolve()
reference=Path(e['PSG_REFERENCE_2024']).resolve()
assert mount != Path('/') and mount.is_mount() and root != mount and root.is_relative_to(mount)
assert not root.exists() and reference.is_dir()
protected=[Path(x).resolve() for x in c['extract']['archivado']['rutas_clinicas_protegidas']]
assert not any(root.is_relative_to(x) or x.is_relative_to(root) for x in protected)
assert not (root.is_relative_to(reference) or reference.is_relative_to(root))
assert e['PSG_TEST_PROJECT'] != c['load']['project_id']
assert re.fullmatch(r'[a-z][a-z0-9-]+', e['PSG_TEST_PROJECT'])
assert re.fullmatch(r'pt07_[A-Za-z0-9_]+',e['PSG_TEST_DATASET'])
assert re.fullmatch(r'pt07_psg_[A-Za-z0-9_]+',e['PSG_TEST_TABLE'])
key=Path(e['PSG_TEST_KEY']).resolve(); assert key.is_file()
root.mkdir(); (root/'source').mkdir(); (root/'archive').mkdir(); (root/'empty').mkdir()
c['extract']['entrada']['ruta']=str(root/'source')
c['extract']['archivado']['destino']=str(root/'archive')
c['load'].update(project_id=e['PSG_TEST_PROJECT'],dataset_id=e['PSG_TEST_DATASET'],
 table_id=e['PSG_TEST_TABLE'],service_account_json=str(key))
p.write_text(yaml.safe_dump(c,sort_keys=False,allow_unicode=True))
PY
cp -a --reflink=never "$PSG_REFERENCE_2024/." "$PSG_COPY_ROOT/source/"
chmod -R u+rwX "$PSG_COPY_ROOT/source"
```

No usar enlaces físicos a originales o a la referencia. La copia mutable debe ser independiente. Crear el manifiesto inicial sobre las copias de entrada; no volver a calcular MD5 de archivados:

```bash
cat > "$PSG_EVIDENCE/capture_manifest.py" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve(); items=[]
for path in sorted(root.rglob('*')):
 if path.suffix.lower() not in ('.doc','.rtf'): continue
 item={'source':str(path.absolute()),'format':path.suffix.lower()[1:],'uuid_md5':None}
 if path.is_symlink():
  item['issue']='symlink'
 else:
  assert path.resolve().is_relative_to(root)
  try:
   item['bytes']=path.stat().st_size
   with path.open('rb') as stream: item['uuid_md5']=hashlib.file_digest(stream,'md5').hexdigest()
  except OSError as error: item['issue']=type(error).__name__
 items.append(item)
with Path(sys.argv[2]).open('x',encoding='utf-8') as target:
 json.dump(items,target,ensure_ascii=False,indent=2)
PY
.venv/bin/python "$PSG_EVIDENCE/capture_manifest.py" "$PSG_COPY_ROOT/source" "$PSG_EVIDENCE/input-manifest-initial.json"
```

El MD5 inicial predice el UUID de las filas aceptadas; documentos no legibles se registran como tales. Para el archivo final se contrastan rutas/evidencia de journal sin rehash. No mostrar nombres de pacientes ni campos clínicos en los informes compartidos.

### 5.2 Crear destinos independientes desde el YAML

Después de autorizar el acceso remoto de prueba:

```bash
.venv/bin/python - <<'PY'
import os,yaml
from google.cloud import bigquery
c=yaml.safe_load(open('0_declarations/psg.yaml')); x=c['load']
assert x['project_id']==os.environ['PSG_TEST_PROJECT']!='observatorio-ino-1'
client=bigquery.Client.from_service_account_json(x['service_account_json'],project=x['project_id'])
d=bigquery.Dataset(f"{x['project_id']}.{x['dataset_id']}"); d.location=os.environ['PSG_BQ_LOCATION']
client.create_dataset(d,exists_ok=True)
assert client.get_dataset(d.reference).location.upper()==d.location.upper()
types={'string':'STRING','int':'INT64','float':'FLOAT64','date':'DATE'}
schema=[bigquery.SchemaField(n,types[t],mode='NULLABLE') for n,t in c['schema']['load']['input']['columns'].items()]
for suffix in ('','_partial','_recovery'):
 table=bigquery.Table(f"{x['project_id']}.{x['dataset_id']}.{x['table_id']}{suffix}",schema=schema)
 client.create_table(table)  # Abortar si ya existe: no reutilizar una población desconocida.
 actual=client.get_table(table.reference)
 aliases={'FLOAT':'FLOAT64','INTEGER':'INT64','BOOLEAN':'BOOL'}
 signature=lambda fields:[(f.name,aliases.get(f.field_type,f.field_type),f.mode) for f in fields]
 assert signature(actual.schema)==signature(schema)
 assert actual.time_partitioning is None and actual.range_partitioning is None and not actual.clustering_fields
PY
```

No se consulta ni copia el esquema de PRD. Guardar identidad de dataset/tablas, región y firma del YAML; no credenciales en el informe.

### 5.3 Primera ejecución, lote vacío y reanudación confirmada

```bash
.venv/bin/python scripts/run_psg.py --input "$PSG_COPY_ROOT/source" \
  --archive-dest "$PSG_COPY_ROOT/archive" --mount "$PSG_DOC_MOUNT" \
  --table-id "$PSG_TEST_TABLE" | tee "$PSG_EVIDENCE/first.console"
export PSG_RUN_JSON="$(.venv/bin/python - <<'PY'
import os
from pathlib import Path
lines=(Path(os.environ['PSG_EVIDENCE'])/'first.console').read_text().splitlines()
print(next(line.split(': ',1)[1] for line in reversed(lines) if line.startswith('PSG ')))
PY
)"
export PSG_RUN_ID="$(.venv/bin/python -c 'import json,os; print(json.load(open(os.environ["PSG_RUN_JSON"]))["id"])')"
.venv/bin/python scripts/run_psg.py --resume "$PSG_RUN_ID" | tee "$PSG_EVIDENCE/resume-confirmed.console"
.venv/bin/python scripts/run_psg.py --input "$PSG_COPY_ROOT/empty" \
  --archive-dest "$PSG_COPY_ROOT/archive" --mount "$PSG_DOC_MOUNT" \
  --table-id "$PSG_TEST_TABLE" | tee "$PSG_EVIDENCE/empty.console"
```

Primera ejecución: esperar OK o WARNING, nunca ERROR aceptado tácitamente. Si no hay filas válidas, resolver población y rechazos antes de probar cargas. Reanudar una ejecución confirmada debe conservar job_id, cantidades y archivo; no crear trabajo. El lote vacío debe ser EMPTY, auditoría explícita OK/ADVERTENCIA, transformación/carga SKIPPED y cero trabajos nuevos. Registrar todos los IDs emitidos; no usar el último archivo por autodiscovery.

El segundo lote diario con documentos nuevos se ejecuta después de las comprobaciones iniciales, según 5.6 bis, manteniendo staging/estado. Una repetición documental sobre otro origen detecta UUID históricos y conserva copias duplicadas sin archivarlas otra vez. No volver a colocar copias bajo el mismo nombre de un original ya archivado: provocaría una colisión de inode que requiere revisión.

### 5.4 Repetición parcial y total de artefactos

Generar nuevos CSV desde el CSV crudo de la ejecución registrada, sin editarlo. Se requieren al menos dos filas aceptadas:

```bash
.venv/bin/python - <<'PY'
import os,json,pandas as pd
from pathlib import Path
r=json.load(open(os.environ['PSG_RUN_JSON']))
df=pd.read_csv(r['paths']['csv'],dtype='string',keep_default_na=False)
assert len(df)>=2
for name,frame in [('subset',df.sort_values('meta_uuid').iloc[:len(df)//2]),('combined',df),('repeat',df)]:
 target=Path('staging')/f'extract_psg_pt07_{name}.csv'
 assert not target.exists(); frame.to_csv(target,index=False)
PY
for name in subset combined repeat; do
 .venv/bin/python 2_transform/main.py --flow psg --yes \
   --input "staging/extract_psg_pt07_${name}.csv" \
   --output "staging/extract_psg_pt07_${name}_transformed.parquet"
 .venv/bin/python 3_load/main.py --flow psg --yes --table-id "${PSG_TEST_TABLE}_partial" \
   --input "staging/extract_psg_pt07_${name}_transformed.parquet" \
   --result-json "$PSG_EVIDENCE/${name}-load.json"
done
```

Si N es el conjunto de UUID del CSV original y S el subconjunto inicial: envíos esperados `|S|`, `|N−S|`, `0`; omisiones `0`, `|S|`, `|N|`. La tabla debe acabar con exactamente `|N|` filas y UUID únicos. En la repetición total no debe existir trabajo nuevo ni sobrescritura. Los JSON de resultado y `.load-state.json` permiten comprobarlo sin comparar datos clínicos en consola.

### 5.5 Interrupción controlada después de confirmar el trabajo remoto

Preparar otro Parquet con los mismos datos y nombre nuevo; usar exclusivamente la tabla `_recovery` inicialmente vacía. La inyección afecta al lanzador de prueba, no al código funcional:

```bash
cp --no-clobber "$(.venv/bin/python -c 'import os,json; print(json.load(open(os.environ["PSG_RUN_JSON"]))["paths"]["csv"])')" \
  staging/extract_psg_pt07_interrupt.csv
.venv/bin/python 2_transform/main.py --flow psg --yes \
  --input staging/extract_psg_pt07_interrupt.csv \
  --output staging/extract_psg_pt07_interrupt_transformed.parquet
cat > "$PSG_EVIDENCE/lose_load_response.py" <<'PY'
import os,sys,runpy
from pathlib import Path
from google.cloud import bigquery
original=bigquery.Client.load_table_from_dataframe
def lose(self,*args,**kwargs):
 job=original(self,*args,**kwargs)
 job.result()
 os._exit(77)  # Journal SUBMITTED previo; sin registrar confirmación ni mover el Parquet.
bigquery.Client.load_table_from_dataframe=lose
loader=Path(os.environ['PSG_CODE'])/'3_load/main.py'
sys.argv=[str(loader),*sys.argv[1:]]
runpy.run_path(str(loader),run_name='__main__')
PY
if .venv/bin/python "$PSG_EVIDENCE/lose_load_response.py" --flow psg --yes \
 --input staging/extract_psg_pt07_interrupt_transformed.parquet --table-id "${PSG_TEST_TABLE}_recovery"; then
 echo 'ABORTAR: no se produjo la interrupción prevista' >&2; exit 1
else
 code=$?; test "$code" -eq 77
fi
cp staging/extract_psg_pt07_interrupt_transformed.load-state.json "$PSG_EVIDENCE/submitted-before-resume.json"
.venv/bin/python 3_load/main.py --flow psg --yes --table-id "${PSG_TEST_TABLE}_recovery" \
  --input staging/extract_psg_pt07_interrupt_transformed.parquet \
  --result-json "$PSG_EVIDENCE/recovered-load.json"
```

Antes de reanudar, copiar a evidencia el journal SUBMITTED y registrar su job_id/attempt. La reanudación debe consultar ese mismo trabajo, confirmar `output_rows`, retirar solo el origen de Parquet y conservar `_loaded`, sin segundo job. No usar el lanzador de fallos fuera del laboratorio.

Para interrupciones anteriores, repetir en artefactos/copias nuevos e inventariados: detener un proceso local y registrar PID/etapa/journal antes de `--resume ID`; verificar el bloqueo de otro orquestador/CLI. No reiniciar WSL, desmontar el volumen ni llenar discos compartidos. Los fallos ENOSPC/EIO y las ventanas de enlace se cubren inicialmente con las pruebas sintéticas existentes. Si la interrupción deja inventario sin checkpoint, job ausente/desconocido o `recovery_blocked`, **el resultado aceptable es detenerse sin reenviar**, conservar evidencia y revisar; no fabricar el estado faltante.

### 5.6 Comprobación real de los trabajos y equivalencia

Después de los casos anteriores, con la misma cuenta de pruebas:

```bash
PYTHONPATH=1_extract:2_transform .venv/bin/python - <<'PY'
import os,json,hashlib,csv
from pathlib import Path
import pandas as pd,yaml
from google.cloud import bigquery
from google.cloud.bigquery import _pandas_helpers
from src.basal.procesar_basal import COMPLETENESS_FIELDS,_completeness
from psg.main import _load_pipeline_config
from psg.core.transforms import register_psg_operations
from transform_commons.engine import OperationRegistry,run_pipeline
from transform_commons.io import read_dataset
c=yaml.safe_load(open('0_declarations/psg.yaml')); x=c['load']
assert x['project_id']==os.environ['PSG_TEST_PROJECT']!='observatorio-ino-1'
client=bigquery.Client.from_service_account_json(x['service_account_json'],project=x['project_id'])
runs=[json.load(open(os.environ['PSG_RUN_JSON']))]
runs += [json.load(open(path)) for path in os.environ.get('PSG_EXTRA_RUN_JSONS','').split(os.pathsep) if path]
manifest={entry['source']:entry for path in Path(os.environ['PSG_EVIDENCE']).glob('input-manifest-*.json')
          for entry in json.loads(path.read_text())}
assert len(COMPLETENESS_FIELDS['doc'])==124 and len(COMPLETENESS_FIELDS['rtf'])==129
config=_load_pipeline_config(str(Path('0_declarations/psg.yaml').resolve()),[Path.cwd()])
registry=OperationRegistry(); register_psg_operations(registry)
frames=[]
for r in runs:
 if r['state']=='EMPTY': continue
 csv_path=Path(r['paths']['csv'])
 with csv_path.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
 for row in rows:
  kind=Path(row['meta_fuente']).suffix.lower().lstrip('.')
  assert float(row['meta_completitud_pct'])==float(_completeness(row,kind))
  assert row['meta_uuid']==manifest[row['meta_fuente']]['uuid_md5']
 expected=run_pipeline(config,registry,read_dataset(str(csv_path),config=config['input']))
 actual=pd.read_parquet(r['paths']['loaded'])
 pd.testing.assert_frame_equal(expected,actual,check_dtype=True,check_exact=True)
 frames.append(actual)
actual=pd.concat(frames,ignore_index=True).drop_duplicates('meta_uuid',keep='first')
from scripts.psg_state import file_evidence
for path in Path('staging/.psg-moves').glob('*.json'):
 item=json.loads(path.read_text())
 assert item['state']=='LOGGED' and not Path(item['source']).exists()
 assert item['uuid']==manifest[item['source']]['uuid_md5']
 assert file_evidence(item['destination'])==item['evidence']
types={'string':'STRING','int':'INT64','float':'FLOAT64','date':'DATE'}
schema=[bigquery.SchemaField(n,types[t]) for n,t in c['schema']['load']['input']['columns'].items()]
expected_rows={v['meta_uuid']:v for v in _pandas_helpers.dataframe_to_arrow(actual,schema).to_pylist()}
for suffix in os.environ.get('PSG_CHECK_SUFFIXES',',_partial,_recovery').split(','):
 table=f"{x['project_id']}.{x['dataset_id']}.{x['table_id']}{suffix}"
 values=[dict(row) for row in client.query(f'SELECT * FROM `{table}`').result()]
 assert len(values)==len(expected_rows) and len({v['meta_uuid'] for v in values})==len(values)
 assert {v['meta_uuid']:v for v in values}==expected_rows
for path in Path('staging').glob('*.load-state.json'):
 state=json.loads(path.read_text()); assert state['state']=='LOADED'
 if state['job_id'] is None:
  assert state['counts']['sent']==state['counts']['inserted']==0; continue
 identity=json.dumps([state['source'],state['artifact_sha256'],state['table'],state['attempt'],state['uuids']])
 assert state['job_id']=='psg_'+hashlib.sha256(identity.encode()).hexdigest()
 job=client.get_job(state['job_id'],project=x['project_id'],location=state['location'])
 assert job.state=='DONE' and not job.error_result
 assert str(job.destination)==state['table'] and job.write_disposition=='WRITE_APPEND'
 assert job.output_rows==state['counts']['sent']==state['counts']['inserted']
print('Equivalencia y trabajos verificados; filas:',len(expected_rows))
PY
```

No imprimir los DataFrame ni las filas remotas en el informe. Conservar únicamente resultados agregados y artefactos privados.

### 5.6 bis — Segundo lote diario y duplicados documentales

Reservar una copia autorizada 2024 adicional, no incluida en el lote inicial, como `PSG_REFERENCE_DAY2`. Debe contener al menos un UUID nuevo; los duplicados deliberados se contabilizan aparte. Ejecutar **después** de 5.6, pues la tabla principal crecerá. Las tablas partial/recovery conservan la población inicial.

```bash
: "${PSG_REFERENCE_DAY2:?referencia autorizada reservada para el segundo lote}"
.venv/bin/python - <<'PY'
import os
from pathlib import Path
root=Path(os.environ['PSG_COPY_ROOT']).resolve(); ref=Path(os.environ['PSG_REFERENCE_DAY2']).resolve()
assert ref.is_dir() and not (ref.is_relative_to(root) or root.is_relative_to(ref))
PY
mkdir "$PSG_COPY_ROOT/source_day2" "$PSG_COPY_ROOT/archive_day2"
cp -a --reflink=never "$PSG_REFERENCE_DAY2/." "$PSG_COPY_ROOT/source_day2/"
chmod -R u+rwX "$PSG_COPY_ROOT/source_day2"
.venv/bin/python "$PSG_EVIDENCE/capture_manifest.py" "$PSG_COPY_ROOT/source_day2" "$PSG_EVIDENCE/input-manifest-day2.json"
.venv/bin/python scripts/run_psg.py --input "$PSG_COPY_ROOT/source_day2" \
 --archive-dest "$PSG_COPY_ROOT/archive_day2" --mount "$PSG_DOC_MOUNT" \
 --table-id "$PSG_TEST_TABLE" | tee "$PSG_EVIDENCE/day2.console"
export PSG_EXTRA_RUN_JSONS="$(.venv/bin/python - <<'PY'
import os
from pathlib import Path
lines=(Path(os.environ['PSG_EVIDENCE'])/'day2.console').read_text().splitlines()
print(next(line.split(': ',1)[1] for line in reversed(lines) if line.startswith('PSG ')))
PY
)"
export PSG_CHECK_SUFFIXES=''
```

Reejecutar **solo la comprobación 5.6**: verificará la unión de los dos registros contra la tabla principal y todos sus jobs. No se repite la extracción ni se altera la referencia inicial. Esperar exactamente el incremento de UUID nuevos del segundo lote, sin duplicados. Si no hay un holdout disponible, no fingir este ensayo: registrar la limitación antes de cerrar E28.

Para el ensayo documental repetido, usar nuevas copias de la referencia inicial, conservando el origen histórico ya archivado:

```bash
mkdir "$PSG_COPY_ROOT/source_repeat" "$PSG_COPY_ROOT/archive_repeat"
cp -a --reflink=never "$PSG_REFERENCE_2024/." "$PSG_COPY_ROOT/source_repeat/"
chmod -R u+rwX "$PSG_COPY_ROOT/source_repeat"
.venv/bin/python scripts/run_psg.py --input "$PSG_COPY_ROOT/source_repeat" \
 --archive-dest "$PSG_COPY_ROOT/archive_repeat" --mount "$PSG_DOC_MOUNT" \
 --table-id "$PSG_TEST_TABLE" | tee "$PSG_EVIDENCE/document-repeat.console"
```

El histórico CSV debe reconocer los UUID aceptados del primer lote: cero filas nuevas/cargas, copias duplicadas conservadas en origen y rechazos nuevamente conciliados. El resultado debe ser EMPTY con auditoría explícita y sin trabajo nuevo. No reutilizar el nombre original bajo el mismo origen archivado.

### 5.7 Criterios cuantitativos de aceptación y cierre de E28

- Cero modificaciones a originales, referencia inmutable, archivos históricos y tablas productivas; evidencia del aislamiento y restricciones de la cuenta.
- 100 % de columnas, orden, tipos y registros esperados equivalentes CSV tipado/Parquet/tabla. Ceros iniciales, UUID, DATE/NULL y JSON exactos. Cero UUID duplicados en cada destino final; ninguna fila sobrescrita.
- Auditoría: `válidos = archivados + reintentos + fallos + rechazados + duplicados + errores técnicos`; `archivados ≤ filas nuevas ≤ archivados + fallos`. Para cerrar una carga: fallos de archivado, recorrido y procesamiento = 0. Rechazos individuales conciliados con suma de motivos y orígenes únicos, sin imponer tasa máxima inventada.
- En ejecución de un CSV: filas extraídas = transformadas; recibidos = omitidos + enviados; enviados = output_rows = insertados. Cero trabajos nuevos cuando enviados = 0 y tras reanudar una carga confirmada.
- 100 % de UUID de filas aceptadas conciliados con el manifiesto inicial y archivos del journal. Cero originales eliminados por rechazo o duplicado. Solo las copias aceptadas cambian a su archivo de laboratorio.
- Completitud recalculada por formato exacta a dos decimales; no umbral mínimo. NULL e incidencias coinciden con la transformación esperada; baja calidad no se convierte en bloqueo clínico.
- Fechas e IDs exactamente acordes con E18: NULL admitidos y trazados, sin imputación. Documentar fechas fuera de 2024 según la población seleccionada; no filtrar silenciosamente ni inventar coherencia clínica.
- Repetición parcial/total y recuperación cumplen los recuentos definidos. Los job_id reales coinciden con identidad/tabla/intento/subconjunto registrados. Cero reenvíos con resultado incierto y cero ejecuciones locales solapadas.
- Comparación con referencia local 2024: conjuntos UUID, filas y diferencias clasificadas y aprobadas. No exigir 9.080/9.083 sin demostrar que las poblaciones son las mismas. Si faltan copia/referencia o hay diferencias inexplicadas, E28 sigue pendiente.
- Medir duración por etapa y total, rechazos e incidencias. La aceptación temporal requiere ventana aprobada por el responsable; ningún umbral se ha supuesto aquí. Cierre requiere acta del ejecutor y del revisor con entorno, SHA, run_id, tablas, jobs, cantidades, incidencias y pendientes resueltos.

## 6. E29 — Integración y alcance Git

La [PR12](https://github.com/moafar/obsino-clisueno/pull/12), «Auditoría automática de cada extracción PSG», se consultó en modo lectura: **open, merged=false**; base `main` en `710460c`, cabecera `d6183164797c18f9b9ae8269119788568f979cec`. `d11abaf` es un merge local con padres `ecb62e3` y exactamente esa cabecera, y es ancestro de `5d5388c`. No hay una integración técnica adicional que realizar para incorporar esa rama al candidato.

La auditoría sigue invocada por extracción, persiste su informe, diferencia OK/ADVERTENCIA/ERROR y bloquea cuando corresponde. Sus modificaciones posteriores están trazadas por E05–E15, E16–E17 y E26; retirar MD5 repetido y controles matemáticos clínicos responde a decisiones aprobadas, no a pérdida accidental del PR. Las pruebas de auditoría y archivado actuales verifican el comportamiento resultante.

**Decisión propuesta, pendiente de aprobación:** consolidar el candidato mediante una única promoción a main y cerrar PR12 como incorporada/sustituida, sin volver a fusionar `feat/psg-auditoria-automatica`. No se cambió el estado remoto ni se envió comentario. E29 no se marca completada porque TODO exige resolución formal del estado en GitHub y decisión aprobada.

Fuera de la lógica PSG aparecen cambios mecánicos de imports en XPAP, DAM, ACTIGRAFIA, AUTOCPAP, CAPNOGRAFIA y POLIGRAFIA, todos originados por `ecb62e3` al separar `extract_commons`/`transform_commons`; no son nuevas funcionalidades de esos flujos. Los cambios locales ajenos enumerados en la sección 4 no se revierten ni se incluyen en el futuro artefacto. No se han realizado commit, push, merge, rebase ni fetch de Git; la consulta remota fue solo de metadatos de PR12.

## 7. E30 — Procedimiento de despliegue y reversión preparado

### Requisitos y condiciones de aborto

Requiere E28 efectivamente cerrada, resolución formal de E29, autorización del despliegue y del marcador v6.0.0, SHA exacto publicado en main, responsable de operación y reversión, ventana y rutas documentales disjuntas aprobadas. No habilitar programación E32. Confirmar WSL2, NTFS documental, ext4 para el repositorio/staging/estado, catdoc y dependencias del entorno ensayado. La clave PRD se administra localmente fuera de Git con permisos mínimos; no copiar la clave DEV ni incluirla en backups públicos.

Abortar ante árbol Git operativo modificado, SHA no aprobado, esquema distinto, falta de montaje/espacio/permisos, procesos antiguos activos, jobs inciertos sin reconciliar, ausencia de backup/evidencia o cualquier diferencia inexplicada de E28. El esquema E21 declarado no exige migración adicional: verificarlo contra YAML tras autorización; si no coincide, abortar y solicitar una migración separada. No ejecutar ALTER, MERGE, DELETE ni TRUNCATE como parte de este procedimiento.

### Preparación en DEV, después de autorización futura

1. Fijar y revisar la lista de archivos del candidato, excluyendo logs, datos, credenciales, ADS y el espacio ajeno de `docs/refactoring-proposal.md`.
2. Registrar el resultado de E28 sobre ese SHA/entorno. Aprobar la actualización de la cabecera de CHANGELOG a v6.0.0 y su descripción de incompatibilidades. Crear/revisar el commit y la promoción a main mediante el flujo Git autorizado; cerrar PR12 según la decisión aprobada. Nada de ello se ejecutó en PT07.
3. Exportar el snapshot de dependencias ensayado y su SHA256 a evidencia restringida. Conservar el SHA previo de PRD, config local y entorno anterior para reversión. La referencia `710460c` de TODO es histórica, no prueba del estado actual de PRD.

### Aplicación controlada en PRD, solo en una sesión autorizada

Mantener la ruta operativa `~/obsino/clisueno2` y staging en su ubicación canónica; los journals contienen rutas absolutas e identidad de inode. No desplegar sobre un directorio nuevo copiando estados y suponiendo que siguen válidos. Detener/coordinar invocaciones manuales y cualquier automatización externa de PSG/XPAP antes de cambiar código o entorno; el software antiguo puede no respetar el bloqueo nuevo.

Comandos de promoción futura, con SHA/ventana aprobados y sin procesos activos:

```bash
cd "$HOME/obsino/clisueno2"
: "${PSG_RELEASE_SHA:?commit exacto aprobado en main}"
: "${PSG_ENV_SNAPSHOT:?snapshot ensayado de dependencias}"
: "${PSG_DEPLOY_ID:?identificador de ventana aprobado}"
: "${PSG_PROD_MOUNT:?montaje documental aprobado}"
test "$(git branch --show-current)" = main
git diff --exit-code
git diff --cached --exit-code
# Revisar por separado archivos sin seguimiento; no borrarlos ni incorporarlos automáticamente.
git status --short
export PSG_PREVIOUS_SHA="$(git rev-parse HEAD)"
# Conservar ese SHA, configuración y estados en evidencia privada antes de seguir.
flock -n staging/.psg-run.lock -c 'echo "Bloqueo global disponible"'
git fetch origin main
test "$(git rev-parse FETCH_HEAD)" = "$PSG_RELEASE_SHA"
git merge --ff-only FETCH_HEAD
test ! -e ".venv.before-${PSG_DEPLOY_ID}"
mv .venv ".venv.before-${PSG_DEPLOY_ID}"
python3 -m venv .venv
.venv/bin/python -m pip install -r "$PSG_ENV_SNAPSHOT"
.venv/bin/python -m pip check
command -v catdoc
mountpoint "$PSG_PROD_MOUNT"
findmnt -T staging
```

La coordinación de mantenimiento debe mantenerse durante toda la aplicación; la comprobación `flock` por sí sola no detiene invocaciones antiguas. No mover ni limpiar staging, journals, CSV históricos, archivos NTFS ni claves. Una copia de seguridad no autoriza a restaurar inodes nuevos sobre journals activos: ante desastre se debe reconciliar, no reanudar a ciegas.

Comprobaciones de rutas tras autorización, antes de procesar documentos:

```bash
: "${PSG_PROD_INPUT:?origen disjunto aprobado}"
: "${PSG_PROD_ARCHIVE:?archivo NTFS aprobado}"
.venv/bin/python - <<'PY'
import os,yaml
from pathlib import Path
from scripts.run_psg import preflight
c=yaml.safe_load(open('0_declarations/psg.yaml'))
preflight(Path(os.environ['PSG_PROD_INPUT']).resolve(),Path(os.environ['PSG_PROD_ARCHIVE']).resolve(),
          Path(os.environ['PSG_PROD_MOUNT']).resolve(),Path('staging').resolve(),
          Path(c['load']['service_account_json']).resolve())
PY
.venv/bin/python 1_extract/main.py --flow psg --input "$PSG_PROD_INPUT" \
 --archive-dest "$PSG_PROD_ARCHIVE" --output-dir "$PWD/staging" --dry-run
```

Comprobar el esquema productivo **en lectura tras autorización**, reutilizando `load_schema`, `build_bq_schema` y `validate_target_schema` del cargador; exigir los 158 campos NULLABLE en orden y ausencia de particionamiento/clustering acordada. Comparar clave/tabla/proyecto configurados con el acta; no mostrar la clave. Probar `--help`, extracción `--dry-run` sobre rutas aprobadas y un lote vacío aislado. Repetir una prueba controlada con documentos sintéticos en carpetas NTFS de laboratorio y destino BigQuery de prueba desde el entorno instalado, con el protocolo E28. Solo después de conformidad permitir un primer lote operacional autorizado y verificar sus cantidades, job_id, archivado, estados y ausencia de solapamiento. Ninguna tarea diaria se programa aquí.

### Reversión

Ante un fallo: detener entradas nuevas, conservar el registro/logs/artefactos y el job_id; consultar el trabajo antes de decidir cualquier reintento. No eliminar filas ni revertir una carga remota con SQL improvisado. Si se desconoce su resultado, no volver a lanzar v5 ni otro lote al destino.

La reversión de código debe prepararse/revisarse en DEV como **un nuevo commit de reversión sobre main**, sin reset ni rebase de la historia. Su SHA aprobado `PSG_ROLLBACK_SHA` se promueve igual que el release:

```bash
# Solo tras aprobar/publicar el commit de reversión y con operación detenida.
cd "$HOME/obsino/clisueno2"
: "${PSG_ROLLBACK_SHA:?SHA de reversión aprobado en main}"
git fetch origin main
test "$(git rev-parse FETCH_HEAD)" = "$PSG_ROLLBACK_SHA"
git merge --ff-only FETCH_HEAD
# Si procede restaurar el entorno previo; ambos nombres deben ser nuevos/existentes según el acta.
test ! -e ".venv.failed-${PSG_DEPLOY_ID}"
mv .venv ".venv.failed-${PSG_DEPLOY_ID}"
mv ".venv.before-${PSG_DEPLOY_ID}" .venv
.venv/bin/python -m pip check
```

Restaurar la configuración local aprobada sin sustituir estados ni originales. **v5.0.1 no entiende la salida Parquet ni los journals nuevos:** volver al código antiguo no autoriza a procesar sus artefactos ni a continuar un lote v6. La operación permanecerá detenida hasta reconciliar cargas y definir qué versión puede completar cada ejecución. El esquema ampliado y las filas ya cargadas se conservan; cualquier reversión de datos requiere otro plan y autorización. Comprobar XPAP por su ruta XLSX antes de reabrirlo. El responsable acepta por escrito el estado final antes de salir de mantenimiento.

Comprobación exacta de esquema tras la autorización de PRD (solo lectura de metadatos):

```bash
: "${PSG_PROD_TABLE_FQN:?destino productivo confirmado en el acta}"
.venv/bin/python - <<'PY'
import os,sys,importlib.util
from pathlib import Path
from google.cloud import bigquery
spec=importlib.util.spec_from_file_location('release_load',Path('3_load/main.py'))
loader=importlib.util.module_from_spec(spec); sys.modules[spec.name]=loader; spec.loader.exec_module(loader)
c=loader.load_runtime_config(Path('0_declarations/psg.yaml'),Path('staging/metadata-only.parquet'))
assert c.table_fqn==os.environ['PSG_PROD_TABLE_FQN']
schema=loader.build_bq_schema(loader.load_schema(c.schema_yaml_path,c.schema_path_in_yaml))
client=bigquery.Client.from_service_account_json(c.service_account_json,project=c.project_id)
loader.validate_target_schema(client,c.table_fqn,schema)
table=client.get_table(c.table_fqn)
assert table.time_partitioning is None and table.range_partitioning is None and not table.clustering_fields
print('Esquema conforme:',len(schema),'columnas')
PY
```

## 8. Propuesta de versión

Se propone **v6.0.0**, pendiente de autorización: PSG cambia su formato público de salida/entrada intermedia de XLSX a Parquet, añade `meta_incidencias_calidad` al esquema tipado (157 → 158 campos frente a la referencia v5.0.1), cambia los denominadores de completitud, las reglas tolerantes/duplicados y los requisitos operativos de identidad, bloqueo y persistencia. Los consumidores XLSX y ejecuciones antiguas no son intercambiables ni automáticamente reanudables. Un incremento MAJOR refleja esas incompatibilidades, aunque XPAP conserve su contrato.

El CSV crudo sigue con 159 campos y el UUID documental continúa basado en el MD5 inicial. No se propone transformar históricos, recalcular completitud histórica ni añadir otra capa de compatibilidad en esta publicación. El marcador y las etiquetas no se han modificado: **v5.0.1 sigue vigente; v6.0.0 es solo una propuesta**.
