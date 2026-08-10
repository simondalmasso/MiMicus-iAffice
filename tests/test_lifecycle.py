import unittest
from allora_edge.lifecycle import infer_lifecycle, transition_events
from allora_edge.models import LifecycleState, TopicSnapshot

class LifecycleTests(unittest.TestCase):
    def test_states(self):
        self.assertEqual(infer_lifecycle(TopicSnapshot(1,True,False)).state, LifecycleState.INACTIVE)
        self.assertEqual(infer_lifecycle(TopicSnapshot(1,True,True,worker_window_open=True)).state, LifecycleState.WORKER_REQUEST)
        self.assertEqual(infer_lifecycle(TopicSnapshot(1,True,True,reward_nonce='9')).state, LifecycleState.REWARDABLE)
    def test_transition(self):
        a=TopicSnapshot(1,True,False,fee_revenue='0',worker_whitelist_enabled=False)
        b=TopicSnapshot(1,True,True,fee_revenue='1',worker_whitelist_enabled=True)
        events=transition_events(a,b); self.assertIn('TOPIC_ACTIVATED',events); self.assertIn('FEE_REVENUE_CHANGED',events); self.assertIn('WORKER_WHITELIST_CHANGED',events)
