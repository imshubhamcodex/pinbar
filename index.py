# pip install yfinance pandas matplotlib tabulate
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from tabulate import tabulate
import sys
import msvcrt
import time
import os

# Fetch historical hourly data for Nifty 50 using yfinance
while True:
    ticker = "^NSEI"
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=720)

    data = yf.download(ticker, start=start_date, end=end_date, interval="1h")

    def is_red_pinbar(open_price, high_price, low_price, close_price, trend_direction):
        total_range = high_price - low_price
        body = abs(open_price - close_price)
        upper_shadow = high_price - max(open_price, close_price)
        lower_shadow = min(open_price, close_price) - low_price

        if body / total_range < 0.3 and upper_shadow / total_range > 0.6 and lower_shadow / upper_shadow < 0.35 and trend_direction == 'downtrend' and total_range > 40:
            return True
        return False

    def is_green_pinbar(open_price, high_price, low_price, close_price, trend_direction):
        total_range = high_price - low_price
        body = abs(open_price - close_price)
        upper_shadow = high_price - max(open_price, close_price)
        lower_shadow = min(open_price, close_price) - low_price

        if body / total_range < 0.3 and lower_shadow / total_range > 0.6 and upper_shadow / lower_shadow < 0.35 and trend_direction == 'uptrend' and total_range > 40:
            return True
        return False

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

    # Simulate paper trading

    def get_input_with_timeout(prompt, default_value, timeout_sec):
        os.system('cls' if os.name == 'nt' else 'clear')
        sys.stdout.write(f"{prompt} (default: {default_value}): ")
        sys.stdout.flush()

        start_time = time.time()
        input_chars = []
        while True:
            if msvcrt.kbhit():  # Check if a key is pressed
                char = msvcrt.getche()  # Get the character
                if char == b'\r':  # Enter key is pressed
                    break
                input_chars.append(char.decode('utf-8'))
            elif time.time() - start_time > timeout_sec:  # Timeout reached
                break

        user_input = ''.join(input_chars).strip()
        return user_input if user_input else default_value

    # stop_loss_points = float(get_input_with_timeout(
    #     "Enter Stop Loss Points", 20, 10))
    # take_profit_points = float(get_input_with_timeout(
    #     "Enter Take Profit Points", 90, 10))
    open_plot = get_input_with_timeout("Open plot (y/n)", "n", 10)

    initial_profit_points = 0
    final_profit_points = initial_profit_points
    position_size = 1
    trade_serial_number = 0
    consecutive_loss = 0
    max_profit_points = 0
    prev_exit_timestamp = None
    prev_entry_timestamp = None
    trade_details = []
    trade_durations = []
    time_between_trades = []

    profit_points = [initial_profit_points]
    loss_drawdown = [0]
    profit_overshoot = [0]
    x_values = [0]

    for i in range(len(data)):
        if data.iloc[i]['IsRedPinbar'] or data.iloc[i]['IsGreenPinbar']:
            entry_price = data.iloc[i]['Open']
            entry_timestamp = data.index[i]

            # Check if the entry timestamp is greater than the previous exit timestamp
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

                
                if stop_loss_points < 5:
                    stop_loss_points = 5
                    
                if stop_loss_points < 12 and take_profit_points > 48:
                    take_profit_points = 24
                    
                if take_profit_points < 10 or stop_loss_points >= 35 or take_profit_points > 80:
                    continue

                stop_loss_price = entry_price + \
                    stop_loss_points if data.iloc[i]['IsRedPinbar'] else entry_price - \
                    stop_loss_points
                take_profit_price = entry_price - \
                    take_profit_points if data.iloc[i]['IsRedPinbar'] else entry_price + \
                    take_profit_points
                    
                trade_serial_number += 1
                
                next_index = 0
                for j in range(i + 1, len(data)):
                    next_row = data.iloc[j]
                    if trade_type == "Short":
                        if next_row['Low'] <= take_profit_price:
                            exit_price = take_profit_price
                            next_index = j
                            break
                        elif next_row['High'] >= stop_loss_price:
                            exit_price = stop_loss_price
                            next_index = j
                            break
                    else:
                        if next_row['High'] >= take_profit_price:
                            exit_price = take_profit_price
                            next_index = j
                            break
                        elif next_row['Low'] <= stop_loss_price:
                            exit_price = stop_loss_price
                            next_index = j
                            break

                if exit_price > 0:
                    exit_timestamp = data.index[next_index]
                    if trade_type == "Short":
                        profit = -1 * \
                            (exit_price - entry_price) * position_size
                    else:
                        profit = (exit_price - entry_price) * position_size

                    if profit < 0:
                        max_profit_points = 0
                        consecutive_loss += abs(profit)
                    else:
                        consecutive_loss = 0
                        max_profit_points += profit

                    trade_duration = exit_timestamp - entry_timestamp
                    trade_durations.append(trade_duration)

                    x_values.append(entry_timestamp)

                    final_profit_points += profit
                    entry_exit_difference = exit_price - entry_price
                    trade_duration = exit_timestamp - entry_timestamp
                    time_between_trades = entry_timestamp - \
                        prev_entry_timestamp if prev_entry_timestamp else pd.Timedelta(
                            0)
                    # print(f"Trade {trade_serial_number}: {trade_type} Trade - Entered at {entry_timestamp}, Exited at {exit_timestamp}, Entry-Exit Difference: {entry_exit_difference:.2f}, Profit: {profit:.2f}, Profit: {final_profit_points:.2f}")
                    # print(f"   Trade Duration: {trade_duration}, Time Between Trades: {time_between_trades}")

                    prev_exit_timestamp = exit_timestamp
                    prev_entry_timestamp = entry_timestamp
                else:
                    # print("No Profit No Loss")
                    exit_timestamp = "N/A"
                    exit_price = "N/A"
                    entry_exit_difference = "N/A"
                    profit = "N/A"
                    final_profit_points = "N/A"
                    trade_duration = "N/A"
                    time_between_trades = "N/A"
                    
                    
                trade_details.append([
                    trade_serial_number,
                    trade_type,
                    entry_timestamp,
                    exit_timestamp,
                    entry_price,
                    exit_price,
                    entry_exit_difference,
                    profit,
                    final_profit_points,
                    take_profit_points,
                    stop_loss_points,
                    trade_duration,
                    time_between_trades
                ])

                profit_points.append(final_profit_points)
                loss_drawdown.append(consecutive_loss)
                profit_overshoot.append(max_profit_points)

    # print(f"Initial Profit Points: {initial_profit_points:.2f}, Final Profit Points: {final_profit_points:.2f}")
    # print(f"Loss Drawdown: {total_consecutive_loss:.2f}")
    # print(f"Profit Overshoot: {max_profit_points:.2f}")

    first_trade_time = trade_details[0][2]
    last_trade_time = trade_details[-1][3]
    time_difference = last_trade_time - first_trade_time
    total_trade_duration = sum(trade_durations, pd.Timedelta(0))

    num_winning_trades = len(
        [trade for trade in trade_details if trade[7] > 0])
    num_losing_trades = len([trade for trade in trade_details if trade[7] < 0])
    win_to_loss_ratio = num_winning_trades / \
        (num_losing_trades +
         num_winning_trades) if num_losing_trades != 0 else num_winning_trades
    win_percentage = round(win_to_loss_ratio * 100, 2)

    total_trade_taken = len(trade_details)

    
    headers = ["Trade #", "Trade Type", "Entry Time", "Exit Time", "Entry Price", "Exit Price",
               "Entry-Exit", "Profit", "Cum. Profit", "TP", "SL", "Active For", "Time Between Trades"]
    with open("Trade_Details.txt", "w") as f:
        f.write(tabulate(trade_details, headers=headers, tablefmt="grid"))
    print("\nDetailed File Generated: Trade_Details.txt")

    print("\nTrade Overview Details:")
    time_frame = "1Hr"
    summary_data = [
        ["Trade taken on Time Frame", f"{time_frame}"],
        ["Maximum SL","35"],
        ["Minimum TP","10"],
        ["Total Trade Taken",
            f"{total_trade_taken} (Win:{num_winning_trades} Loss:{num_losing_trades})"],
        ["Final Profit Points", f"{final_profit_points:.2f}"],
        ["Win Percent:", win_percentage, "%"],
        ["Profit Factor",
            f"{round(take_profit_points / stop_loss_points, 2)}"],
        ["Active in Trade", f"{total_trade_duration}"],
        ["Time between Frist and Last Trade", f"{time_difference}"]
    ]
    print(tabulate(summary_data, headers=["Metric", "Value"], tablefmt="grid"))

    
    # Plotting code
    plt.figure(figsize=(12, 8))
    plt.plot(range(len(profit_points)), profit_points, label='Profit Points')
    plt.plot(range(len(loss_drawdown)), loss_drawdown, label='Loss Drawdown')
    plt.plot(range(len(profit_overshoot)),
             profit_overshoot, label='Profit Overshoot')
    plt.xlabel('Trade')
    plt.ylabel('Points')
    plt.title('Trade Metrics')
    plt.legend()
    plt.xticks(range(len(x_values)), x_values, rotation=90, fontsize=8)
    plt.grid(True)
    plt.tight_layout()

    if open_plot.lower() == 'y':
        plt.show()
    else:
        plt.close()

    latest_trade = trade_details[-1] if trade_details else None
    if latest_trade:
        print("\nLatest Trade:")
        latest_trade_headers = ["Trade #", "Trade Type", "Entry Time", "Exit Time",
                                "Entry Price", "Exit Price", "Profit", "Final Profit", "Time Ago"]
        now = datetime.now(latest_trade[2].tzinfo)
        time_ago = now - latest_trade[2]
        latest_trade_formatted = [latest_trade_headers, [latest_trade[0], latest_trade[1], latest_trade[2], latest_trade[3], round(
            latest_trade[4], 2), round(latest_trade[5], 2), round(latest_trade[7], 2), round(latest_trade[8], 2), str(time_ago)]]
        print(tabulate(latest_trade_formatted, tablefmt="grid"))


        print("\nMade with ","\033[91m♥\033[0m", " : https://github.com/imshubhamcodex/")
    # Repeat After 5Min
    time.sleep(5 * 60)
