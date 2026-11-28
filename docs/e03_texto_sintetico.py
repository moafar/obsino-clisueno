"""Compara texto DOC/RTF sintético sin alterar el extractor ni instalar nada."""

import difflib
import hashlib
import json
import tempfile
from pathlib import Path

from e01_perfil_extractor import as_rtf, synthetic_report
from e02_benchmark import generate_corpus
from extract_commons.texto_utils import extraer_texto_doc, extraer_texto_rtf
from src.basal.procesar_basal import procesar_basal_doc, procesar_basal_rtf


def summary(text):
    return {"length": len(text), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "lines": text.count("\n") + 1, "tabs": text.count("\t"),
            "pipes": text.count("|")}


with tempfile.TemporaryDirectory(prefix="e03-texto-") as folder:
    root = Path(folder)
    corpus = generate_corpus(root, 1, True)
    doc_source = root / "doc_source/synthetic_0000.rtf"
    doc = corpus["doc"] / "synthetic_0000.doc"
    rtf = corpus["rtf"] / "synthetic_0000.rtf"
    source_doc_text = synthetic_report("doc").replace("000123", "000001")
    source_rtf_text = synthetic_report("rtf").replace("000123", "000001")
    rtf_doc_text = extraer_texto_rtf(doc_source)
    doc_text = extraer_texto_doc(doc)
    rtf_text = extraer_texto_rtf(rtf)
    if not all((rtf_doc_text, doc_text, rtf_text)):
        raise RuntimeError("Falló alguna conversión de texto sintético")
    doc_row = procesar_basal_doc(doc_text, doc)
    rtf_row = procesar_basal_rtf(rtf_text, rtf)
    result = {
        "doc_from_rtf": {
            "source": summary(source_doc_text), "rtf_extractor": summary(rtf_doc_text),
            "catdoc": summary(doc_text),
            "exact_equal": rtf_doc_text == doc_text,
            "whitespace_equal": " ".join(rtf_doc_text.split()) == " ".join(doc_text.split()),
            "sequence_ratio": round(difflib.SequenceMatcher(None, rtf_doc_text, doc_text).ratio(), 6),
            "parsed_columns": len(doc_row), "parsed_id": doc_row["pte_id"],
            "parsed_completeness": doc_row["meta_completitud_pct"],
        },
        "rtf_direct": {
            "source": summary(source_rtf_text), "striprtf": summary(rtf_text),
            "exact_equal": source_rtf_text == rtf_text,
            "parsed_columns": len(rtf_row), "parsed_id": rtf_row["pte_id"],
            "parsed_completeness": rtf_row["meta_completitud_pct"],
        },
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
