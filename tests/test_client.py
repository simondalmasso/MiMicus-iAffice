import unittest
from allora_edge.client import SchemaMismatch, VersionAwareAlloraClient
from allora_edge.http import HttpResult, ReadError, ReadOnlyHttpClient

class Fake:
    def __init__(self): self.calls=[]; self.once429=True
    def __call__(self,url,timeout):
        self.calls.append(url)
        if '/status?' in url: return HttpResult({'result':{'node_info':{'network':'allora-mainnet-1','version':'0.38.19'},'sync_info':{'latest_block_height':'10','earliest_block_height':'1','catching_up':False}}},1,200,{})
        if url.endswith('/next_topic_id'):
            if self.once429: self.once429=False; raise ReadError('HTTP 429 for '+url)
            return HttpResult({'next_topic_id':'24'},1,200,{})
        if url.endswith('/params'): return HttpResult({'params':{'version':'v7'}},1,200,{})
        if '/topic_exists/1' in url: return HttpResult({'exists':True},1,200,{})
        if '/topics/1' in url: return HttpResult({'topic':{'id':'1','metadata':'BTC/USD'},'weight':'1'},1,200,{})
        if '/is_topic_active/1' in url: return HttpResult({'is_active':False},1,200,{})
        raise ReadError('not found')

class ClientTests(unittest.TestCase):
    def test_version_path_and_retry(self):
        f=Fake(); c=VersionAwareAlloraClient('mainnet',ReadOnlyHttpClient(f,retries=1)); self.assertEqual(c.next_topic_id(),24); self.assertIn('/emissions/v9/next_topic_id',f.calls[-1])
    def test_chain_verify(self):
        f=Fake(); c=VersionAwareAlloraClient('mainnet',ReadOnlyHttpClient(f)); self.assertEqual(c.verify_network()['chain_id'],'allora-mainnet-1')
    def test_malformed(self):
        def bad(url,timeout): return HttpResult({},1,200,{})
        c=VersionAwareAlloraClient('mainnet',ReadOnlyHttpClient(bad));
        with self.assertRaises(SchemaMismatch): c.next_topic_id()
    def test_testnet_v10(self):
        c=VersionAwareAlloraClient('testnet',ReadOnlyHttpClient(Fake())); self.assertTrue(c.api_root.endswith('/emissions/v10'))
    def test_census_checks_existence(self):
        f=Fake(); c=VersionAwareAlloraClient('mainnet',ReadOnlyHttpClient(f)); t=c.census_topic(1,10); self.assertTrue(t.exists); self.assertFalse(t.active)
