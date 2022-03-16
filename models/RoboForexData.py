import MetaTrader5 as mt5


class RoboForexData:

    def __init__(self, server, user, password):
        # establish MetaTrader 5 connection to a specified trading account
        if not mt5.initialize(login=user, server=server, password=password):
            print("initialize() failed, error code =", mt5.last_error())
            quit()

    def __del__(self):
        # shut down connection to the MetaTrader 5 terminal
        mt5.shutdown()

    def get_info(self):
        # display data on connection status, server name and trading account
        return mt5.terminal_info()

    def get_version(self):
        # display data on MetaTrader 5 version
        return mt5.version()

    def get_bars(self, symbol, timeframe, date_from, count):
        rates = mt5.copy_rates_from(symbol, timeframe, date_from, count)
        return rates
