# pip install yfinance pandas matplotlib tabulate windows-curses
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from tabulate import tabulate
import sys
import msvcrt
import time
import os
import curses
import requests
import json

ticker = ""  
time_interval = "1h"


def main(stdscr, options, head):
    curses.curs_set(0)
    stdscr.clear()
    current_option = 0
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, head)
        for i, option in enumerate(options):
            if i == current_option:
                stdscr.addstr(i + 1, 0, "-> " + option, curses.A_REVERSE)
            else:
                stdscr.addstr(i + 1, 0, "   " + option)
        stdscr.refresh()
        key = stdscr.getch()
        if key == curses.KEY_DOWN and current_option < len(options) - 1:
            current_option += 1
        elif key == curses.KEY_UP and current_option > 0:
            current_option -= 1
        elif key == 10:  # Enter key
            return options[current_option]
        curses.flushinp()

if __name__ == "__main__":
    
    #menu_options = ["^NSEBANK", "^NSEI"]
    menu_options = ["^NSEBANK"]
    selected_option = curses.wrapper(main, menu_options, ":::::::::::::Choose Trading Asset::::::::::::")
    if selected_option is not None:
        ticker = selected_option
               
        
def get_input_with_timeout(prompt, default_value, timeout_sec):
    os.system('cls' if os.name == 'nt' else 'clear')
    sys.stdout.write(f"{prompt} (default: {default_value}): ")
    sys.stdout.flush()

    start_time = time.time()
    input_chars = []
    while True:
        if msvcrt.kbhit():  
            char = msvcrt.getche()
            if char == b'\r': 
                break
            input_chars.append(char.decode('utf-8'))
        elif time.time() - start_time > timeout_sec:
            break

    user_input = ''.join(input_chars).strip()
    return user_input if user_input else default_value



def fetch_data(ticker, time_interval):
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=720)
    data = yf.download(ticker, start=start_date, end=end_date, interval=time_interval)
    return data



def is_red_pinbar(open_price, high_price, low_price, close_price, trend_direction):
    total_range = high_price - low_price
    if total_range == 0:
        return False
    
    body = abs(open_price - close_price)
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price

    if body / total_range < 0.3 and upper_shadow / total_range > 0.6 and lower_shadow / upper_shadow < 0.35 and total_range > 40:
        return True
    return False



def is_green_pinbar(open_price, high_price, low_price, close_price, trend_direction):
    total_range = high_price - low_price
    if total_range == 0:
        return False
    
    body = abs(open_price - close_price)
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price

    if body / total_range < 0.3 and lower_shadow / total_range > 0.6 and upper_shadow / lower_shadow < 0.35 and total_range > 40:
        return True
    return False



