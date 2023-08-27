import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from tabulate import tabulate
import time
import json
import os
import requests
from datetime import datetime, time as datetime_time

# Ticker symbol for NSE Bank Index
ticker = "^NSEBANK"
time_interval = "15m"


# Fetch data
def fetch_data(ticker, time_interval):
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=59)
    data = yf.download(ticker, start=start_date, end=end_date, interval=time_interval)

    return data


# Calculate candlestick characteristics
def calculate_candlestick_characteristics(data):
    data['Open'] = pd.to_numeric(data['Open'])
    data['Close'] = pd.to_numeric(data['Close'])
    data['High'] = pd.to_numeric(data['High'])
    data['Low'] = pd.to_numeric(data['Low'])
    
    data['Body'] = abs(data['Open'] - data['Close'])
    data['Shadow'] = data[['High', 'Low']].max(axis=1) - data[['Open', 'Close']].min(axis=1)
    data['BodyRatio'] = data['Body'] / data['Shadow']
    data['Pattern'] = ""
    return data


# Pattern defination
def is_bullish_tweezer(data, index):
    if index < 1 or index >= len(data) - 1:
        return False
    
    if (
        data.iloc[index - 1]['Close'] < data.iloc[index - 1]['Open'] and
        data.iloc[index]['Close'] > data.iloc[index]['Open'] and
        data.iloc[index]['Open'] <= data.iloc[index - 1]['Close'] and
        data.iloc[index]['Close'] >= data.iloc[index - 1]['Open'] and
        abs(data.iloc[index]['Close'] - data.iloc[index - 1]['Open']) <= 10 and
        abs(data.iloc[index]['Close'] - data.iloc[index]['Open']) <=75
    ):
        return True
    return False

def is_bearish_tweezer(data, index):
    if index < 1 or index >= len(data) - 1:
        return False
    
    if (
        data.iloc[index - 1]['Close'] > data.iloc[index - 1]['Open'] and
        data.iloc[index]['Close'] < data.iloc[index]['Open'] and
        data.iloc[index]['Open'] >= data.iloc[index - 1]['Close'] and
        data.iloc[index]['Close'] <= data.iloc[index - 1]['Open'] and
        abs(data.iloc[index]['Close'] - data.iloc[index - 1]['Open']) <= 10 and
        abs(data.iloc[index]['Close'] - data.iloc[index]['Open']) <= 75
    ):
        return True
    return False


# Detect patterns
def detect_patterns(data):
    pattern_results = []

    for i in range(0, len(data)):
        if is_bullish_tweezer(data, i):
            pattern_results.append((data.index[i], "Bullish Tweezer"))
            data.at[data.index[i], 'Pattern'] = "Bullish Tweezer"
        elif is_bearish_tweezer(data, i):
            pattern_results.append((data.index[i], "Bearish Tweezer"))
            data.at[data.index[i], 'Pattern'] = "Bearish Tweezer"
    return pattern_results, data


# Simulate trades
def simulate_trades(data, pattern_results):
    trades = []
    position = None
    
    up_check = "Bullish Tweezer"
    down_ckeck = "Bearish Tweezer"

    for i in range(len(pattern_results)):
        date, pattern = pattern_results[i]

        if pattern == up_check:
            entry_price = data.loc[date]['Close']
            stop_loss_price = entry_price - 45
            take_profit_price = entry_price + 70
            position = take_trade(stop_loss_price, take_profit_price, pattern, date, data, up_check, down_ckeck)

        elif pattern == down_ckeck:
            entry_price = data.loc[date]['Close']  
            stop_loss_price = entry_price + 45
            take_profit_price = entry_price - 70
            position = take_trade(stop_loss_price, take_profit_price, pattern, date, data, up_check, down_ckeck)
       
        trades.append(position)

    return trades

# Execute trade
def take_trade(sl_price, tp_price, pattern, enter_date, entry_data, up_check, down_ckeck):
    entry_price = entry_data.loc[enter_date]['Close']
    profit = 0
    exit_date = None
    trade_type = None
    for date, next_price in entry_data.loc[enter_date:].iterrows():
        
        if date <= enter_date:
            continue
        
        if pattern == up_check:
            trade_type = "Long"
            if next_price['Low'] <= sl_price:           # exit in loss
                profit = -abs(entry_price - sl_price)
                exit_date = date
                break
            if next_price['High'] >= tp_price:          # exit in profit
                profit = abs(tp_price - entry_price)
                exit_date = date
                break
        elif pattern == down_ckeck:
            trade_type = "Short"
            if next_price['High'] >= sl_price:          # exit in loss
                profit = -abs(entry_price - sl_price)
                exit_date = date
                break
            if next_price['Low'] <= tp_price:           # exit in profit
                profit = abs(tp_price - entry_price)
                exit_date = date
                break

    exit_price = entry_price + profit

    position = {
        
        "trade_type" : trade_type,
        "entry_date": enter_date,
        "entry_price": entry_price,
        "profit": profit,
        "exit_date": exit_date,
        "exit_price": exit_price,
    }

    return position




