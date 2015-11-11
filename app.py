from collections import OrderedDict
import requests
import numpy as np
import pandas as pd
from bokeh.plotting import figure, save, output_file, vplot
from bokeh.models import LinearAxis, Range1d

from flask import Flask, render_template, request, redirect

app = Flask(__name__)

urlFred = 'https://api.stlouisfed.org/fred'
apiKeyFred = 'c265baefbe397fa81b57baabdb060c40'
urlSuffixFred = '&api_key={0}&file_type=json'.format(apiKeyFred)

urlQuandl = 'https://www.quandl.com/api/v3/datasets'
apiKeyQuandl = '8_FFJtgQm-FWzKv6S--d'
urlSuffixQuandl = '.json?api_key={0}'.format(apiKeyQuandl)

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
    Fetch a time series in database `database`, dataset `dataset`, and column `columnName`.
    Convert it to a Pandas series.
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

def plotSeries(series1, series2, title, label1, label2, start2, end2):
    timestamps, values1, values2 = combineSeries(series1, series2)
    chart = figure(x_axis_type="datetime", x_axis_label="Time", y_axis_label=label1, tools=TOOLS)
    chart.title = title
    chart.extra_y_ranges = {"Y2": Range1d(start=start2, end=end2)}
    chart.add_layout(LinearAxis(y_range_name="Y2", axis_label=label2), 'right')
    chart.line(timestamps, values1, legend=label1, color='blue')
    chart.line(timestamps, values2, legend=label2, y_range_name="Y2", color='red')
    return chart

output_file('templates/index.html')
seriesFred = fetchSeriesFred('ISRATIO')
seriesQuandl = fetchSeriesQuandl('ODA', 'POILAPSP_INDEX', 'Value')
chart1 = plotSeries(seriesQuandl, seriesFred, "Inventory to Sales Ratio vs Blended Crude Oil", "OIL", "ISRATIO", 1.2, 1.55)
seriesFred = fetchSeriesFred('CIVPART')
chart2 = plotSeries(seriesQuandl, seriesFred, "Labor Force Participation vs Blended Crude Oil", "OIL", "LFPART", 58.0, 68.0)
seriesQuandl2 = fetchSeriesQuandl('YAHOO', 'INDEX_GSPC', 'Close')
seriesFred = fetchSeriesFred('WALCL')
chart3 = plotSeries(seriesFred, seriesQuandl2, "Fed Balance Sheet vs S&P 500", "WALCL", "S&P 500", 500.0, 2050.0)
chart3.legend.orientation = 'bottom_right'
seriesQuandl2 = fetchSeriesQuandl('GOOG', 'NYSE_SEA', 'Close')
#seriesQuandl3 = fetchSeriesQuandl('LLOYDS', 'BDI', 'Index')
chart4 = plotSeries(seriesQuandl, seriesQuandl2, "Global Shipping Index SEA vs Blended Crude Oil", "OIL", "SEA", 8.0, 30.0)
save(vplot(chart1, chart2, chart3, chart4))

@app.route('/')
def main():
  return redirect('/index')

@app.route('/index')
def index():
  return render_template('index.html')

if __name__ == '__main__':
    app.run(port=33507)
