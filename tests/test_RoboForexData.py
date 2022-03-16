from unittest import TestCase
from models.RoboForexData import RoboForexData
import MetaTrader5 as mt5
import os
from datetime import datetime


class TestRoboForexData(TestCase):

    def setUp(self):
        self.server = os.getenv('ROBOFOREX_SERVER', 'RoboForex-ECN')
        self.user = int(os.getenv('ROBOFOREX_USER', '123456'))
        self.password = os.getenv('ROBOFOREX_PASSWORD', '')
        self.rf = RoboForexData(self.server, self.user, self.password)

    def test_get_info(self):
        info = self.rf.get_info()
        self.assertIsInstance(info, mt5.TerminalInfo)

    def test_get_version(self):
        version = self.rf.get_version()
        self.assertIsInstance(version, tuple)

    def test_get_bars(self):
        data = self.rf.get_bars(symbol="EURUSD", timeframe=mt5.TIMEFRAME_M5, date_from=datetime(2022, 3, 11, 10), count=100)
        self.assertEqual(data[0][0], 1646959500)
        self.assertEqual(data[0][1], 1.09885)
        self.assertEqual(data[0][2], 1.09906)
        self.assertEqual(data[0][3], 1.09883)
        self.assertEqual(data[0][4], 1.09903)
        self.assertEqual(data[0][5], 27)
        self.assertEqual(data[0][6], 16)
        self.assertEqual(data[0][7], 0)
