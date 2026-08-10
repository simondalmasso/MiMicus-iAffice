import unittest
from allora_edge.analytics import concentration
from allora_edge.rewards import canonical_topic_reward, simulate_reward

class RewardTests(unittest.TestCase):
    def test_concentration(self):
        r=concentration([0,1,3]); self.assertEqual(r['count'],3); self.assertAlmostEqual(r['zero_reward_share'],1/3)
    def test_reward_requires_inputs(self):
        r=simulate_reward(our_score='2',lowest_active_score='1'); self.assertTrue(r.would_be_active); self.assertIsNone(r.estimated_allo_reward); self.assertIn('topic_reward_or_canonical_topic_reward_inputs',r.missing_inputs)
    def test_inactive_zero(self):
        r=simulate_reward(our_score='0',lowest_active_score='1'); self.assertFalse(r.would_be_active); self.assertEqual(r.estimated_allo_reward,'0')
    def test_canonical_topic_reward_main_path(self):
        self.assertEqual(canonical_topic_reward(topic_weight='25',sum_topic_weights='100',current_emission_per_block='2',epoch_length=10),'5.00')

# canonical v0.16 main-path topic reward fraction * block emission * epoch length
