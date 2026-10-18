import json
import tempfile
import unittest
from pathlib import Path
from caea.run import run


class OutputLifecycle(unittest.TestCase):
    def test_llm_restart_does_not_append_duplicate_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,'llm_calls.jsonl');path.write_text('preserved old trace\n')
            with self.assertRaisesRegex(ValueError,'fresh run directory'):
                run({'llm':{'model':'unused'}},folder)
            self.assertEqual(path.read_text(),'preserved old trace\n')

    def test_configuration_cannot_overwrite_existing_run(self):
        with tempfile.TemporaryDirectory() as folder:
            original={'settings':[],'methods':[],'case_seeds':[]}
            run(original,folder)
            with self.assertRaisesRegex(ValueError,'different configuration'):
                run({**original,'capacity':2},folder)
            self.assertEqual(json.loads(Path(folder,'used_config.json').read_text()),original)