def simulate_trade(data):
    position_size = 1
    final_profit_points = 0
    trade_serial_number = 0
    consecutive_loss = 0
    max_profit_points = 0
    
    prev_exit_timestamp = None
    prev_entry_timestamp = None
    
    trade_details = []
    profit_points = [0]
    loss_drawdown = [0]
    profit_overshoot = [0]
    traded_timestamp = [0]
    
    for i in range(len(data)):
        if data.iloc[i]['IsRedPinbar'] or data.iloc[i]['IsGreenPinbar']:
            entry_price = data.iloc[i]['Close']
            entry_timestamp = data.index[i]
            
            if prev_exit_timestamp is None or entry_timestamp > prev_exit_timestamp:
                trade_type = "Short" if data.iloc[i]['IsRedPinbar'] else "Long"
        
                exit_price = 0
                inv_loss_factor = 1.8
                earn_factor = 0.4

                if trade_type == "Short":
                    stop_loss_points = abs((
                        data.iloc[i]['Low'] - entry_price)/inv_loss_factor)
                    take_profit_points = abs((
                        entry_price - data.iloc[i]['High'])*earn_factor)
                else:
                    stop_loss_points = abs((
                        entry_price - data.iloc[i]['High'])/inv_loss_factor)
                    take_profit_points = abs((
                        data.iloc[i]['Low'] - entry_price)*earn_factor)
                
                
                if ticker == "^NSEBANK":
                    stop_loss_points = 40      #Fixed it
                    if take_profit_points < 30:
                        continue
                else:
                    stop_loss_points = 25
                    if take_profit_points < 10:
                        continue

                stop_loss_price = entry_price + stop_loss_points if data.iloc[i]['IsRedPinbar'] else entry_price - stop_loss_points
                take_profit_price = entry_price - take_profit_points if data.iloc[i]['IsRedPinbar'] else entry_price + take_profit_points
                    
                trade_serial_number += 1
                exit_trade_index = 0
                
                trail_sl = False
                trail_tp = False
                
                for j in range(i + 1, len(data)):
                    next_row = data.iloc[j]
                    if trade_type == "Short":
                        if next_row['Low'] <= take_profit_price:
                            if take_profit_points < 40  or (take_profit_points >= 55 and take_profit_points < 90) :
                                exit_price = take_profit_price - 10
                                trail_tp = True
                            else:
                                exit_price = take_profit_price
                                trail_tp = False
                            exit_trade_index = j
                            break
                        elif next_row['High'] >= stop_loss_price:
                            exit_price = stop_loss_price
                            exit_trade_index = j
                            break
                    else:
                        if next_row['High'] >= take_profit_price:
                            if take_profit_points < 40  or (take_profit_points >= 55 and take_profit_points < 70) :
                                exit_price = take_profit_price + 10
                                trail_tp = True
                            else: 
                                exit_price = take_profit_price
                                trail_tp = False
                            exit_trade_index = j
                            break
                        elif next_row['Low'] <= stop_loss_price:
                            exit_price = stop_loss_price  
                            exit_trade_index = j
                            break

                if exit_price > 0:
                    exit_timestamp = data.index[exit_trade_index]
                    if trade_type == "Short":
                        profit = -1 * (exit_price - entry_price) * position_size
                    else:
                        profit = (exit_price - entry_price) * position_size

                    if profit < 0:
                        max_profit_points = 0
                        consecutive_loss += abs(profit)
                    else:
                        consecutive_loss = 0
                        max_profit_points += profit

                    trade_duration = exit_timestamp - entry_timestamp
                    traded_timestamp.append(entry_timestamp)
                    final_profit_points += profit
                    entry_exit_difference = exit_price - entry_price
                    time_between_trades = entry_timestamp - prev_entry_timestamp if prev_entry_timestamp else pd.Timedelta(0)
                    prev_exit_timestamp = exit_timestamp
                    prev_entry_timestamp = entry_timestamp
                else:
                    exit_timestamp = pd.NaT
                    exit_price = 0
                    entry_exit_difference = 0
                    profit = 0
                    trade_duration = pd.NaT
                    time_between_trades = pd.NaT
                    
                    
                take_profit_str = f"{round(take_profit_points,2)}(+10)" if trail_tp else f"{round(take_profit_points,2)}(+0)"
                stop_loss_str = f"{round(stop_loss_points,2)}(+0)" if trail_sl else f"{round(stop_loss_points,2)}(+0)"
                trade_details.append([
                    trade_serial_number,
                    trade_type,
                    entry_timestamp,
                    exit_timestamp,
                    round(entry_price,2),
                    round(exit_price,2),
                    entry_exit_difference,
                    profit,
                    final_profit_points,
                    take_profit_str,
                    stop_loss_str,
                    trade_duration,
                    time_between_trades,
                ])

                profit_points.append(final_profit_points)
                loss_drawdown.append(consecutive_loss)
                profit_overshoot.append(max_profit_points)
    return trade_details, profit_points, loss_drawdown, profit_overshoot, traded_timestamp



def result_params_calc(trade_details) :
    first_trade_time = trade_details[0][2]
    last_trade_time = trade_details[-1][3]
    time_difference = last_trade_time - first_trade_time

    num_winning_trades = len(
        [trade for trade in trade_details if trade[7] > 0])
    num_losing_trades = len([trade for trade in trade_details if trade[7] < 0])
    win_to_loss_ratio = num_winning_trades / (num_losing_trades + num_winning_trades) if num_losing_trades != 0 else num_winning_trades
    win_percentage = round(win_to_loss_ratio * 100, 2)
    total_trade_taken = len(trade_details)
    return total_trade_taken, num_winning_trades, num_losing_trades, win_percentage, time_difference



def print_txt(filename, data_to_print):
    headers = ["Trade #", "Trade Type", "Entry Time", "Exit Time", "Entry Price", "Exit Price", "Entry-Exit", "Profit", "Cum. Profit", "TP(+Trail)", "SL(+Trail)", "Active For", "Time Between Trades"]
    with open(filename + ".txt", "w") as f:
        f.write(tabulate(data_to_print, headers = headers, tablefmt="grid"))
    print(" ")
    print("\nFile Generated: "+ filename + ".txt")



