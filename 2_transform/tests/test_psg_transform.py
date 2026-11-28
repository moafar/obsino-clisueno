import re
import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import yaml
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "2_transform"))
sys.path.insert(0, str(ROOT / "1_extract"))

from src.basal.procesar_basal import PSG_COLUMNS
from transform_commons.engine import OperationRegistry, run_pipeline
from transform_commons.errors import SchemaValidationError
from transform_commons.io import read_dataset
from transform_commons.schema import validate_input_schema, validate_output_schema
from psg.core.transforms import DATA_TYPES, FINAL_COLS, register_psg_operations
from psg.main import (_discover_input_files, _load_pipeline_config,
                      _require_exact_columns, _validate_psg_input_schema, execute, run)
from xpap.core.transforms import DATA_TYPES as XPAP_DATA_TYPES
from xpap.core.transforms import FINAL_COLS as XPAP_FINAL_COLS
from xpap.core.transforms import register_xpap_operations


CONTRACT = ROOT / "0_declarations" / "psg.yaml"


def source_row(**overrides):
    row = dict.fromkeys(PSG_COLUMNS, "")
    row.update(pte_id="000123", meta_uuid="synthetic-uuid", meta_completitud_pct="0", pte_edad_anos="12",
               pte_peso_valor="70", pte_peso_unidad="kg",
               pte_talla_valor="170", pte_talla_unidad="cm",
               pte_cuello_valor="38", pte_cuello_unidad="cm",
               pte_perimetro_abdominal_valor="90", pte_perimetro_abdominal_unidad="cm",
               meta_fecha_estudio="01/02/2026", oxi_t90_despierto_min="0",
               clin_interpretacion="Texto íntegro con acentos.\nSegunda línea.")
    row.update(overrides)
    return row


