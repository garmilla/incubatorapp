from collections import OrderedDict
import requests
import numpy as np
import pandas as pd
from bokeh.plotting import figure, show, output_file
from bokeh.models import LinearAxis, Range1d

urlFred = 'https://api.stlouisfed.org/fred'
apiKeyFred = 'c265baefbe397fa81b57baabdb060c40'
urlSuffixFred = '&api_key={0}&file_type=json'.format(apiKeyFred)

urlQuandl = 'https://www.quandl.com/api/v3/datasets'
apiKeyQuandl = '8_FFJtgQm-FWzKv6S--d'
urlSuffixQuandl = '?api_key={0}'.format(apiKeyQuandl)

TOOLS="resize,pan,wheel_zoom,box_zoom,reset,previewsave"

def fetchSeriesFred(seriesId):
    """
    Fetch a time series with series ID `seriesId` and 
    convert it to a Pandas series.
    """
    url = "{0}/series/observations?series_id={1}{2}".format(urlFred, seriesId, urlSuffixFred)
    r = requests.get(url)
    observations = r.json()['observations']
    data = {}
    for obs in observations:
        data[obs['date']] = obs['value']
    series = pd.Series(data)
    mask = series != u'.'
    series = series[mask]
    series = series.astype(pd.np.float64)
    series.index = pd.to_datetime(series.index)
    return series

def fetchSeriesQuandl(database, dataset, columnName):
    """
    Fetch a time series in database `database` and dataset `dataset`
    convert it to a Pandas series. This function uses the closing prices.
    """
    url = "{0}/{1}/{2}{3}".format(urlQuandl, database, dataset, urlSuffixQuandl) 
    r = requests.get(url)
    dataset = r.json()['dataset']['data']
    idx = r.json()['dataset']['column_names'].index(columnName)
    data = {}
    for element in dataset:
        data[element[0]] = element[idx]
    series = pd.Series(data)
    series = series.astype(pd.np.float64)
    series.index = pd.to_datetime(series.index)
    return series

def combineSeries(series1, series2):
    """
    Combine two series in such a way that they can be plotted together.
    For series that have higher time resolution we apply a moving
    average.
    """
    start = max(series1.index[0], series2.index[1])
    end = min(series1.index[-1], series2.index[-1])
    delta1 = series1.index[1] - series1.index[0]
    delta2 = series2.index[1] - series2.index[0]
    if delta1 < delta2:
        maskStart = series2.index > start
        maskEnd = series2.index < end
        mask = maskStart & maskEnd
        timestamps = series2[mask].index
        values2 = series2[mask].values[1:]
        values1 = np.zeros((len(timestamps)-1,))
        for i in range(len(timestamps)-1):
            maskStart = series1.index > timestamps[i]
            maskEnd = series1.index < timestamps[i+1]
            mask = maskStart & maskEnd
            values1[i] = np.mean(series1.values[mask])
    elif delta1 > delta2:
        maskStart = series1.index > start
        maskEnd = series1.index < end
        mask = maskStart & maskEnd
        timestamps = series1[mask].index
        values1 = series1[mask].values[1:]
        values2 = np.zeros((len(timestamps)-1,))
        for i in range(len(timestamps)-1):
            maskStart = series2.index > timestamps[i]
            maskEnd = series2.index < timestamps[i+1]
            mask = maskStart & maskEnd
            values2[i] = np.mean(series2.values[mask])
    else:
        maskStart = series1.index > start
        maskEnd = series1.index < end
        mask = maskStart & maskEnd
        timestamps1 = series1[mask].index
        values1 = series1[mask].values
        maskStart = series2.index > start
        maskEnd = series2.index < end
        mask = maskStart & maskEnd
        timestamps2 = series2[mask].index
        values2 = series2[mask].values
        assert timestamps1 == timestamps2
        timestamps = timestamps1
    return timestamps, values1, values2

if __name__ == '__main__':
    # Get FRED series for inventory to sales ratio
    seriesFred = fetchSeriesFred('ISRATIO')
    # Get WTI closing series from QUANDL
    seriesQuandl = fetchSeriesQuandl('BP', 'SPOT_CRUDE_OIL_PRICES', u'West Texas Intermediate')
    # Put the two series into a Bokeh timeseries
    timestamps, valuesFred, valuesQuandl = combineSeries(seriesFred, seriesQuandl)
    output_file("ISRatio_WTI.html")
    s1 = figure(x_axis_type="datetime", x_axis_label="Time", y_axis_label="WTI", tools=TOOLS)
    s1.title = "Inventory to Sales Ratio vs Crude Oil WTI"
    s1.extra_y_ranges = {"FRED": Range1d(start=1.2, end=1.5), "WTI": Range1d(start=0, end=60)}
    s1.add_layout(LinearAxis(y_range_name="FRED", axis_label='ISRATIO'), 'right')
    s1.line(timestamps, valuesFred, legend='ISRATIO', y_range_name="FRED", color='blue')
    s1.line(timestamps, valuesQuandl, legend='WTI', color='red')
    show(s1)