def print_todays_trade(trades):
    print("Latest Trades:")
    print("Today's Open Postion:")
    
    for i in range(len(trades)):
        latest_trade = trades[i]
        
        now = datetime.now(latest_trade[2].tzinfo)
        time_ago = now - latest_trade[2]
        
        if str(latest_trade[3]) == "NaT":
            latest_trade_headers = ["Trade #", "Trade Type", "Entry Time", "Exit Time", "Entry Price", "Exit Price", "TP(+Trail)", "SL(+Trail)", "Time Ago"]
            latest_trade_formatted = [latest_trade_headers, [latest_trade[0], latest_trade[1], latest_trade[2], latest_trade[3],latest_trade[4], latest_trade[5], latest_trade[9], latest_trade[10], str(time_ago)]]
            print(tabulate(latest_trade_formatted, tablefmt="grid"))
            print(" ")
           
    print(" ")
    print("Today's Closed Postion:")   
    for i in range(len(trades)):
        latest_trade = trades[i]
        
        now = datetime.now(latest_trade[2].tzinfo)
        time_ago = now - latest_trade[2]
        
        if str(latest_trade[3]) != "NaT":
            headers = ["Trade #", "Trade Type", "Entry Time", "Exit Time", "Entry Price", "Exit Price", "Profit", "TP(+Trail)", "SL(+Trail)", "Active For"]
            headers_formatted = [headers, [latest_trade[0], latest_trade[1], latest_trade[2], latest_trade[3],latest_trade[4], latest_trade[5], latest_trade[7], latest_trade[8],latest_trade[9], latest_trade[10]]]
            print(tabulate(headers_formatted, tablefmt="grid"))
            print(" ")
        
    
    
def date_to_timestamp(date):
    time_tuple = date.timetuple()
    timestamp = round(time.mktime(time_tuple))
    return timestamp



def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(timestamp)



def data_adjusted_to_one_hr(data_df, filter_day):
    
    filtered_day_data = data_df[data_df['Date'].dt.date == filter_day]
    filtered_day_data.set_index('Date', inplace=True)
    resampled_data = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

    if filtered_day_data.empty:
        return resampled_data
    
    for hour in range(9, 16):
        start_time = filtered_day_data.index[0].replace(hour=hour, minute=15)
        end_time = filtered_day_data.index[0].replace(hour=hour, minute=15) + timedelta(hours=1)
        hour_data = filtered_day_data.between_time(start_time.time(), end_time.time())
        
        if not hour_data.empty:
            resampled_data.loc[start_time] = [
                hour_data['Open'].iloc[0],
                hour_data['High'].max(),
                hour_data['Low'].min(),
                hour_data['Close'].iloc[-1],
                hour_data['Volume'].sum()
            ] 
    
    resampled_data = resampled_data.rename_axis('Datetime').reset_index() 
    return resampled_data



