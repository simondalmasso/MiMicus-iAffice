import unittest
from allora_edge.models import TopicClass
from allora_edge.shadow import AbsoluteErrorLoss, ShadowWorkerEngine

class T:
    def request_context(self, topic_id): return {'topic_id':topic_id}
class D:
    def fetch(self, context): return {'available_ports':3}
class M:
    def infer(self, data): return data['available_ports']/4
class G:
    def ground_truth(self, context): return 1.0
class R:
    def estimate(self, loss, context): return {'would_be_rewarded':None,'confidence':'LOW'}

class ShadowTests(unittest.TestCase):
    def test_non_trading_shadow(self):
        r=ShadowWorkerEngine().run(topic_id=99,topic_class=TopicClass.NON_TRADING,topic_adapter=T(),data_source=D(),model=M(),truth_adapter=G(),loss_adapter=AbsoluteErrorLoss(),reward_estimator=R())
        self.assertFalse(r.submitted); self.assertEqual(len(r.inference_hash),64)
    def test_trading_blocked(self):
        with self.assertRaisesRegex(RuntimeError,'TRADING_MODEL_EXECUTION_PROHIBITED_BY_ORDER_001'):
            ShadowWorkerEngine().run(topic_id=1,topic_class=TopicClass.TRADING,topic_adapter=T(),data_source=D(),model=M(),truth_adapter=G(),loss_adapter=AbsoluteErrorLoss(),reward_estimator=R())
