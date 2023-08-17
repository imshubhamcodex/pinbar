import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Fetch historical hourly data for Nifty 50 using yfinance
ticker = "^NSEI"
end_date = datetime.today().date()
start_date = end_date - timedelta(days=720)

data = yf.download(ticker, start=start_date, end=end_date, interval="1h")

def is_red_pinbar(open_price, high_price, low_price, close_price, trend_direction):
    total_range = high_price - low_price
    body = abs(open_price - close_price)
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price
    
    if body / total_range < 0.2 and upper_shadow / total_range > 0.6 and lower_shadow / upper_shadow < 0.35 and trend_direction == 'downtrend' and total_range > 50:
        return True
    return False

def is_green_pinbar(open_price, high_price, low_price, close_price, trend_direction):
    total_range = high_price - low_price
    body = abs(open_price - close_price)
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price
    
    if body / total_range < 0.2 and lower_shadow / total_range > 0.6 and upper_shadow / lower_shadow < 0.35 and trend_direction == 'uptrend' and total_range > 50:
        return True
    return False

data['Direction'] = data['Close'].diff().apply(lambda x: 'uptrend' if x > 0 else 'downtrend')
data['IsRedPinbar'] = data.apply(lambda row: is_red_pinbar(row['Open'], row['High'], row['Low'], row['Close'], row['Direction']), axis=1)
data['IsGreenPinbar'] = data.apply(lambda row: is_green_pinbar(row['Open'], row['High'], row['Low'], row['Close'], row['Direction']), axis=1)

data['Range'] = data['High'] - data['Low']
data['Body'] = abs(data['Open'] - data['Close'])
data['Upper Shadow'] = data['High'] - data[['Open', 'Close']].max(axis=1)
data['Lower Shadow'] = data[['Open', 'Close']].min(axis=1) - data['Low']






# Simulate paper trading
initial_profit_points = 0
final_profit_points = initial_profit_points
position_size = 1  # Number of contracts per trade
stop_loss_points = 15
take_profit_points = 150
trade_serial_number = 0
consecutive_loss = 0
total_consecutive_loss = 0
max_profit_points = 0
prev_exit_timestamp = None
prev_entry_timestamp = None
trade_durations = []
time_between_trades = []

profit_points = [initial_profit_points]
loss_drawdown = [0]
profit_overshoot = [0]

for i in range(len(data)):
    if data.iloc[i]['IsRedPinbar'] or data.iloc[i]['IsGreenPinbar']:
        trade_serial_number += 1
        entry_price = data.iloc[i]['Open']
        entry_timestamp = data.index[i]
        exit_price = 0
        stop_loss_price = entry_price + stop_loss_points if data.iloc[i]['IsRedPinbar'] else entry_price - stop_loss_points
        take_profit_price = entry_price - take_profit_points if data.iloc[i]['IsRedPinbar'] else entry_price + take_profit_points
        trade_type = "Short" if data.iloc[i]['IsRedPinbar'] else "Long"
        
        for j in range(i + 1, len(data)):
            next_row = data.iloc[j]
            if trade_type == "Short":
                if next_row['High'] <= take_profit_price:
                    exit_price = take_profit_price
                    break
                elif next_row['Low'] >= stop_loss_price:
                    exit_price = stop_loss_price
                    break
            else:
                if next_row['Low'] >= take_profit_price:
                    exit_price = take_profit_price
                    break
                elif next_row['High'] <= stop_loss_price:
                    exit_price = stop_loss_price
                    break
        
        if exit_price > 0:
            exit_timestamp = data.index[j]
            if trade_type == "Short":
                profit = -1 * (exit_price - entry_price) * position_size
            else:
                profit = (exit_price - entry_price) * position_size
            
            if profit < 0:
                    consecutive_loss += abs(profit)
                    if consecutive_loss > total_consecutive_loss:
                        total_consecutive_loss = consecutive_loss
            else:
                consecutive_loss = 0

            if final_profit_points > max_profit_points:
                max_profit_points = final_profit_points 

            final_profit_points += profit
            entry_exit_difference = exit_price - entry_price
            
            trade_duration = exit_timestamp - entry_timestamp
            trade_durations.append(trade_duration)
            
            if prev_exit_timestamp:
                time_between_trade = entry_timestamp - prev_exit_timestamp
                time_between_trades.append(time_between_trade)
            
            prev_exit_timestamp = exit_timestamp
            prev_entry_timestamp = entry_timestamp
            
            print(f"Trade {trade_serial_number}: {trade_type} Trade - Entered at {entry_timestamp}, Exited at {exit_timestamp}, Entry-Exit Difference: {entry_exit_difference:.2f}, Profit: {profit:.2f}, Profit: {final_profit_points:.2f}")
        else:
            print(f"Trade {trade_serial_number}: {trade_type} Trade - Entered at {entry_timestamp}, No Profit")

        profit_points.append(final_profit_points)
        loss_drawdown.append(total_consecutive_loss)
        profit_overshoot.append(max_profit_points)

print(f"Initial Profit Points: {initial_profit_points:.2f}, Final Profit Points: {final_profit_points:.2f}")
print(f"Loss Drawdown: {total_consecutive_loss:.2f}")
print(f"Profit Overshoot: {max_profit_points:.2f}")

# Convert trade durations and time between trades to seconds
trade_durations_seconds = [duration.total_seconds() for duration in trade_durations]
time_between_trades_seconds = [duration.total_seconds() for duration in time_between_trades]

# Plotting code
plt.figure(figsize=(12, 8))
plt.plot(data.index[:len(profit_points)], profit_points, label='Profit Points')
plt.plot(data.index[:len(loss_drawdown)], loss_drawdown, label='Loss Drawdown')
plt.plot(data.index[:len(profit_overshoot)], profit_overshoot, label='Profit Overshoot')
plt.xlabel('Date')
plt.ylabel('Points')
plt.title('Trade Metrics')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()

# plt.figure(figsize=(12, 6))
# plt.plot(trade_durations_seconds, label='Trade Durations (seconds)')
# plt.plot(time_between_trades_seconds, label='Time Between Trades (seconds)')
# plt.xlabel('Trade Number')
# plt.ylabel('Duration / Time Difference (seconds)')
# plt.title('Trade Durations and Time Between Trades')
# plt.legend()
# plt.tight_layout()

plt.show()
