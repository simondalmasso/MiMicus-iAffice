import unittest
from allora_edge.classify import classify_topic
from allora_edge.models import TopicClass

class ClassificationTests(unittest.TestCase):
    def test_trading_crypto_price(self):
        self.assertEqual(classify_topic('BTC/USD - Price Prediction - 8h').classification, TopicClass.TRADING)
    def test_trading_volatility(self):
        self.assertEqual(classify_topic('ETH/USD - Volatility - 15m').classification, TopicClass.TRADING)
    def test_non_trading(self):
        self.assertEqual(classify_topic('Charger availability at ETA').classification, TopicClass.NON_TRADING)
    def test_unknown_fails_closed(self):
        self.assertEqual(classify_topic('mystery topic').classification, TopicClass.UNKNOWN)
