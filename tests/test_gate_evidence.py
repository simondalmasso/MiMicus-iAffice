import json, tempfile, unittest
from pathlib import Path
from allora_edge.gate_evidence import GateEvidenceRegistry

class GateEvidenceTests(unittest.TestCase):
    def test_unreviewed_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'g.json'; p.write_text(json.dumps({'topics':{'7':{'reviewed':False,'external_demand_evidence':True}}}))
            self.assertIsNone(GateEvidenceRegistry(p).for_topic(7).external_demand_evidence)
    def test_reviewed_loads(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'g.json'; p.write_text(json.dumps({'topics':{'7':{'reviewed':True,'external_demand_evidence':True,'liquid_reward_mechanism':True,'entry_cost_under_100':False,'source_urls':['https://example.invalid/evidence']}}}))
            e=GateEvidenceRegistry(p).for_topic(7); self.assertTrue(e.reviewed); self.assertTrue(e.external_demand_evidence); self.assertFalse(e.entry_cost_under_100)
