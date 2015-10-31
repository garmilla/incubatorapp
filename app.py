from collections import OrderedDict
import requests
import pandas as pd
from bokeh._legacy_charts import TimeSeries, show, output_file

fredUrl = 'https://api.stlouisfed.org/fred'
# FRED requires develpers to request an API key
apiKey = 'c265baefbe397fa81b57baabdb060c40'
urlSuffix = '&api_key={0}&file_type={1}'.format(apiKey, 'json')

def fetchFredSeries(seriesId):
    """
    Fetch a time series with series ID `seriesId` and 
    convert it to a Pandas series.
    """
    url = "{0}/series/observations?series_id={1}{2}".format(fredUrl, seriesId, urlSuffix)
    r = requests.get(url)
    observations = r.json()['observations']
    data = {}
    for obs in observations:
        data[obs['date']] = obs['value']
    series = pd.Series(data)
    series = series.astype(pd.np.float64)
    series.index = pd.to_datetime(series.index)
    return series

