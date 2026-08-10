import unittest
from allora_edge.benchmark import benchmark
from allora_edge.http import HttpResult

class BenchmarkTests(unittest.TestCase):
    def test_percentiles_and_error_rate(self):
        vals=iter([1.0,2.0,3.0])
        def call(): return HttpResult({},next(vals),200,{})
        r=benchmark(call,3); self.assertEqual(r.successes,3); self.assertEqual(r.error_rate,0); self.assertEqual(r.p50_ms,2.0); self.assertGreater(r.p99_ms,2.9)
    def test_errors(self):
        def call(): raise RuntimeError('x')
        r=benchmark(call,2); self.assertEqual(r.errors,2); self.assertIsNone(r.p50_ms)