class PSGTransformTest(unittest.TestCase):
    def setUp(self):
        self.config = _load_pipeline_config(str(CONTRACT), [ROOT])

    def transform(self, rows):
        source = pd.DataFrame(rows, columns=PSG_COLUMNS, dtype="string")
        registry = OperationRegistry()
        register_psg_operations(registry)
        _require_exact_columns(source, self.config["schema"]["input"], "entrada")
        _validate_psg_input_schema(source, self.config["schema"]["input"])
        output = run_pipeline(self.config, registry, source)
        _require_exact_columns(output, self.config["schema"]["output"], "salida")
        validate_output_schema(output, self.config["schema"]["output"])
        return output

    def test_contract_matches_dictionary_and_extract(self):
        dictionary = (ROOT / "docs" / "diccionario_datos_psg.md").read_text(encoding="utf-8")
        rows = re.findall(
            r"^\|\s*\d+\s*\|\s*`([a-z0-9_]+)`\*?\s*\|[^\n]*?\|\s*(texto|categoría|entero|decimal|fecha)\s*\|",
            dictionary, re.M,
        )
        types = {"texto": "string", "categoría": "string", "entero": "int",
                 "decimal": "float", "fecha": "date"}
        self.assertEqual(158, len(rows))
        self.assertEqual({name: types[kind] for name, kind in rows}, DATA_TYPES)
        self.assertEqual([name for name, _ in rows], FINAL_COLS)
        self.assertEqual(list(PSG_COLUMNS), list(self.config["schema"]["input"]["columns"]))
        self.assertEqual(FINAL_COLS, list(self.config["schema"]["output"]["columns"]))
        contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["schema"]["transform"]["output"],
                         contract["schema"]["load"]["input"])
        self.assertEqual("psg_basal_transform", self.config["steps"][0]["op"])
        transformed = self.transform([source_row()])
        for field, kind in DATA_TYPES.items():
            with self.subTest(field=field):
                if kind == "date":
                    self.assertTrue(pd.api.types.is_datetime64_any_dtype(transformed[field]))
                else:
                    self.assertEqual({"int": "Int64", "float": "Float64",
                                      "string": "string"}[kind], str(transformed[field].dtype))

    def test_derived_units_ages_nulls_zero_and_text(self):
        rows = [
            source_row(pte_edad_anos="11", pte_edad_meses="11", pte_edad_dias="0",
                       pte_peso_valor="70000", pte_peso_unidad="g",
                       pte_talla_valor="1,7", pte_talla_unidad="m",
                       pte_cuello_valor="380", pte_cuello_unidad="mm",
                       arq_eficiencia_pct="83,5", oxi_t90_pct="5,5",
                       evresp_ah_indice_evhora="10,1", evresp_iah_tst_evhora="11,2"),
            source_row(pte_id="000124", meta_uuid="synthetic-uuid-2",
                       pte_edad_anos="18", pte_edad_meses="", pte_edad_dias="",
                       pte_peso_valor="", pte_peso_unidad="kg",
                       oxi_t90_despierto_min=""),
            source_row(pte_id="000125", meta_uuid="synthetic-uuid-3",
                       pte_edad_anos="", pte_edad_meses="", pte_edad_dias=""),
        ]
        result = self.transform(rows)
        self.assertEqual(3, len(result))
        self.assertEqual(158, len(result.columns))
        self.assertEqual(["000123", "000124", "000125"], result["pte_id"].tolist())
        self.assertEqual(11.9167, result.loc[0, "pte_edad_decimal_anos"])
        self.assertEqual("Menor de 12", result.loc[0, "pte_grupo_edad"])
        self.assertEqual("Mayor de 18", result.loc[1, "pte_grupo_edad"])
        self.assertTrue(pd.isna(result.loc[2, "pte_edad_decimal_anos"]))
        self.assertTrue(pd.isna(result.loc[2, "pte_grupo_edad"]))
        self.assertEqual((70, 170, 38, 90), tuple(result.loc[0, [
            "pte_peso_kg", "pte_talla_cm", "pte_cuello_cm", "pte_perimetro_abdominal_cm"]]))
        self.assertTrue(pd.isna(result.loc[1, "pte_peso_kg"]))
        self.assertEqual(0, result.loc[0, "oxi_t90_despierto_min"])
        self.assertEqual(83.5, result.loc[0, "arq_eficiencia_pct"])
        self.assertEqual(5.5, result.loc[0, "oxi_t90_pct"])
        self.assertEqual(10.1, result.loc[0, "evresp_ah_indice_evhora"])
        self.assertEqual(11.2, result.loc[0, "evresp_iah_tst_evhora"])
        self.assertTrue(pd.isna(result.loc[1, "oxi_t90_despierto_min"]))
        self.assertEqual(0, result.loc[0, "meta_completitud_pct"])
        self.assertEqual(rows[0]["clin_interpretacion"], result.loc[0, "clin_interpretacion"])
        self.assertEqual("Int64", str(result["pte_edad_anos"].dtype))
        self.assertEqual("Float64", str(result["pte_peso_kg"].dtype))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["meta_fecha_estudio"]))
        self.assertTrue(result["meta_incidencias_calidad"].isna().all())

    def test_invalid_metadata_and_duplicate_uuid_raise_without_dropping(self):
        for changes in (
            {"meta_completitud_pct": "101"},
            {"meta_completitud_pct": "valor ilegible"},
            {"meta_fecha_estudio": "fecha imposible"},
        ):
            with self.subTest(changes=changes), self.assertRaises((ValueError, SchemaValidationError)):
                self.transform([source_row(**changes)])
        with self.assertRaisesRegex(ValueError, "duplicado"):
            self.transform([source_row(), source_row(pte_id="000124")])

    def test_incompatible_clinical_numbers_become_null_with_original_value(self):
        rows = [
            source_row(pte_edad_anos="12,5", arq_tiempo_sueno_min="valor ilegible",
                       pte_peso_valor="peso?", evresp_ah_numero_n="inf",
                       clin_epworth_puntos="9999999999999999999999"),
            source_row(meta_uuid="clean-2", pte_id="000124", pte_edad_anos="0",
                       arq_tiempo_sueno_min="3,5", pte_peso_valor="70000",
                       pte_peso_unidad="g"),
            source_row(meta_uuid="absent-3", pte_id="000125", pte_edad_anos="N/A",
                       arq_tiempo_sueno_min="--", pte_peso_valor=""),
        ]
        result = self.transform(rows)
        for column in ("pte_edad_anos", "arq_tiempo_sueno_min", "pte_peso_kg",
                       "evresp_ah_numero_n"):
            self.assertTrue(pd.isna(result.loc[0, column]), column)
        self.assertEqual("Int64", str(result["pte_edad_anos"].dtype))
        self.assertEqual("Float64", str(result["arq_tiempo_sueno_min"].dtype))
        self.assertEqual(0, result.loc[1, "pte_edad_anos"])
        self.assertEqual(3.5, result.loc[1, "arq_tiempo_sueno_min"])
        self.assertEqual(70, result.loc[1, "pte_peso_kg"])
        self.assertTrue(result.loc[1:, "meta_incidencias_calidad"].isna().all())
        incidents = json.loads(result.loc[0, "meta_incidencias_calidad"])
        self.assertEqual(5, len(incidents))
        self.assertEqual({"pte_edad_anos": "12,5", "arq_tiempo_sueno_min": "valor ilegible",
                          "evresp_ah_numero_n": "inf", "pte_peso_valor": "peso?",
                          "clin_epworth_puntos": "9999999999999999999999"},
                         {item["campo"]: item["valor_original"] for item in incidents})
        self.assertTrue(all(set(item) == {"campo", "valor_original", "error", "accion"}
                            and item["accion"] == "convertido_a_null" for item in incidents))
        self.assertEqual(result.loc[0, "meta_incidencias_calidad"],
                         self.transform(rows).loc[0, "meta_incidencias_calidad"])

    def test_invalid_anthropometric_units_become_null(self):
        cases = [
            ("cuello", "41", "c"),
            ("cuello", "43", "anos"),
            ("talla", "178", "imc"),
            ("cuello", "38", ""),
            ("cuello", "35", ""),
            ("peso", "70", "unidad desconocida"),
        ]
        rows = [
            source_row(meta_uuid=f"invalid-unit-{index}", pte_id=str(1000 + index),
                       **{f"pte_{part}_valor": value, f"pte_{part}_unidad": unit})
            for index, (part, value, unit) in enumerate(cases)
        ]
        result = self.transform(rows)
        self.assertEqual(len(cases), len(result))
        for index, (part, _, _) in enumerate(cases):
            target = {"peso": "pte_peso_kg", "talla": "pte_talla_cm",
                      "cuello": "pte_cuello_cm"}[part]
            with self.subTest(index=index, target=target):
                self.assertTrue(pd.isna(result.loc[index, target]))
        # Las medidas con unidades válidas del mismo registro siguen convirtiéndose.
        self.assertEqual(170.0, result.loc[0, "pte_talla_cm"])
        self.assertEqual(38.0, result.loc[2, "pte_cuello_cm"])
        self.assertEqual(70.0, result.loc[0, "pte_peso_kg"])

    def test_t90_percentage_fallback_preserves_reported_value_and_nulls(self):
        rows = [
            source_row(arq_tiempo_sueno_min="200", oxi_t90_tst_min="11"),
            source_row(pte_id="000124", meta_uuid="synthetic-uuid-2",
                       arq_tiempo_sueno_min="200", oxi_t90_tst_min="11", oxi_t90_pct="6,7"),
            source_row(pte_id="000125", meta_uuid="synthetic-uuid-3",
                       arq_tiempo_sueno_min="200", oxi_t90_tst_min="0"),
            source_row(pte_id="000126", meta_uuid="synthetic-uuid-4",
                       arq_tiempo_sueno_min="200"),
        ]
        result = self.transform(rows)
        self.assertEqual([5.5, 6.7, 0], result["oxi_t90_pct"].iloc[:3].tolist())
        self.assertTrue(pd.isna(result.loc[3, "oxi_t90_pct"]))

    def test_t90_reported_zero_and_missing_denominator(self):
        rows = [
            source_row(
                oxi_t90_pct="0",
                oxi_t90_tst_min="11",
                arq_tiempo_sueno_min="200",
            ),
            source_row(
                pte_id="000124",
                meta_uuid="synthetic-uuid-2",
                oxi_t90_tst_min="11",
                arq_tiempo_sueno_min="",
            ),
        ]
        result = self.transform(rows)
        self.assertEqual(0.0, result.loc[0, "oxi_t90_pct"])
        self.assertTrue(pd.isna(result.loc[1, "oxi_t90_pct"]))

    def test_t90_zero_sleep_is_indeterminate_not_zero(self):
        rows = [
            source_row(meta_uuid="zero-sleep-1", arq_tiempo_sueno_min="0",
                       arq_eficiencia_pct="0", fase_rem_duracion_min="0",
                       oxi_t90_tst_min="0,0"),
            source_row(meta_uuid="zero-sleep-2", pte_id="000124",
                       arq_tiempo_sueno_min="0", oxi_t90_tst_min="0"),
            source_row(meta_uuid="sleep-positive", pte_id="000125",
                       arq_tiempo_sueno_min="200", oxi_t90_tst_min="11"),
        ]
        result = self.transform(rows)
        self.assertEqual(3, len(result))
        self.assertTrue(pd.isna(result.loc[0, "oxi_t90_pct"]))
        self.assertTrue(pd.isna(result.loc[1, "oxi_t90_pct"]))
        self.assertEqual(5.5, result.loc[2, "oxi_t90_pct"])
        self.assertEqual(0.0, result.loc[0, "arq_tiempo_sueno_min"])
        self.assertEqual(0.0, result.loc[0, "oxi_t90_tst_min"])

    def test_t90_percentage_rejects_invalid_derivation(self):
        for minutes, total in (("1", "0"), ("11", "10"), ("-1", "200")):
            with self.subTest(minutes=minutes, total=total), self.assertRaisesRegex(ValueError, "oxi_t90_pct"):
                self.transform([source_row(oxi_t90_tst_min=minutes,
                                           arq_tiempo_sueno_min=total)])

    def test_csv_to_xlsx_runs_psg_step_and_preserves_id(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "extract_psg_2026-11-23_12-00.csv"
            target = Path(folder) / "output.xlsx"
            pd.DataFrame([source_row(arq_tiempo_sueno_min="200", oxi_t90_tst_min="11")],
                         columns=PSG_COLUMNS).to_csv(source, index=False)
            read_back = read_dataset(str(source), config=self.config["input"])
            self.assertEqual("000123", read_back.loc[0, "pte_id"])
            self.assertEqual("", read_back.loc[0, "pte_edad_meses"])
            self.assertEqual(target, run(str(CONTRACT), str(source), str(target)))
            workbook = load_workbook(target, read_only=True, data_only=True)
            try:
                sheet = workbook.active
                self.assertEqual(158, sheet.max_column)
                self.assertEqual("000123", sheet.cell(2, FINAL_COLS.index("pte_id") + 1).value)
                self.assertEqual(70, sheet.cell(2, FINAL_COLS.index("pte_peso_kg") + 1).value)
                self.assertEqual(5.5, sheet.cell(2, FINAL_COLS.index("oxi_t90_pct") + 1).value)
                self.assertEqual("De 12 a 18", sheet.cell(2, FINAL_COLS.index("pte_grupo_edad") + 1).value)
                self.assertEqual("Texto íntegro con acentos.\nSegunda línea.",
                                 sheet.cell(2, FINAL_COLS.index("clin_interpretacion") + 1).value)
            finally:
                workbook.close()

    def test_incidence_is_serialized_in_xlsx_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "extract_psg_synthetic.csv"
            target = Path(folder) / "output.xlsx"
            pd.DataFrame([source_row(arq_tiempo_sueno_min="no numérico")],
                         columns=PSG_COLUMNS).to_csv(source, index=False)
            self.assertEqual(target, run(str(CONTRACT), str(source), str(target)))
            workbook = load_workbook(target, read_only=True, data_only=True)
            try:
                value = workbook.active.cell(2, FINAL_COLS.index("meta_incidencias_calidad") + 1).value
                self.assertEqual([{
                    "campo": "arq_tiempo_sueno_min", "valor_original": "no numérico",
                    "error": "decimal_incompatible", "accion": "convertido_a_null",
                }], json.loads(value))
            finally:
                workbook.close()

    def test_exact_schema_and_autodiscovery_excludes_results(self):
        frame = pd.DataFrame([source_row()], columns=PSG_COLUMNS)
        with self.assertRaises(ValueError):
            _require_exact_columns(frame[list(PSG_COLUMNS[::-1])], self.config["schema"]["input"], "entrada")
        with self.assertRaises(ValueError):
            _require_exact_columns(frame.drop(columns="meta_uuid"), self.config["schema"]["input"], "entrada")
        with self.assertRaises(ValueError):
            _require_exact_columns(frame.assign(unexpected="x"), self.config["schema"]["input"], "entrada")
        with tempfile.TemporaryDirectory() as folder:
            for name in (
                "extract_psg_2026-11-23_12-00.csv",
                "extract_psg_2026-11-23_12-00_transformed.csv",
                "extract_psg_2026-11-23_12-00_transformed.xlsx",
            ):
                (Path(folder) / name).touch()
            with patch("psg.main.STAGING_DIR", Path(folder)):
                self.assertEqual(["extract_psg_2026-11-23_12-00.csv"],
                                 [path.name for path in _discover_input_files()])

    def test_shared_csv_reader_and_runner_keep_xpap_behavior(self):
        row = dict.fromkeys(XPAP_DATA_TYPES, "")
        row.update(id="123456", edad_anos="12", peso="70", medida_peso="kg",
                   talla="170", medida_talla="cm", fecha_estudio="01/02/2026",
                   uuid="synthetic-xpap")
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic_xpap.csv"
            pd.DataFrame([row]).to_csv(source, index=False)
            read_back = read_dataset(str(source), config={"format": "csv"})
        registry = OperationRegistry()
        register_xpap_operations(registry)
        output = run_pipeline({"steps": [{"op": "xpap_transform", "params": {}}]},
                              registry, read_back)
        self.assertEqual(XPAP_FINAL_COLS, list(output.columns))
        self.assertEqual(1, len(output))
        self.assertEqual("synthetic-xpap", output.loc[0, "xpap_uuid"])

    def test_execution_checks_uuids_across_selected_csvs_before_writing(self):
        first_name = "extract_psg_2026-11-23_12-00.csv"
        second_name = "extract_psg_2026-11-23_12-01.csv"

        def exercise(rows_by_file, explicit_input=False):
            with tempfile.TemporaryDirectory() as folder:
                staging = Path(folder)
                for name, rows in rows_by_file.items():
                    pd.DataFrame(rows, columns=PSG_COLUMNS).to_csv(staging / name, index=False)
                chosen = str(staging / first_name) if explicit_input else None
                with patch("psg.main.STAGING_DIR", staging), \
                     patch("psg.main._confirm_execution", return_value=True), \
                     redirect_stdout(io.StringIO()):
                    try:
                        result = execute(str(CONTRACT), chosen, None, False)
                        error = None
                    except ValueError as exc:
                        result, error = None, str(exc)
                return result, error, sorted(path.name for path in staging.glob("*_transformed.xlsx"))

        unique = {
            first_name: [source_row(meta_uuid="uuid-1")],
            second_name: [source_row(meta_uuid="uuid-2", pte_id="000124")],
        }
        result, error, outputs = exercise(unique)
        self.assertEqual((0, None, 2), (result, error, len(outputs)))

        shared = {**unique, second_name: [source_row(meta_uuid="uuid-1", pte_id="000124")]}
        result, error, outputs = exercise(shared)
        self.assertIsNone(result)
        self.assertIn(first_name, error)
        self.assertIn(second_name, error)
        self.assertEqual([], outputs)

        repeated = {first_name: [source_row(meta_uuid="uuid-1"),
                                 source_row(meta_uuid="uuid-1", pte_id="000124")]}
        result, error, outputs = exercise(repeated)
        self.assertIsNone(result)
        self.assertIn(first_name, error)
        self.assertEqual([], outputs)

        result, error, outputs = exercise({first_name: [source_row()]}, explicit_input=True)
        self.assertEqual((0, None, 1), (result, error, len(outputs)))


if __name__ == "__main__":
    unittest.main()
