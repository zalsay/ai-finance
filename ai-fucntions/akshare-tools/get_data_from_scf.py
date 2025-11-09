from tencentserverless import scf 
from tencentserverless.scf import Client
from tencentserverless.exception import TencentServerlessSDKException
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
import json, datetime
import numpy as np
import pandas as pd

def scf0(event0, context0):
    scf = Client(***REMOVED***,***REMOVED***,region="ap-shanghai",token="")# 替换为您的 secret_id 和 secret_key
    try:
        params = {
            "type":event0["type"],
            "code":event0["code"],
            "start_date":event0["start_date"],
            "end_date":event0["end_date"],
        }
        data = scf.invoke(event0["functionName"],data=params,namespace='default') 
        return data
    except TencentServerlessSDKException as e:
        print (e)
    except TencentCloudSDKException as e:
        print (e)
    except Exception as e:
        print (e)
today = datetime.datetime.today()
years = 5
start = today - datetime.timedelta(days=365*years)
start = start.strftime("%Y%m%d")
code = "sh600439"
data = json.loads(scf0({"functionName":"get_financial_data","type":"stock","code":code,"start_date":start,"end_date":None},""))
if data["code"] > 0:
    df = pd.DataFrame(data["data"])
    df['change'] = df['close'].pct_change()  # 计算每日收盘价的百分比变化
    # 定义涨跌标签，这里我们简单地以涨跌阈值0.01%为例
    df['up_or_down'] = np.where(df['change'] > 0.0001, 1, np.where(df['change'] < -0.0001, -1, 0)) 
    # df.loc[df["Change"] >= 0.03,'up_above_3%'] = df["Change"]
    df.fillna(0)
    df.dropna(inplace=True)

print(df.head(1))