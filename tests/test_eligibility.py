import unittest
from allora_edge.eligibility import evaluate_eligibility
from allora_edge.models import Classification, TopicClass, TopicSnapshot

class EligibilityTests(unittest.TestCase):
    def topic(self): return TopicSnapshot(topic_id=1, exists=True, active=True)
    def test_all_true(self):
        c=Classification(TopicClass.NON_TRADING,'x',[],'HIGH')
        d=evaluate_eligibility(self.topic(),c,open_to_unknown_worker=True,worker_requests_exist=True,rewardable=True,external_demand_evidence=True,liquid_reward_mechanism=True,entry_cost_under_100=True)
        self.assertTrue(d.eligible)
    def test_unknown_fails_closed(self):
        c=Classification(TopicClass.UNKNOWN,'x',[],'LOW')
        d=evaluate_eligibility(self.topic(),c,open_to_unknown_worker=None,worker_requests_exist=True,rewardable=True,external_demand_evidence=True,liquid_reward_mechanism=True,entry_cost_under_100=True)
        self.assertFalse(d.eligible)
        self.assertIn('NON_TRADING', d.blockers)