# Fetch live data
def fetch_todays_data_from_ET():
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": "\"Not/A)Brand\";v=\"99\", \"Microsoft Edge\";v=\"115\", \"Chromium\";v=\"115\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.203",
        "Referer": "https://ettechcharts.indiatimes.com/ETLiveFeedChartRead/livefeeddata?scripcode=BANKNIFTY&exchangeid=50&datatype=intraday&filtertype=15MIN&tagId=&firstreceivedataid=&lastreceivedataid=&directions=all&callback=serviceHit.chartResultCallback&scripcodetype=index"
    }
    url = ("https://ettechcharts.indiatimes.com/ETLiveFeedChartRead/livefeeddata?scripcode=BANKNIFTY&exchangeid=50&datatype=intraday&filtertype=15MIN&tagId=&firstreceivedataid=&lastreceivedataid=&directions=all&callback=serviceHit.chartResultCallback&scripcodetype=index")
    
    res = res = requests.get(url,headers=headers)
    response_text = res.text
    start_index = response_text.find("(") + 1
    end_index = response_text.rfind(")")
    json_data = response_text[start_index:end_index]
        
    data = json.loads(json_data)
    quote_data = data['query']['results']['quote']
    df = pd.DataFrame(quote_data)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)

    current_date = pd.Timestamp.today()
    todays_data = df[df.index.date == current_date.date()]
    
    
    print("Fetched Sequence: ", len(todays_data))
    print(" ")
    return todays_data
    


def pattern_table(pattern_results):
    count_trade = 0
    pattern_table = []
    
    first_trade_date = 0
    last_trade_date = 0

    for date, pattern in pattern_results:
        count_trade += 1
        if count_trade == 1:
            first_trade_date = date
        last_trade_date = date
        pattern_table.append([count_trade, pattern, date])
        
    # print("Detected Patterns:")
    # pattern_headers = ["#", "Pattern", "Date"]
    # print(tabulate(pattern_table, headers=pattern_headers, tablefmt="grid"))
        
    return first_trade_date, last_trade_date



def calc_trades_params(trades):
    trade_table = []
    total_profit = 0
    win_trade = 0
    loss_trade = 0
    for i, trade in enumerate(trades):
        entry_date = trade["entry_date"]
        entry_price = round(trade["entry_price"], 2)
        exit_date = trade["exit_date"]
        exit_price = round(trade["exit_price"], 2)
        profit = trade["profit"]
        trade_type = trade["trade_type"]
        if profit > 0:
            win_trade += 1
        else:
            loss_trade += 1
        total_profit += profit
        trade_table.append([i + 1, trade_type, entry_date, entry_price, exit_date, exit_price, profit, total_profit])

    return trade_table, win_trade, loss_trade, total_profit
       



def print_metric(win_trade, loss_trade, total_profit, last_trade_date, first_trade_date, trade_table):
    
    win_percentage = 0
    
    if win_trade != 0 or loss_trade != 0:
        win_percentage = (win_trade * 100) / (win_trade + loss_trade)
    
    summary_data = [
        ["Trade on Time Frame", "15 Min."],
        ["Fixed SL","45"],
        ["Fixed TP","70"],
        ["Total Trade Taken",f"{win_trade + loss_trade} (Win:{win_trade} Loss:{loss_trade})"],
        ["Cumm. Profit Points", f"{total_profit:.2f}"],
        ["Win Percent:", round(win_percentage, 2), "%"],
        ["Time between Frist and Last Trade", f"{last_trade_date - first_trade_date}"]
    ]
    
    print(tabulate(summary_data, headers=["Metric", "Value"], tablefmt="grid"))
        
    trade_headers = ["#","Trade Type", "Entry Date", "Entry Price", "Exit Date", "Exit Price", "Profit", "Cumulative Profit"]    
    print("\nTrade Details: "+ ticker)
    print(tabulate(trade_table, headers=trade_headers, tablefmt="grid")) 


def backtest():
    data = fetch_data(ticker, time_interval)
    data_with_characteristics = calculate_candlestick_characteristics(data)
    pattern_results, data_with_pattern = detect_patterns(data_with_characteristics)
    first_trade_date, last_trade_date = pattern_table(pattern_results)
    data = data_with_pattern

    trades = simulate_trades(data, pattern_results)
    trade_table, win_trade, loss_trade, total_profit = calc_trades_params(trades)
    
    print_metric(win_trade, loss_trade, total_profit, last_trade_date, first_trade_date, trade_table)
    time.sleep(20)
    
    main()


# Main program
def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(" ")

    
    # Fetch Live data
    data = fetch_todays_data_from_ET()
    data = data[::-1]
    data_with_characteristics = calculate_candlestick_characteristics(data)
    pattern_results, data_with_pattern = detect_patterns(data_with_characteristics)
    first_trade_date, last_trade_date = pattern_table(pattern_results)
    data = data_with_pattern

 
    trades = simulate_trades(data, pattern_results)
    trade_table, win_trade, loss_trade, total_profit = calc_trades_params(trades)
    print("Live Trade Details: ----------")
    print_metric(win_trade, loss_trade, total_profit, last_trade_date, first_trade_date, trade_table)
    print(" ")
    print("\nMade with ","♥", " : https://github.com/imshubhamcodex/")
    
    
    
    
    
backtest()

# Looper
def check_and_call_function():
    current_time = datetime.now().time()
    
    for hour in range(9, 16):  # From 9 AM to 3 PM
        start_timei = datetime_time(hour, 15)
        end_timei = datetime_time(hour, 17)
        
        start_timej = datetime_time(hour, 0)
        end_timej = datetime_time(hour, 2)
        
        start_timek = datetime_time(hour, 30)
        end_timek = datetime_time(hour, 32)
        
        start_timel = datetime_time(hour, 45)
        end_timel = datetime_time(hour, 47)
                
        if start_timei <= current_time <= end_timei or start_timej <= current_time <= end_timej or start_timek <= current_time <= end_timek or start_timel <= current_time <= end_timel:
            main()
            print(" ")
            print("Re-Run at " + str(current_time))
            break

while True:
    check_and_call_function()
    time.sleep(30)  # 30-second wait



