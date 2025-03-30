import docx
import subprocess
import fitz  # PyMuPDF
import logging
import os
import unicodedata
import re


def normalizar_texto(texto):
    """
    Normaliza el texto reemplazando caracteres especiales por sus equivalentes Unicode y 
    ajustando espacios y saltos de línea.

    Args:
        texto (str): El texto a normalizar.

    Returns:
        str: El texto normalizado.
    """

    # Diccionario de reemplazos de caracteres especiales por sus equivalentes Unicode
    REEMPLAZOS = {
        'á': 'a',
        'é': 'e',
        'í': 'i',
        'ó': 'o',
        'ú': 'u',
        'Á': 'A',
        'É': 'E',
        'Í': 'I',
        'Ó': 'O',
        'Ú': 'U',
        'ñ': 'n',
        'Ñ': 'N'
    }
    
    # Reemplazar caracteres específicos con equivalentes ASCII
    for original, reemplazo in REEMPLAZOS.items():
        texto = texto.replace(original, reemplazo)

    texto = re.sub(r'\s+', ' ', texto)  # Reemplazar múltiples espacios por uno solo
    texto = re.sub(r'\n+', '|', texto)  # Reemplazar múltiples saltos de línea por uno solo
    texto = re.sub(r'\r+', '|', texto)  # Eliminar retornos de carro
    texto = re.sub(r'\t+', '|', texto)  # Reemplazar múltiples tabulaciones por un espacio
    texto = texto.strip()  # Eliminar espacios en blanco al inicio y al final
    
    return texto

def extraer_texto_docx(archivo):
    doc = docx.Document(archivo)
    textos = []

    # Extraer texto del header
    for section in doc.sections:
        header = section.header
        for paragraph in header.paragraphs:
            textos.append(paragraph.text)

    # Extraer texto de las tablas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                textos.append(cell.text)

    # Extraer texto de los párrafos
    for paragraph in doc.paragraphs:
        textos.append(paragraph.text)

    # Extraer texto del footer
    for section in doc.sections:
        footer = section.footer
        for paragraph in footer.paragraphs:
            textos.append(paragraph.text)

    return "\n".join(textos)

def extraer_texto_rtf(archivo):
    from striprtf.striprtf import rtf_to_text
    with open(archivo, "r", encoding="utf-8") as f:
        rtf_content = f.read()
    return rtf_to_text(rtf_content).strip()

def extraer_texto_pdf(archivo):
    doc = fitz.open(archivo)
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    return texto

def extraer_texto_doc(archivo):
    try:
        resultado = subprocess.run(["catdoc", archivo], capture_output=True, text=True)
        if resultado.returncode == 0:
            return resultado.stdout.strip()
        else:
            raise RuntimeError(f"catdoc no pudo procesar {archivo}: {resultado.stderr}")
    except FileNotFoundError:
        logging.error("❌ No se pudo procesar .doc porque 'catdoc' no está instalado.")
        return None
    except Exception as e:
        logging.error(f"❌ Error al procesar .doc {archivo}: {e}")
        return None

def extraer_subcadenas(texto, inicio, fin):
    # Buscar la primera aparición de la cadena de inicio
    match_inicio = re.search(inicio, texto, re.DOTALL | re.IGNORECASE)
    if not match_inicio:
        return []  # No se encontró la cadena de inicio

    # Buscar la primera aparición de la cadena de fin a partir de la posición de la cadena de inicio
    match_fin = re.search(fin, texto[match_inicio.end():], re.DOTALL | re.IGNORECASE)
    if not match_fin:
        return []  # No se encontró la cadena de fin

    # Extraer la subcadena entre las cadenas de inicio y fin
    subcadena = texto[match_inicio.end():match_inicio.end() + match_fin.start()].strip()
    
    return subcadena