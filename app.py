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

def combineSeries(series1, series2, overrideStart=None, overrideEnd=None):
    """
    Combine two series in such a way that they can be plotted together.
    For series that have higher time resolution we apply a moving
    average.
    """
    start = max(series1.index[0], series2.index[0])
    if overrideStart is not None:
        start = overrideStart
    end = min(series1.index[-1], series2.index[-1])
    if overrideEnd is not None:
        end = overrideEnd
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
        #assert timestamps1 == timestamps2
        timestamps = timestamps1
    return timestamps, values1, values2

def plotSeries(seriesTuple, title, labels, colors):
    deltaMax = seriesTuple[0].index[1] - seriesTuple[0].index[0]
    start = seriesTuple[0].index[0]
    end = seriesTuple[0].index[-1]
    valMax = seriesTuple[0].values.max()
    idxValMax = 0
    idxDeltaMax = 0
    for i in range(len(seriesTuple)):
        series = seriesTuple[i]
        delta = series.index[1] - series.index[0]
        if delta > deltaMax:
            deltaMax = delta
            idxDeltaMax = i
        if series.values.max() > valMax: 
            valMax = series.values.max()
            idxValMax = i
        if series.index[0] > start:
            start = series.index[0]
        if series.index[-1] < end:
            end = series.index[-1]
    valuesList = []
    for i in range(len(seriesTuple)):
        timestamps, valuesDeltaMax, values = combineSeries(seriesTuple[idxDeltaMax], seriesTuple[i], overrideStart=start, overrideEnd=end)
        valuesList.append(values)
    chart = figure(x_axis_type="datetime", x_axis_label="Time", y_axis_label=labels[idxValMax], tools=TOOLS)
    chart.title = title
    for i in range(len(seriesTuple)):
        if i != idxValMax:
            series = seriesTuple[i]
            chart.extra_y_ranges["Y{0}".format(i)] = Range1d(start=series.values.min(), end=series.values.max())
            chart.add_layout(LinearAxis(y_range_name="Y{0}".format(i), axis_label=labels[i]), 'right')
    chart.line(timestamps, valuesList[idxValMax], legend=labels[idxValMax], color=colors[idxValMax])
    for i in range(len(seriesTuple)):
        if i != idxValMax:
            chart.line(timestamps, valuesList[i], legend=labels[i], y_range_name="Y{0}".format(i), color=colors[i])
    return chart

output_file('templates/index.html')
seriesFred = fetchSeriesFred('ISRATIO')
seriesQuandl = fetchSeriesQuandl('ODA', 'POILAPSP_INDEX', 'Value')
chart1 = plotSeries((seriesQuandl, seriesFred), "Inventory to Sales Ratio vs Blended Crude Oil", ("OIL", "ISRATIO"), ("blue", "red"))
seriesFred = fetchSeriesFred('CIVPART')
chart2 = plotSeries((seriesQuandl, seriesFred), "Labor Force Participation vs Blended Crude Oil", ("OIL", "LFPART"), ("blue", "red"))
seriesQuandl2 = fetchSeriesQuandl('YAHOO', 'INDEX_GSPC', 'Close')
seriesFred = fetchSeriesFred('WALCL')
chart3 = plotSeries((seriesFred, seriesQuandl2), "Fed Balance Sheet vs S&P 500", ("WALCL", "S&P 500"), ("blue", "red"))
chart3.legend.orientation = 'bottom_right'
seriesQuandl2 = fetchSeriesQuandl('GOOG', 'NYSE_SEA', 'Close')
seriesQuandl3 = fetchSeriesQuandl('LLOYDS', 'BDI', 'Index')
chart4 = plotSeries((seriesQuandl, seriesQuandl2), "Global Shipping Index SEA vs Blended Crude Oil", ("OIL", "SEA"), ("blue", "red"))
chart5 = plotSeries((seriesQuandl2, seriesQuandl3), "Global Shipping Index SEA vs Baltic Dry Index", ("SEA", "BDI"), ("blue", "red"))
save(vplot(chart1, chart2, chart3, chart4, chart5))

@app.route('/')
def main():
  return redirect('/index')

@app.route('/index')
def index():
  return render_template('index.html')

if __name__ == '__main__':
    app.run(port=33507)
