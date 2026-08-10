import tempfile, unittest
from pathlib import Path
from allora_edge.config import WRITE_LOCK_ERROR
from allora_edge.safety import LiveExecutionProhibited, assert_read_only_operation, assert_safe_url, scan_tree

class SafetyTests(unittest.TestCase):
    def test_write_lock_commands(self):
        for op in ['create-topic','fund-topic','register','remove-registration','insert-worker-payload','insert-reputer-payload','add-stake','delegate-stake','MsgRegister','broadcast_tx']:
            with self.subTest(op=op), self.assertRaisesRegex(LiveExecutionProhibited, WRITE_LOCK_ERROR): assert_read_only_operation(op)
    def test_get_path_allowed(self):
        assert_safe_url('https://allora-api.mainnet.allora.network/emissions/v9/next_topic_id')
    def test_credential_url_rejected(self):
        with self.assertRaises(ValueError): assert_safe_url('https://' + 'u' + ':' + 'p' + '@example.com/read')
    def test_secret_scan(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'a.txt').write_text('Bearer ' + 'A'*30,encoding='utf-8')
            self.assertTrue(scan_tree(p))
