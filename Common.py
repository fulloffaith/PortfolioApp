from requests import Request, Session
import datetime as dt
import pandas as pd
from scipy.optimize import Bounds, minimize
import numpy as np
import time
from dateutil.relativedelta import relativedelta

class ServerT:
    CandleIntervals = {'1min': 1, '5min': 2, '15min': 3,
                   'hour': 4, 'day': 5, 'week': 12, 'month': 13}
    def __init__(self):
        headers = {'Authorization': 'token'}
        s = Session()
        s.headers.update(headers)
        self.session = s

    def GetRuStocksList(self):
        url = 'https://sandbox-invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.InstrumentsService/Shares'
        response = self.session.post(
            url=url, json={"instrumentStatus": "INSTRUMENT_STATUS_UNSPECIFIED"})
        if response.status_code == 200:
            return [x for x in response.json()['instruments'] if x['currency'] == 'rub']
        else:
            return response.status_code
    
    def GetAssetFundametals(self,uid):  # get fundamental info about asset
        url = 'https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.InstrumentsService/GetAssetFundamentals'

        response = self.session.post(
            url=url, json={"assets": [uid]})
        if response.status_code == 200:
            return response.json()['fundamentals'][0]
        else:
            return response.status_code

    def MapNames(self,StocksList):  # StocksList - result of GetRuStocksList() figi:name
        d = {}
        for i in StocksList:
            figi = i['figi']
            name = i['name']
            d[figi] = name
        return d

    def GetStock(self,figi):
        url = 'https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.InstrumentsService/ShareBy'

        response = self.session.post(
            url=url, json={
            "idType": "INSTRUMENT_ID_TYPE_FIGI",
            "classCode": "string",
            "id": figi
        })
        if response.status_code == 200:
            return response.json()
        else:
            return response.status_code

    def GetCandles(self,figi, start_time, end_time, interval):
        url = 'https://sandbox-invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.MarketDataService/GetCandles'

        response = self.session.post(url=url, json={"figi": figi,
                                     "from": start_time,
                                     "to": end_time,
                                     "interval": interval,
                                     "instrumentId": figi})
        if response.status_code == 200:
            return response.json()['candles']
        else: response.status_code
        
    def GetLastPrice(self,figis):
        url = 'https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.MarketDataService/GetLastPrices'
        response = self.session.post(url=url, json={"instrumentId": figis} )
        if response.status_code == 200:
            respArray =  response.json()['lastPrices']
            prices = {}
            for element in respArray:
                units = element['price']['units']
                nano = element['price']['nano']
                prices[element['figi']] = self.UnitsPlusNano(units, nano)
            return prices
                
        else: pass
    def GetAssetInfo(self,assetuid):
        url = "https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.InstrumentsService/GetAssetBy";
        response = self.session.post(url=url, json={"id": assetuid} )
        if response.status_code == 200:
            return response.json()['asset']               
        else: response.status_code

    def GetStocksCandles(self,figis, start_time, end_time, interval):  # figis - list of figi
        data = {}
        for figi in figis:
            candles = self.GetCandles(figi, start_time, end_time, interval)

            data[figi] = self.maininfoofcandles(candles)

        return data


    def UnitsPlusNano(self,units, nano):  # unit: '200' nano : 100000 -> return 200.1
        degree = 9
        try:
            fraction = nano/(10**degree)
        except:
            fraction = 0
        return int(units) + float(fraction)


    def maininfoofcandles(self,candles):

        new_candles = []
        for i in candles:
            nano = i['close']['nano']
            units = i['close']['units']
            nums = self.UnitsPlusNano(units, nano)
            new_candles.append({'time': i['time'], 'value': nums})
        return new_candles


    def GetMatrix(self,data):
        max_len = 0
        max_figi = ''
        figi_list = []
        for key in data:
            length = len(data[key])
            figi_list.append(key)
            if length > max_len:
                max_len = length
                max_figi = key
        df = pd.DataFrame([], columns=figi_list, index=[date['time']
                      for date in data[max_figi]])
        for key in data:
            for i in data[key]:
                df[key].loc[i['time']] = i['value']
        return df


    def dominationStocks(self,df):
        stocks1 = list(zip(df.columns, df.mean(), df.std()))
        stocks2 = []
        for i in stocks1:
            for j in stocks1:
                if i != j and i[1] <= j[1] and i[2] >= j[2]:
                    stocks2.append(i)
                    break
        result = list(set(stocks1) ^ set(stocks2))
        df3 = df[[x[0] for x in result]]
        return df3


    def Portfolio(self,MatrixOfProfits):
        def func(x):
            return x @ S @ x.T


        def optimize():


            sum_cons = {'type': 'eq',
                 'fun': lambda x: x @ np.ones(len(df3.columns)) - 1
                }
            bnds = Bounds (np.zeros_like(x), np.ones(len(df3.columns)) * np.inf)

            res = minimize(func, x, method='SLSQP',
                   constraints=[ sum_cons], bounds=bnds)
            return res.x

        df3 = MatrixOfProfits
        labels = np.array(list(df3.columns))
        mu = np.array(df3.mean())
        S = df3.cov()
        x = np.ones(len(df3.columns)) / len(df3.columns)
        r = optimize()
        response = {"profit": r@mu, "variation": r @ S @ r.T,"rates":{labels[i]: round(r[i], 2) for i in range(len(r))}}
        return response

    def PortfolioR(self,MatrixOfProfits,r1):
        def func(x):
            return x @ S @ x.T


        def optimize(r1):
            mu_cons = {'type': 'eq',
                 'fun':  lambda x: mu @ x.T - r1
                }

            sum_cons = {'type': 'eq',
                 'fun': lambda x: x @ np.ones(len(df3.columns)) - 1
                }
            bnds = Bounds (np.zeros_like(x), np.ones(len(df3.columns)) * np.inf)

            res = minimize(func, x, method='trust-constr',
                   constraints=[mu_cons, sum_cons], bounds=bnds)
            return res.x

        df3 = MatrixOfProfits
        labels = np.array(list(df3.columns))
        mu = np.array(df3.mean())
        S = df3.cov()
        x = np.ones(len(df3.columns)) / len(df3.columns)
        r = optimize(r1)
        response = {"profit": r@mu, "variation": r @ S @ r.T,"rates":{labels[i]: round(r[i], 2) for i in range(len(r))}}
        return response

    def PortfolioSharpe(self,MatrixOfProfits,rf):
        def func(x):
            return -(mu @ x.T - rf)/(x @ S @ x.T)**0.5


        def optimize():


            sum_cons = {'type': 'eq',
                 'fun': lambda x: x @ np.ones(len(df3.columns)) - 1
                }
            bnds = Bounds (np.zeros_like(x), np.ones(len(df3.columns)) * np.inf)

            res = minimize(func, x, method='SLSQP',
                   constraints=[ sum_cons], bounds=bnds)
            return res.x
        df3 = MatrixOfProfits
        labels = np.array(list(df3.columns))
        mu = np.array(df3.mean())
        S = df3.cov()
        x = np.ones(len(df3.columns)) / len(df3.columns)
        r = optimize()
        response = {"profit": r@mu, "variation": r @ S @ r.T,"rates":{labels[i]: round(r[i], 2) for i in range(len(r))},"sharpe": func(r)}
        return response

if __name__ == "__main__":
    MyServer = ServerT()
    print(MyServer.GetRuStocksList()[0])
    print(MyServer.CandleIntervals)
