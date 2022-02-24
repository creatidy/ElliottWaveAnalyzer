from time import sleep

import yfinance as yf
import requests_cache
import numpy as np
from pandas import DataFrame
from models.WavePattern import WavePattern
from models.WaveRules import Impulse, LeadingDiagonal
from models.WaveAnalyzer import WaveAnalyzer
from models.WaveOptions import WaveOptionsGeneratorWithRange
from models.helpers import plot_pattern
from models.WaveScore import WaveScore

from multiprocessing import Pool

POOL = 7  # 1 for single process; 2 or more for multiprocessing (limited debugging)
PERIOD = '1d'
INTERVAL = '5m'
VLT_WINDOW = 12
WAVE_UP_TO = 15
WITH_RANGE = 3  # with range +/- in relation to WAVE_UP_TO, e.g. for wave option==7 --> range: 2 -> 12
WAVE_PROPORTION_THRESHOLD = 0.7  # Proportion score minimum
WAVE_AGE_THRESHOLD = 0.7  # The last wave point should be later 80%
LIMIT = 3  # Number of the best charts to present
TICKERS = ['EURUSD=X', 'JPY=X', 'GBPUSD=X', 'AUDUSD=X', 'NZDUSD=X', 'EURJPY=X', 'GBPJPY=X', 'EURGBP=X', 'EURCAD=X',
           'EURSEK=X', 'EURCHF=X', 'EURHUF=X', 'EURJPY=X', 'CNY=X', 'HKD=X', 'SGD=X', 'INR=X', 'MXN=X', 'PHP=X',
           'IDR=X', 'THB=X', 'MYR=X', 'ZAR=X', 'RUB=X']
# TICKERS = ['EURJPY=X']


def main():
    session = requests_cache.CachedSession(cache_name='data/yfinance.cache', expire_after=300)
    session.headers['User-agent'] = 'screener.py'
    params = []
    report = DataFrame()
    for ticker in TICKERS:
        yf_ticker = yf.Ticker(ticker, session=session)
        data = yf_ticker.history(period=PERIOD, interval=INTERVAL)

        # Merging 1h into 4h dataframe
        # ohlc_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}
        # data = hist_1h.resample('240T').apply(ohlc_dict).dropna(how='any')

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

def find_minimums(data: DataFrame):
    '''
    Finds local minimal values
    '''

    data['Lowest_Start'] = data['Low'].rolling(window=VLT_WINDOW, min_periods=VLT_WINDOW).min()
    data['Minimum_Start'] = data['Low'] == data['Lowest_Start']
    # Reverse datafreame
    data = data.iloc[::-1]
    data.loc[:, 'Lowest_End'] = data['Low'].rolling(window=VLT_WINDOW, min_periods=VLT_WINDOW).min()
    data.loc[:, 'Minimum_End'] = data['Low'] == data['Lowest_End']
    # Reverse datafreame
    data = data.iloc[::-1]
    # Minimum should be from both sides
    data['Minimum'] = np.logical_and(data['Minimum_Start'], data['Minimum_End'])
    # Remove unnecessary columns
    data = data.drop(['Lowest_Start', 'Minimum_Start', 'Lowest_End', 'Minimum_End'], axis=1)
    return data


def worker(params: {}) -> {}:
    data = params['data']
    ticker = params['ticker']

    data = find_minimums(data)

    wa = WaveAnalyzer(df=data, verbose=False)
    wave_options_impulse = WaveOptionsGeneratorWithRange(up_to=WAVE_UP_TO, with_range=WITH_RANGE)

    impulse = Impulse('impulse')
    leading_diagonal = LeadingDiagonal('leading diagonal')
    rules_to_check = [impulse, leading_diagonal]

    idx_start = np.argmin(np.array(list(data['Low'])))

    # print(f'Start at idx: {idx_start}')
    # print(f'will run up to {wave_options_impulse.number / 1e6}M combinations.')

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
    wavepatterns_up_to_plot = []
    for new_option_impulse in wave_options_impulse.options_sorted:
        all_waves_up = wa.find_5_impulsive_waves(wave_config=new_option_impulse.values)
        for waves_up in all_waves_up:
            wavepattern_up = WavePattern(waves_up, verbose=False)
            for rule in rules_to_check:
                if wavepattern_up.check_rule(rule):
                    if wavepattern_up in wavepatterns_up:
                        continue
                    else:
                        scoring = WaveScore(waves_up)
                        proportion_score = scoring.value()
                        age_score = wavepattern_up.idx_end / data.index.size
                        if proportion_score > WAVE_PROPORTION_THRESHOLD and age_score > WAVE_AGE_THRESHOLD:
                            to_check = []
                            if new_option_impulse.m is None and len(results) > 0:
                                to_check = [r for r in results['new_option_impulse'] if r[0] == new_option_impulse.i and \
                                            r[1] == new_option_impulse.j and \
                                            r[2] == new_option_impulse.k and \
                                            r[3] == new_option_impulse.l]
                            if len(to_check) == 0:
                                wavepatterns_up.add(wavepattern_up)
                                print(f'{rule.name} found: {new_option_impulse.values}')
                                result = {
                                    'ticker': ticker,
                                    'rule': rule.name,
                                    'new_option_impulse': new_option_impulse.values,
                                    'proportion_score': proportion_score,
                                    'data_size': data.index.size,
                                    'wave_end': wavepattern_up.idx_end,
                                    'age_score': age_score
                                }
                                results = results.append(result, ignore_index=True)
                                wavepatterns_up_to_plot.append({
                                    'wave_pattern': wavepattern_up,
                                    'result': result
                                })
    wavepatterns_up_to_plot = sorted(wavepatterns_up_to_plot, key=lambda w: w['result']['proportion_score'] * w['result']['age_score'], reverse=True)[:LIMIT]
    if len(wavepatterns_up_to_plot) > 0:
        plot_pattern(df=data, wave_patterns=wavepatterns_up_to_plot,
                     title=ticker + ' (period: ' + PERIOD + ', interval: ' + INTERVAL + '):<BR />')
        sleep(1)
    return results


if __name__ == '__main__':
    main()
    pass
