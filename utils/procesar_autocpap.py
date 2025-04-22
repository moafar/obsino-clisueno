import logging
from utils.texto_utils import extraer_regex

def procesar_autocpap_docx(texto_relevante: str):
    logging.info("Procesando examen AUTO CPAP (DOCX)*****************")

    datos = {}
    
    campos = [
        ("nombre_paciente", r"(?i)Nombre(?: del paciente)?\s*:\s*([^:]+?)\s*Sexo"),
        ("sexo_paciente", r"(?i)sexo\s*:\s*([^:]+?)\s*fecha"),
        ("fecha_estudio", r"(?i)(?:fecha\s*(?:est\.?|estudio)?)\s*:\s*(\d{2}[\/-]\d{2}[\/-]\d{4})\s*(?=fecha|de\s+nacimiento|$)"),        
        ("edad_paciente", r"(?i)(?:Edad|edad)(?:\s*del\s*paciente)?\s*[:=]\s*(\d+)"),
        ("medida_edad_paciente", r"(?i)\bEdad(?: del paciente)?\s*:\s*\d+\s+([a-z]+)(?=\s+ID\b)"),
        ("id_paciente", r"(?i)(?:ID|CC|CE|TI)\s*:\s*([A-Za-z0-9]+)\s*(?=INDICACION)"),
        ("presion_terapeutica", r"(?i)se\s+observo\s+disminucion\s+de\s+eventos\s+respiratorios\s+a\s+(\d+)\s*cm\s*de\s*[agua|h20]"),
        ("mascara_tipo", r"(?i)(?:se\s+utilizo\s+)?mascara\s+(\w+)\s+talla"),
        ("mascara_tamano", r"(?i)talla\s*(?:[:=]\s*)?(?:[\"']?\s*([^\"'\s,)]+)\s*[\"']?|([^,\s)]+))(?=[,\s)]*(?:ref|\)|$))"),
        ("mascara_referencia", r"(?i)(?:ref|referencia)\s*[:\-]?\s*([^)]{1,60})(?:\)|$)")
        
]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos
