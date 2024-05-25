from flask import Flask, jsonify, Response,request
from Common import ServerT as ST
import json
import datetime as dt
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
@app.route('/stockslist',methods = ['GET'])
def get_list():
    try:
        resp1 = Server.GetRuStocksList()
        data = resp1
        figis = {element['figi']:element for element in data if element.get('first1dayCandleDate') != None}
        resp2 = Server.GetLastPrice(list(figis.keys()))
        for i in resp2:
            figis[i]['price'] = resp2[i]
        return jsonify(figis)
    except Exception as ex: print("ex",ex)

@app.route('/stock/<uid>',methods = ['GET'])
def get_stock(uid):
    resp = Server.GetAssetFundametals(uid)
    resp2 = Server.GetAssetInfo(uid)
    start_time = (dt.date.today() - relativedelta(months=12)).strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = dt.date.today().strftime('%Y-%m-%dT%H:%M:%SZ')
    interval = 5
    resp3 = Server.GetCandles(resp2['instruments'][0]['figi'],start_time,end_time,interval)
    candles = Server.maininfoofcandles(resp3)
    resp["info"] = resp2["brand"]["info"]
    resp["name"]  = resp2["brand"]["name"]
    resp["sector"]  = resp2["brand"]["sector"]
    resp["candles"] = candles
    return jsonify(resp)

@app.route('/portfolio',methods = ['POST'])  
def get_portfolio():
    data = request.json
    date1 = data['start_time']
    date2 = data['end_time']
    interval = data['interval']
    figis = data['figis']
    candles = Server.GetStocksCandles(figis,date1,date2,interval)
    df = Server.GetMatrix(candles)
    df1 = df.dropna(axis=1)
    df2 = df1.pct_change()
    df2 = df2.drop(df.index[0])
    positive_profit = df2.mean().where(df2.mean() > 0).dropna().index
    df3 = df2[positive_profit]
    if data['portfolioType'] == 'minrisk':
        res = Server.Portfolio(df3)
    elif data['portfolioType'] == 'sharpe':
        r = data['rate']
        res = Server.PortfolioSharpe(df3,r)    
    else:
        r = data['rate']
        res = Server.PortfolioR(df3,r)
    return jsonify(res)

if __name__ == '__main__':
    
    Server = ST()
    app.run()
