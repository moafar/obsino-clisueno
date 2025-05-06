import os
import re

def es_archivo_texto(ruta):
    """Intenta determinar si un archivo es de texto leyendo sus primeros bytes"""
    try:
        with open(ruta, 'rb') as f:
            chunk = f.read(1024)
            # Archivos de texto no deben contener bytes nulos
            return b'\x00' not in chunk
    except:
        return False

def buscar_en_archivo(ruta, palabra, es_binario=False):
    """Busca una palabra en un archivo, manejando tanto texto como binarios"""
    try:
        if es_binario:
            # Modo binario: buscar el string como secuencia de bytes
            with open(ruta, 'rb') as f:
                contenido = f.read()
                return palabra.encode('utf-8') in contenido
        else:
            # Modo texto
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
                return palabra in contenido
    except Exception as e:
        print(f"Error procesando {ruta}: {str(e)}")
        return False

def buscar_palabra_en_archivos(carpeta, palabra):
    archivos_con_palabra = []
    archivos_sin_palabra = []
    archivos_binarios_con_palabra = []
    archivos_binarios_sin_palabra = []
    archivos_no_procesados = []
    
    for raiz, _, archivos in os.walk(carpeta):
        for archivo in archivos:
            ruta_completa = os.path.join(raiz, archivo)
            
            # Determinar si es archivo de texto o binario
            es_texto = es_archivo_texto(ruta_completa)
            
            try:
                if es_texto:
                    if buscar_en_archivo(ruta_completa, palabra):
                        archivos_con_palabra.append(ruta_completa)
                        print(f"✅ [TEXTO] Palabra encontrada en: {ruta_completa}")
                    else:
                        archivos_sin_palabra.append(ruta_completa)
                        print(f"❌ [TEXTO] Palabra NO encontrada en: {ruta_completa}")
                else:
                    if buscar_en_archivo(ruta_completa, palabra, es_binario=True):
                        archivos_binarios_con_palabra.append(ruta_completa)
                        print(f"🔍 [BINARIO] Posible coincidencia en: {ruta_completa}")
                    else:
                        archivos_binarios_sin_palabra.append(ruta_completa)
                        print(f"📦 [BINARIO] No se encontró coincidencia en: {ruta_completa}")
            except Exception as e:
                archivos_no_procesados.append(ruta_completa)
                print(f"🚫 Error procesando archivo: {ruta_completa} - {str(e)}")
    
    return {
        'texto_con_palabra': archivos_con_palabra,
        'texto_sin_palabra': archivos_sin_palabra,
        'binarios_con_palabra': archivos_binarios_con_palabra,
        'binarios_sin_palabra': archivos_binarios_sin_palabra,
        'no_procesados': archivos_no_procesados
    }

def generar_reporte(resultados, palabra):
    print("\n" + "="*50)
    print(" " * 15 + "REPORTE COMPLETO")
    print("="*50)
    
    print(f"\n🔎 Palabra buscada: '{palabra}'")
    
    print("\n📊 Estadísticas:")
    print(f"✅ Archivos de texto CON la palabra: {len(resultados['texto_con_palabra'])}")
    print(f"❌ Archivos de texto SIN la palabra: {len(resultados['texto_sin_palabra'])}")
    print(f"🔍 Archivos binarios CON posible coincidencia: {len(resultados['binarios_con_palabra'])}")
    print(f"📦 Archivos binarios SIN coincidencia: {len(resultados['binarios_sin_palabra'])}")
    print(f"🚫 Archivos no procesados: {len(resultados['no_procesados'])}")
    
    # Detalles por categoría
    categorias = [
        ('✅ Archivos de texto CON la palabra', 'texto_con_palabra'),
        ('❌ Archivos de texto SIN la palabra', 'texto_sin_palabra'),
        ('🔍 Archivos binarios CON posible coincidencia', 'binarios_con_palabra'),
        ('📦 Archivos binarios SIN coincidencia', 'binarios_sin_palabra'),
        ('🚫 Archivos no procesados', 'no_procesados')
    ]
    
    for titulo, clave in categorias:
        if resultados[clave]:
            print(f"\n{titulo} ({len(resultados[clave])}):")
            for archivo in resultados[clave]:
                print(f"- {archivo}")

if __name__ == "__main__":
    carpeta_busqueda = input("Ingrese la ruta de la carpeta a buscar: ")
    palabra_buscar = input("Ingrese la palabra a buscar: ")
    
    if not os.path.isdir(carpeta_busqueda):
        print(f"La carpeta {carpeta_busqueda} no existe.")
    else:
        print(f"\nBuscando la palabra '{palabra_buscar}' en {carpeta_busqueda}...\n")
        resultados = buscar_palabra_en_archivos(carpeta_busqueda, palabra_buscar)
        generar_reporte(resultados, palabra_buscar)