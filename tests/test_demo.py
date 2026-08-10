import tempfile, unittest
from pathlib import Path
from allora_edge.demo import run_synthetic_demo
from allora_edge.storage import Storage

class DemoTests(unittest.TestCase):
    def test_fixture_is_non_economic_and_persisted(self):
        with tempfile.TemporaryDirectory() as d:
            db=Storage(Path(d)/'x.db')
            r=run_synthetic_demo(Path('tests/fixtures/synthetic_non_trading.json'), persist=db.put_shadow_result)
            self.assertFalse(r['submitted']); self.assertFalse(r['economic_evidence']); self.assertEqual(r['source_tag'],'SYNTHETIC_FIXTURE')
            self.assertEqual(db.db.execute('select count(*) c from shadow_runs').fetchone()['c'],1)
            db.close()