def adjust_data():
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    start_timestamp = date_to_timestamp(today)
    end_timestamp = date_to_timestamp(tomorrow)
        
    money_control_url = "https://priceapi.moneycontrol.com//techCharts/indianMarket/index/history?symbol=in%3Bnbx&resolution=15&from=" + str(start_timestamp) + "&to=" + str(end_timestamp) + "&countback=234&currencyCode=INR"
    headers = {
        "Cookie": "MC_PPID_LOGIC=normaluser6667461145079466mcids; _gcl_au=1.1.257365712.1692387851; _gid=GA1.2.713682474.1692387853; _cb=Com7GORN8-NZSBMe; WZRK_G=1c78bf5e96fd496295f57ea236ce2122; _cc_id=ffe51bfcbbbb6514f53a347582d6e56e; panoramaId_expiry=1692474289980; _hjSessionUser_3470143=eyJpZCI6IjlhNTJjNjQ3LTdhOTQtNWE2My1iN2RiLTU0YWUyNzkyNjBiMyIsImNyZWF0ZWQiOjE2OTIzODc4NjA5NjksImV4aXN0aW5nIjp0cnVlfQ==; PHPSESSID=8i2fj7mcped3pvem5a2kehro06; __utma=129839248.2034491628.1692387853.1692392018.1692392018.1; __utmc=129839248; __utmz=129839248.1692392018.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); _ga_4S48PBY299=GS1.1.1692425530.3.0.1692425530.0.0.0; _ga=GA1.1.2034491628.1692387853; _chartbeat2=.1692387855383.1692425531727.1.CIZ_WG0dRpHCGUi9RgQfDABM84-L.1; _cb_svref=https%3A%2F%2Fwww.google.com%2F; _hjIncludedInSessionSample_3470143=0; _hjSession_3470143=eyJpZCI6ImEyNzJmNTFkLWUxODEtNDk3Ni1iZTQwLWUzMDVmMjFmNGEzZSIsImNyZWF0ZWQiOjE2OTI0MjU1MzI4NTAsImluU2FtcGxlIjpmYWxzZX0=; FCNEC=%5B%5B%22AKsRol8q-cLq2qkwwnTjdahbNbG5lKKtkco-TtklgxqY5Q608OQQiKWqSI5tPHJtdlEF-_sgGGLGRzQhFt7q-iUvzAE5G8kNOQAssSMO4DXdOc4mH1teCThoFmX2IUUkOn3Mp62LG6NXwn7bSevOvu45G5wcigSAZA%3D%3D%22%5D%2Cnull%2C%5B%5D%5D; _ga_1ERSHJWQZ9=GS1.1.1692425551.3.0.1692425551.0.0.0; WZRK_S_86Z-5ZR-RK6Z=%7B%22p%22%3A1%2C%22s%22%3A1692425534%2C%22t%22%3A1692425652%7D; __gads=ID=d320eb17fa7180a8-22c2dcfcede20002:T=1692387887:RT=1692425854:S=ALNI_MbgMED0m7OrgGvRnIvmsChkneORYg; __gpi=UID=00000c2eec922b16:T=1692387887:RT=1692425854:S=ALNI_MaLpAs4dMry-7NDzplBLvdw-lhRqw",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    response = requests.get(money_control_url,headers=headers)
    
    try:
        response_data = response.json()
    except Exception as e:
        print("JSON Decode Error:", e)
        return None
    
    date = []
    for dt in response_data['t']:
        date.append({'Date': timestamp_to_date(dt)})
    date_df = pd.DataFrame(date)

    other_data_df = pd.DataFrame({
        'Open': response_data['o'],
        'High': response_data['h'],
        'Low': response_data['l'],
        'Close': response_data['c'],
        'Volume': response_data['v']
    })
    
    other_data_df = pd.concat([date_df, other_data_df], axis=1)

    data_df = pd.DataFrame(other_data_df)
    data_df['Date'] = pd.to_datetime(data_df['Date'])

    #today_date = (datetime.now() - timedelta(days=1)).date() # TESTING ON 1 DAY BACK
    today_date = datetime.now().date()
    todays_data = data_adjusted_to_one_hr(data_df, today_date)
    return todays_data



def fetch_todays_data():
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    start_timestamp = date_to_timestamp(today)
    end_timestamp = date_to_timestamp(tomorrow)
        
    money_control_url = "https://priceapi.moneycontrol.com//techCharts/indianMarket/index/history?symbol=in%3Bnbx&resolution=60&from=" + str(start_timestamp) + "&to=" + str(end_timestamp) + "&countback=234&currencyCode=INR"
    headers = {
        "Cookie": "MC_PPID_LOGIC=normaluser6667461145079466mcids; _gcl_au=1.1.257365712.1692387851; _gid=GA1.2.713682474.1692387853; _cb=Com7GORN8-NZSBMe; WZRK_G=1c78bf5e96fd496295f57ea236ce2122; _cc_id=ffe51bfcbbbb6514f53a347582d6e56e; panoramaId_expiry=1692474289980; _hjSessionUser_3470143=eyJpZCI6IjlhNTJjNjQ3LTdhOTQtNWE2My1iN2RiLTU0YWUyNzkyNjBiMyIsImNyZWF0ZWQiOjE2OTIzODc4NjA5NjksImV4aXN0aW5nIjp0cnVlfQ==; PHPSESSID=8i2fj7mcped3pvem5a2kehro06; __utma=129839248.2034491628.1692387853.1692392018.1692392018.1; __utmc=129839248; __utmz=129839248.1692392018.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); _ga_4S48PBY299=GS1.1.1692425530.3.0.1692425530.0.0.0; _ga=GA1.1.2034491628.1692387853; _chartbeat2=.1692387855383.1692425531727.1.CIZ_WG0dRpHCGUi9RgQfDABM84-L.1; _cb_svref=https%3A%2F%2Fwww.google.com%2F; _hjIncludedInSessionSample_3470143=0; _hjSession_3470143=eyJpZCI6ImEyNzJmNTFkLWUxODEtNDk3Ni1iZTQwLWUzMDVmMjFmNGEzZSIsImNyZWF0ZWQiOjE2OTI0MjU1MzI4NTAsImluU2FtcGxlIjpmYWxzZX0=; FCNEC=%5B%5B%22AKsRol8q-cLq2qkwwnTjdahbNbG5lKKtkco-TtklgxqY5Q608OQQiKWqSI5tPHJtdlEF-_sgGGLGRzQhFt7q-iUvzAE5G8kNOQAssSMO4DXdOc4mH1teCThoFmX2IUUkOn3Mp62LG6NXwn7bSevOvu45G5wcigSAZA%3D%3D%22%5D%2Cnull%2C%5B%5D%5D; _ga_1ERSHJWQZ9=GS1.1.1692425551.3.0.1692425551.0.0.0; WZRK_S_86Z-5ZR-RK6Z=%7B%22p%22%3A1%2C%22s%22%3A1692425534%2C%22t%22%3A1692425652%7D; __gads=ID=d320eb17fa7180a8-22c2dcfcede20002:T=1692387887:RT=1692425854:S=ALNI_MbgMED0m7OrgGvRnIvmsChkneORYg; __gpi=UID=00000c2eec922b16:T=1692387887:RT=1692425854:S=ALNI_MaLpAs4dMry-7NDzplBLvdw-lhRqw",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    response = requests.get(money_control_url,headers=headers)
    
    try:
        response_data = response.json()
    except Exception as e:
        print("JSON Decode Error:", e)
        return None
    
    data_ajusted = False
    
    if response_data['s'] == "no_data" :
        data_ajusted = True
        todays_data = adjust_data()
        return todays_data, data_ajusted 
    else:
        date = []
        for dt in response_data['t']:
            date.append({'Date': timestamp_to_date(dt)})
        date_df = pd.DataFrame(date)

        other_data_df = pd.DataFrame({
            'Open': response_data['o'],
            'High': response_data['h'],
            'Low': response_data['l'],
            'Close': response_data['c'],
            'Volume': response_data['v']
        })
        
        other_data_df = pd.concat([date_df, other_data_df], axis=1)

        data_df = pd.DataFrame(other_data_df)
        data_df['Date'] = pd.to_datetime(data_df['Date'])
        
        #today_date = (datetime.now() - timedelta(days=1)).date() # TESTING ON 1 DAY BACK
        today_date = datetime.now().date()
        
        filtered_day_data = data_df[data_df['Date'].dt.date == today_date]
        filtered_day_data.set_index('Date', inplace=True)
        todays_data = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        return todays_data, data_ajusted



def fetch_todays_trade(data):
   
    #TESTING BY ADDING NEW DATA
    # new_rows_data1 = {'Open': 43810.148438, 'High': 43847.601562, 'Low': 43731.000000, 'Close': 43824.851562, 'Volume': 0}
    # # new_rows_data2 = {'Open': 43823.300781, 'High': 43934.699219, 'Low': 43810.750000, 'Close': 43913.449219, 'Volume': 0}
    
    # rows_to_replace1 = '2023-08-18 15:15:00'
    # # rows_to_replace2 = '2023-08-18 14:15:00'

    # data.loc[rows_to_replace1] = new_rows_data1
    # # data.loc[rows_to_replace2] = new_rows_data2
    
    data['Direction'] = data['Close'].diff().apply(lambda x: 'uptrend' if x > 0 else 'downtrend')
    data['IsRedPinbar'] = data.apply(lambda row: is_red_pinbar(row['Open'], row['High'], row['Low'], row['Close'], row['Direction']), axis=1)
    data['IsGreenPinbar'] = data.apply(lambda row: is_green_pinbar(row['Open'], row['High'], row['Low'], row['Close'], row['Direction']), axis=1)

    data['Range'] = data['High'] - data['Low']
    data['Body'] = abs(data['Open'] - data['Close'])
    data['Upper Shadow'] = data['High'] - data[['Open', 'Close']].max(axis=1)
    data['Lower Shadow'] = data[['Open', 'Close']].min(axis=1) - data['Low']
    
    trade_details, profit_points, loss_drawdown, profit_overshoot, traded_timestamp = simulate_trade(data)
    
    data['Datetime'] = data.index
    data['Date'] = data['Datetime'].dt.date
    data['Time'] = data['Datetime'].dt.time
    data.drop(columns=['Datetime'], inplace=True)
    data_fetch_date = str(data['Date'].iloc[-1]) + " " + str(data['Time'].iloc[-1]) 
    print("\nLast Refresh ------->  " + ticker + " [" + data_fetch_date + "]")   
    print(" ")
    return trade_details




def execution():
    data = fetch_data(ticker , time_interval)
    
    data['Direction'] = data['Close'].diff().apply(
        lambda x: 'uptrend' if x > 0 else 'downtrend')
    data['IsRedPinbar'] = data.apply(lambda row: is_red_pinbar(
        row['Open'], row['High'], row['Low'], row['Close'], row['Direction']), axis=1)
    data['IsGreenPinbar'] = data.apply(lambda row: is_green_pinbar(
        row['Open'], row['High'], row['Low'], row['Close'], row['Direction']), axis=1)

    data['Range'] = data['High'] - data['Low']
    data['Body'] = abs(data['Open'] - data['Close'])
    data['Upper Shadow'] = data['High'] - data[['Open', 'Close']].max(axis=1)
    data['Lower Shadow'] = data[['Open', 'Close']].min(axis=1) - data['Low']

    open_plot = get_input_with_timeout("Open P/L plot (y/n)", "n", 5)
    
    trade_details, profit_points, loss_drawdown, profit_overshoot, traded_timestamp = simulate_trade(data)
    
    total_trade_taken, num_winning_trades, num_losing_trades, win_percentage, time_difference = result_params_calc(trade_details)
    
    print_txt("Trade_Backtest_"+ ticker, trade_details)
    
    
    data['Datetime'] = data.index
    data['Date'] = data['Datetime'].dt.date
    data['Time'] = data['Datetime'].dt.time
    data.drop(columns=['Datetime'], inplace=True)
    data_fetch_date = str(data['Date'].iloc[-1]) + " " + str(data['Time'].iloc[-1]) 
        
    print("\nTrade Overview Details: " + ticker + " [" + data_fetch_date + "]")   
    summary_data = [
        ["Trade on Time Frame", "1Hr"],
        ["Fixed SL","40"],
        ["Minimum TP","30"],
        ["TP+ Offset","10"],
        ["Total Trade Taken",f"{total_trade_taken} (Win:{num_winning_trades} Loss:{num_losing_trades})"],
        ["Cumm. Profit Points", f"{trade_details[-1][8]:.2f}"],
        ["Win Percent:", win_percentage, "%"],
        ["Time between Frist and Last Trade", f"{time_difference}"]
    ]
    print(tabulate(summary_data, headers=["Metric", "Value"], tablefmt="grid"))

    todays_data, data_ajusted = fetch_todays_data()
    print(" ")
    if data_ajusted:
        print("1Hr API Request Failed -----> Adjusted Data Thrown")
    else:
        print("1Hr API Request Sucess -----> Live Data Thrown")
    
    if todays_data.empty:
        print(" ")
        print("NO DATA [DATE OR TIME NOK]", todays_data)
        if open_plot.lower() == 'y':
             plot_chart(profit_points, loss_drawdown, profit_overshoot, traded_timestamp, open_plot)
        return
    
    todays_data['Datetime'] = pd.to_datetime(todays_data['Datetime'])
    todays_data.set_index('Datetime', inplace=True)
    
    latest_trade = fetch_todays_trade(todays_data)
    print_todays_trade(latest_trade)
    
    if open_plot.lower() == 'y':
        plot_chart(profit_points, loss_drawdown, profit_overshoot, traded_timestamp, open_plot)
    else:   
        print("\nMade with ","\033[91m♥\033[0m", " : https://github.com/imshubhamcodex/")



def plot_chart(profit_points, loss_drawdown, profit_overshoot, traded_timestamp, open_plot):
    plt.figure(figsize=(12, 8))
    plt.plot(range(len(profit_points)), profit_points, label='Profit Points')
    plt.plot(range(len(loss_drawdown)), loss_drawdown, label='Loss Drawdown')
    plt.plot(range(len(profit_overshoot)),
             profit_overshoot, label='Profit Overshoot')
    plt.xlabel('Trade')
    plt.ylabel('Points')
    plt.title('Trade Metrics')
    plt.legend()
    plt.xticks(range(len(traded_timestamp)), traded_timestamp, rotation=90, fontsize=8)
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    print("\nMade with ","\033[91m♥\033[0m", " : https://github.com/imshubhamcodex/")



# Runner
def check_and_call_function():
    current_time = datetime.now().time()
    
    for hour in range(9, 16):  # From 9 AM to 3 PM
        start_time = time(hour, 15)
        end_time = time(hour, 20)
        
        if start_time <= current_time <= end_time:
            execution()
            break

# while True:
#     check_and_call_function()
#     time.sleep(90) 90sec
execution()
