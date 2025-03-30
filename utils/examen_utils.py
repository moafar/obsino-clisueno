import re

def determinar_tipos_examenes(texto: str) -> list:
    tipos_examen = {
        "BASAL": [r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL"],
        "CPAP": [r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+EN\s+TITULACION\s+DE\s+CPAP"],
        "DAM": [r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL\s+CON\s+DISPOSITIVO(\s+DE\s+AVANCE)?\s+MANDIBULAR"],
        "BPAP": [r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+EN\s+TITULACION\s+DE\s+B[I]?PAP"],
        "ACTIGRAFIA": [r"INFORME\s+ACTIGRAFIA"],
        "CAPNOGRAFIA": [r"INFORME\s+DE\s+CAPNOGRAFIA"],
        "AUTOCPAP": [r"INFORME\s+DE\s+TITULACION\s+CON\s+AUTO\s+CPAP"],
        "POLIGRAFIA": [r"INFORME\s+POLIGRAFIA\s+RESPIRATORIA"]
    }
    tipos_detectados = []
    for tipo, patrones in tipos_examen.items():
        for patron in patrones:
            if re.search(patron, texto, re.IGNORECASE):
                tipos_detectados.append(tipo)
                break
    if not tipos_detectados:
        tipos_detectados.append("DESCONOCIDO")
    return tipos_detectados
