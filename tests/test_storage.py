import tempfile, unittest
from pathlib import Path
from allora_edge.models import Classification, EligibilityDecision, TopicClass, TopicSnapshot
from allora_edge.storage import Storage

class StorageTests(unittest.TestCase):
    def test_restart_safe(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'db.sqlite3'; s=Storage(path)
            t=TopicSnapshot(topic_id=7,exists=True,active=True,metadata='Charger availability',query_time_utc='2026-01-01T00:00:00Z')
            c=Classification(TopicClass.NON_TRADING,'physical',['charger availability'],'HIGH')
            e=EligibilityDecision(7,False,{'x':None},['x'],[])
            s.put_topic(t,c,e,['NEW_TOPIC']); s.close()
            s2=Storage(path); self.assertEqual(s2.health()['topic_count'],1); self.assertEqual(s2.latest_topic(7).metadata,'Charger availability'); s2.close()
