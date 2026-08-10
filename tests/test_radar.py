import tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from allora_edge.models import TopicSnapshot
from allora_edge.radar import Radar
from allora_edge.storage import Storage

class FakeClient:
    def __init__(self, snapshots, *, head=100, catching=False, age=0, params=None):
        self.snapshots=snapshots; self.head=head; self.catching=catching
        self.spec=SimpleNamespace(name='mainnet',chain_id='allora-mainnet-1')
        self._params=params or {'global_worker_whitelist_enabled':True}
        self.latest_time=(datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat()
    def verify_network(self): return {'network':'mainnet','chain_id':'allora-mainnet-1','latest_block_height':self.head,'latest_block_time':self.latest_time,'catching_up':self.catching}
    def params(self): return self._params
    def next_topic_id(self): return max(self.snapshots)+1
    def census_topic(self, i, h):
        t=self.snapshots[i]; t.source_height=h; t.query_time_utc=datetime.now(timezone.utc).isoformat(); return t

class RadarTests(unittest.TestCase):
    def _run(self, client, dbpath, evdir):
        s=Storage(dbpath)
        try: return Radar(client,s,evdir).scan()
        finally: s.close()
    def test_dynamic_new_topic_and_fail_closed_whitelist(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); db=d/'x.db'; ev=d/'e'
            one=TopicSnapshot(1,True,True,metadata='BTC/USD price prediction',worker_whitelist_enabled=True,reward_nonce='1',next_worker_window_start=101)
            r1=self._run(FakeClient({1:one}),db,ev); self.assertEqual(r1['topic_count'],1); self.assertEqual(r1['eligible_count'],0)
            two=TopicSnapshot(2,True,True,metadata='Charger availability at ETA',worker_whitelist_enabled=False,reward_nonce='1',next_worker_window_start=101)
            r2=self._run(FakeClient({1:one,2:two},head=101,params={'global_worker_whitelist_enabled':False}),db,ev); self.assertEqual(r2['topic_count'],2); self.assertEqual(r2['non_trading_active_count'],1); self.assertEqual(r2['eligible_count'],0)
    def test_head_regression_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); db=d/'x.db'; ev=d/'e'; t=TopicSnapshot(1,True,True,metadata='BTC/USD')
            self._run(FakeClient({1:t},head=100),db,ev)
            with self.assertRaisesRegex(RuntimeError,'CHAIN_HEAD_REGRESSION'): self._run(FakeClient({1:t},head=99),db,ev)
    def test_stale_and_catching_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); t=TopicSnapshot(1,True,True,metadata='BTC/USD')
            with self.assertRaisesRegex(RuntimeError,'RPC_STALE_HEAD'): self._run(FakeClient({1:t},age=10000),d/'a.db',d/'ea')
            with self.assertRaisesRegex(RuntimeError,'RPC_CATCHING_UP'): self._run(FakeClient({1:t},catching=True),d/'b.db',d/'eb')
    def test_duplicate_observation_is_idempotent_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); s=Storage(d/'x.db')
            t=TopicSnapshot(1,True,True,metadata='BTC/USD',query_time_utc='2026-08-10T00:00:00+00:00')
            from allora_edge.classify import classify_topic
            from allora_edge.eligibility import evaluate_eligibility
            c=classify_topic(t.metadata); e=evaluate_eligibility(t,c,open_to_unknown_worker=False,worker_requests_exist=None,rewardable=False,external_demand_evidence=None,liquid_reward_mechanism=None,entry_cost_under_100=None)
            s.put_topic(t,c,e,[]); s.put_topic(t,c,e,[])
            self.assertEqual(s.db.execute('select count(*) c from topic_snapshots').fetchone()['c'],1); s.close()
