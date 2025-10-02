# analiza_csvs.py
import os, glob, uuid
import pandas as pd

EXCLUIR_ARCHIVOS = {"unificado.csv"}          # excluye salidas previas
IGNORAR_COLUMNAS = {"uuid"}                   # columnas sintéticas a ignorar

def _listar_csvs(carpeta: str) -> list[str]:
    archivos = glob.glob(os.path.join(carpeta, "*.csv"))
    return [p for p in archivos if os.path.basename(p) not in EXCLUIR_ARCHIVOS]

def _cols_sin_ignoradas(df: pd.DataFrame) -> set[str]:
    return set(c for c in df.columns if c not in IGNORAR_COLUMNAS)

def analizar_y_unificar(carpeta: str, nombre_salida: str = "unificado.csv") -> str:
    archivos_csv = _listar_csvs(carpeta)
    if not archivos_csv:
        print("No se encontraron archivos CSV en la carpeta (o todos fueron excluidos).")
        return ""

    print(f"Se detectaron {len(archivos_csv)} archivos CSV \n")
    print("=== Iniciando unificación de CSV === \n", flush=True)
    print("-"*50)

    columnas_por_archivo = {}
    for archivo in archivos_csv:
        df = pd.read_csv(archivo)
        columnas_por_archivo[archivo] = {
            "columnas": _cols_sin_ignoradas(df),
            "forma": df.shape
        }
        print(f"Archivo: {os.path.basename(archivo)} | Forma: {df.shape}")

    todas = set().union(*[d["columnas"] for d in columnas_por_archivo.values()])
    print("\nResumen columnas (ignorando: " + ", ".join(sorted(IGNORAR_COLUMNAS)) + "):")
    for archivo, d in columnas_por_archivo.items():
        cols = d["columnas"]
        faltantes = list(todas - cols)
        sobrantes = list(cols - todas)
        print(f"- {os.path.basename(archivo)} | Faltantes: {faltantes} | Sobrantes: {sobrantes}")

    # Base = el primer archivo (sin columnas ignoradas)
    archivo_base = archivos_csv[0]
    df_base = pd.read_csv(archivo_base)
    columnas_base = _cols_sin_ignoradas(df_base)
    print(f"\nArchivo base: {os.path.basename(archivo_base)} con forma {df_base.shape}")
    print("-"*100)

    dfs = []
    for archivo in archivos_csv:
        df_actual = pd.read_csv(archivo)
        columnas_actual = _cols_sin_ignoradas(df_actual)
        print(f"\nProcesando... {archivo} con forma {df_actual.shape}")
        if columnas_base != columnas_actual:
            print("  .... AVISO (esquema distinto, ignoradas las sintéticas):")
            dif_base = columnas_base - columnas_actual
            dif_act = columnas_actual - columnas_base
            if dif_base: print(f" - Faltan columnas: {sorted(dif_base)}")
            if dif_act:  print(f" - Columnas adicionales: {sorted(dif_act)}")
        print("  .... ok")
        dfs.append(df_actual)

    print("\n" + "-"*100)
    print(f"Se procesaron {len(dfs)} archivos CSV.")
    df_unificado = pd.concat(dfs, ignore_index=True)
    print("Se ha combinado el DataFrame.  El nuevo DataFrame tiene forma:", df_unificado.shape)

    # Escribir salida (y asegurarte de no leerla en la próxima corrida)
    archivo_salida = os.path.join(carpeta, nombre_salida)
    df_unificado["uuid"] = [str(uuid.uuid4()) for _ in range(len(df_unificado))]
    df_unificado.to_csv(archivo_salida, index=False)
    print(f"El DataFrame unificado se ha guardado en {archivo_salida} con forma {df_unificado.shape}")
    return archivo_salida

if __name__ == "__main__":
    print("Ejecuta analizar_y_unificar(carpeta) desde tu main.")
