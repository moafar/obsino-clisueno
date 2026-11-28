"""Pipeline sintético completo: CLI reales hasta Parquet y BigQuery simulado."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '1_extract/tests'))
sys.path.insert(0, str(ROOT / '3_load/tests'))
from test_psg_extractor import synthetic_report
import test_psg_load as fixture


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Pt07PipelineTest(unittest.TestCase):
    def test_real_extraction_transform_and_recovery_of_lost_load_response(self):
        with tempfile.TemporaryDirectory() as directory:
            code = Path(directory) / 'code'
            def excluded(_path, names):
                return [n for n in names if n in ('tests', 'secrets', '__pycache__', '.venv', 'logs', 'staging')
                        or (Path(_path, n).is_file() and Path(n).suffix not in ('.py', '.yaml'))]
            for name in ('0_declarations', '1_extract', '2_transform', '3_load', 'scripts'):
                shutil.copytree(ROOT / name, code / name, ignore=excluded)
            (code / 'staging').mkdir()
            source, archive = Path(directory) / 'source', Path(directory) / 'archive'
            source.mkdir(); archive.mkdir()
            text = synthetic_report('rtf')
            body = ''.join('\\par\n' if ch == '\n' else '\\' + ch if ch in '\\{}'
                           else f'\\u{ord(ch)}?' if ord(ch) > 127 else ch for ch in text)
            (source / 'synthetic.rtf').write_text('{\\rtf1\\ansi ' + body + '}', encoding='ascii')
            key = code / '3_load/secrets/synthetic.json'
            key.parent.mkdir(); key.write_text('{}')
            contract = code / '0_declarations/psg.yaml'
            config = yaml.safe_load(contract.read_text())
            config['load'].update(project_id='synthetic-test', dataset_id='test_dataset',
                                  table_id='test_psg', service_account_json=str(key))
            contract.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
            pipeline = module_at('pt07_sandbox_pipeline', code / 'scripts/run_psg.py')
            loader = module_at('pt07_sandbox_load', code / '3_load/main.py')
            schema = loader.build_bq_schema(loader.load_schema(contract, 'schema.load.input.columns'))
            client = fixture.FakeClient(schema)
            def lost(frame, table, **kwargs):
                job = client._load(frame, table, **kwargs)
                job.result()
                raise TimeoutError('respuesta remota perdida')
            client.load_table_from_dataframe = Mock(side_effect=lost)
            real_subprocess = subprocess.run
            def invoke(command, **options):
                if Path(command[1]) != code / '3_load/main.py':
                    return real_subprocess(command, **options)
                def arg(flag):
                    return command[command.index(flag) + 1]
                runtime = loader.load_runtime_config(contract, Path(arg('--input')), arg('--table-id'))
                with patch.dict(os.environ, {'PSG_LOCK_FD': options['env']['PSG_LOCK_FD']}), \
                     patch.object(loader, 'authenticate_bigquery', return_value=client):
                    try:
                        result = loader.run(runtime, 'psg', non_interactive=True)
                    except TimeoutError:
                        raise subprocess.CalledProcessError(1, command) from None
                loader.save(Path(arg('--result-json')), result)
                return subprocess.CompletedProcess(command, 0)
            with patch.object(pipeline, 'preflight'), patch.object(pipeline.subprocess, 'run', side_effect=invoke), \
                 redirect_stdout(io.StringIO()):
                with self.assertRaises(subprocess.CalledProcessError):
                    pipeline.run(source, archive, Path(directory), 'test_psg')
                record_path = next((code / 'staging/psg_runs').glob('*/run.json'))
                record = json.loads(record_path.read_text())
                before = json.loads(Path(record['paths']['load_state']).read_text())
                self.assertEqual('UNKNOWN', before['state'])
                pipeline.run(resume_id=record['id'])
            final = json.loads(record_path.read_text())
            self.assertIn(final['state'], ('OK', 'WARNING'))
            self.assertEqual(1, final['counts']['extracted'])
            self.assertEqual(1, final['counts']['inserted'])
            self.assertEqual(before['job_id'], final['job_id'])
            self.assertEqual(1, client.load_table_from_dataframe.call_count)
            frame = pd.read_parquet(final['paths']['loaded'])
            self.assertEqual('000123', frame.loc[0, 'pte_id'])
            self.assertEqual(158, len(frame.columns))
            self.assertFalse((source / 'synthetic.rtf').exists())
            self.assertEqual(1, len(list(archive.rglob('*.rtf'))))
