import pandas as pd
import matplotlib.pyplot as plt
import sys
sys.path.append("../")
from model import Kronos, KronosTokenizer, KronosPredictor


def plot_prediction(kline_df, pred_df):
    pred_df.index = kline_df.index[-pred_df.shape[0]:]
    sr_close = kline_df['close']
    sr_pred_close = pred_df['close']
    sr_close.name = 'Ground Truth'
    sr_pred_close.name = "Prediction"

    sr_volume = kline_df['volume']
    sr_pred_volume = pred_df['volume']
    sr_volume.name = 'Ground Truth'
    sr_pred_volume.name = "Prediction"

    close_df = pd.concat([sr_close, sr_pred_close], axis=1)
    volume_df = pd.concat([sr_volume, sr_pred_volume], axis=1)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)

    ax1.plot(close_df['Ground Truth'], label='Ground Truth', color='blue', linewidth=1.5)
    ax1.plot(close_df['Prediction'], label='Prediction', color='red', linewidth=1.5)
    ax1.set_ylabel('Close Price', fontsize=14)
    ax1.legend(loc='lower left', fontsize=12)
    ax1.grid(True)

    ax2.plot(volume_df['Ground Truth'], label='Ground Truth', color='blue', linewidth=1.5)
    ax2.plot(volume_df['Prediction'], label='Prediction', color='red', linewidth=1.5)
    ax2.set_ylabel('Volume', fontsize=14)
    ax2.legend(loc='upper left', fontsize=12)
    ax2.grid(True)

    plt.tight_layout()
    plt.show()


# 1. Load Model and Tokenizer
tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
model = Kronos.from_pretrained("/Users/yingzhang/Documents/dev/Kronos/Kronos-base")

# 2. Instantiate Predictor
predictor = KronosPredictor(model, tokenizer, device="mps", max_context=512)

# 3. Prepare Data
df = pd.read_csv("./data/XSHG_5min_600977.csv")
df['timestamps'] = pd.to_datetime(df['timestamps'])

lookback = 400
pred_len = 120

dfs = []
xtsp = []
ytsp = []
for i in range(5):
    idf = df.loc[(i*400):(i*400+lookback-1), ['open', 'high', 'low', 'close', 'volume', 'amount']]
    i_x_timestamp = df.loc[(i*400):(i*400+lookback-1), 'timestamps']
    i_y_timestamp = df.loc[(i*400+lookback):(i*400+lookback+pred_len-1), 'timestamps']

    dfs.append(idf)
    xtsp.append(i_x_timestamp)
    ytsp.append(i_y_timestamp)

pred_df = predictor.predict_batch(
    df_list=dfs,
    x_timestamp_list=xtsp,
    y_timestamp_list=ytsp,
    pred_len=pred_len,
)


# Combine historical and forecasted data for plotting
# pred_df is a list of DataFrames, align them to the same time points
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

colors = ['red', 'green', 'orange', 'purple', 'brown']

# Use the first batch's time range as reference
reference_start = 0
reference_end = lookback + pred_len - 1
reference_kline = df.loc[reference_start:reference_end]
reference_timestamps = df.loc[lookback:lookback+pred_len-1, 'timestamps']

# Plot reference ground truth
ax1.plot(reference_kline['close'], label='Ground Truth', color='blue', alpha=0.8, linewidth=2)
ax2.plot(reference_kline['volume'], label='Ground Truth', color='blue', alpha=0.8, linewidth=2)

# Plot all predictions aligned to the same time points
for i, single_pred_df in enumerate(pred_df):
    # Set the same time index for all predictions
    single_pred_df.index = reference_kline.index[-single_pred_df.shape[0]:]
    
    # Plot close price predictions
    ax1.plot(single_pred_df['close'], label=f'Prediction {i+1}', color=colors[i], linewidth=1.5, alpha=0.8)
    
    # Plot volume predictions
    ax2.plot(single_pred_df['volume'], label=f'Prediction {i+1}', color=colors[i], linewidth=1.5, alpha=0.8)

ax1.set_ylabel('Close Price', fontsize=14)
ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
ax1.grid(True)

ax2.set_ylabel('Volume', fontsize=14)
ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
ax2.grid(True)

plt.tight_layout()
plt.show()