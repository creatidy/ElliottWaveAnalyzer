from time import sleep

import pandas
import yfinance as yf
import requests_cache
import numpy as np
from pandas import DataFrame
from models.WavePattern import WavePattern
from models.WaveRules import Impulse, LeadingDiagonal
from models.WaveAnalyzer import WaveAnalyzer
from models.WaveOptions import WaveOptionsGenerator5
from models.helpers import plot_pattern

from multiprocessing import Pool

POOL = 7  # 1 for single process; 2 or more for multiprocessing (limited debugging)
PERIOD = '1mo'
INTERVAL = '1h'
WAVE_UP_TO = 5
TICKERS = ['EURUSD=X', 'JPY=X', 'GBPUSD=X', 'AUDUSD=X', 'NZDUSD=X', 'EURJPY=X', 'GBPJPY=X', 'EURGBP=X', 'EURCAD=X',
           'EURSEK=X', 'EURCHF=X', 'EURHUF=X', 'EURJPY=X', 'CNY=X', 'HKD=X', 'SGD=X', 'INR=X', 'MXN=X', 'PHP=X',
           'IDR=X', 'THB=X', 'MYR=X', 'ZAR=X', 'RUB=X']


# tickers = ['EURUSD=X']

def main():
    session = requests_cache.CachedSession('data/yfinance.cache')
    session.headers['User-agent'] = 'screener.py'
    params = []
    report = DataFrame()
    for ticker in TICKERS:
        yf_ticker = yf.Ticker(ticker, session=session)
        hist_1h = yf_ticker.history(period=PERIOD, interval=INTERVAL)
        ohlc_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}

        # Merging 1h into 4h dataframe
        data = hist_1h.resample('240T').apply(ohlc_dict).dropna(how='any')
        data['Date'] = data.index

        args = {
            'ticker': ticker,
            'data': data
        }
        params.append(args)

    if POOL <= 1:
        for param in params:
            result = worker(param)
            if result is not None:
                report = report.append(result)
    else:
        with Pool(POOL) as p:
            # Running in parallel
            result = p.map(worker, iter(params))
            if result is not None:
                report = report.append(result)
            p.close()
            p.join()


    print(report)


def worker(params: {}) -> {}:
    data = params['data']
    ticker = params['ticker']

    wa = WaveAnalyzer(df=data, verbose=False)
    wave_options_impulse = WaveOptionsGenerator5(up_to=WAVE_UP_TO)

    impulse = Impulse('impulse')
    leading_diagonal = LeadingDiagonal('leading diagonal')
    rules_to_check = [impulse, leading_diagonal]
    idx_start = np.argmin(np.array(list(data['Low'])))

    print(f'Start at idx: {idx_start}')
    print(f'will run up to {wave_options_impulse.number / 1e6}M combinations.')

    # set up a set to store already found wave counts
    # it can be the case, that 2 WaveOptions lead to the same WavePattern.
    # This can be seen in a chart, where for example we try to skip more maxima as there are. In such a case
    # e.g. [1,2,3,4,5] and [1,2,3,4,10] will lead to the same WavePattern (has same sub-wave structure, same begin / end,
    # same high / low etc.
    # If we find the same WavePattern, we skip and do not plot it

    wavepatterns_up = set()

    # loop over all combinations of wave options [i,j,k,l,m] for impulsive waves sorted from small, e.g.  [0,1,...] to
    # large e.g. [3,2, ...]
    results = DataFrame()
    for new_option_impulse in wave_options_impulse.options_sorted:

        waves_up = wa.find_impulsive_wave(idx_start=idx_start, wave_config=new_option_impulse.values)

        if waves_up:
            wavepattern_up = WavePattern(waves_up, verbose=True)

            for rule in rules_to_check:

                if wavepattern_up.check_rule(rule):
                    if wavepattern_up in wavepatterns_up:
                        continue
                    else:
                        wavepatterns_up.add(wavepattern_up)
                        print(f'{rule.name} found: {new_option_impulse.values}')
                        result = {
                            'ticker': ticker,
                            'rule': rule.name,
                            'new_option_impulse': new_option_impulse.values
                        }
                        plot_pattern(df=data, wave_pattern=wavepattern_up,
                                     title=ticker + ': ' + str(new_option_impulse))
                        sleep(1)
                        results = results.append(result, ignore_index=True)
    return results


if __name__ == '__main__':
    main()
    pass
