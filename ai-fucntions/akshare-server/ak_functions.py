# -*- coding:utf-8 -*-

import time
import json
import pandas as pd
import requests
import demjson
import py_mini_racer
from cons import (
    zh_sina_a_stock_payload,
    zh_sina_a_stock_url,
    zh_sina_a_stock_count_url,
    zh_sina_a_stock_hist_url,
    hk_js_decode,
    zh_sina_a_stock_hfq_url,
    zh_sina_a_stock_qfq_url,
    zh_sina_a_stock_amount_url,
)
def hello():
    return "hello world"

def fund_open_fund_daily_em() -> pd.DataFrame:
    """
    东方财富网-天天基金网-基金数据-开放式基金净值
    http://fund.eastmoney.com/fund.html#os_0;isall_0;ft_;pt_1
    :return: 当前交易日的所有开放式基金净值数据
    :rtype: pandas.DataFrame
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
    }
    url = "http://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx"
    params = {
        "t": "1",
        "lx": "1",
        "letter": "",
        "gsid": "",
        "text": "",
        "sort": "zdf,desc",
        "page": "1,20000",
        "dt": "1580914040623",
        "atfc": "",
        "onlySale": "0",
    }
    res = requests.get(url, params=params, headers=headers)
    text_data = res.text
    data_json = demjson.decode(text_data.strip("var db="))
    temp_df = pd.DataFrame(data_json["datas"])
    show_day = data_json["showday"]
    temp_df.columns = [
        "基金代码",
        "基金简称",
        "-",
        f"{show_day[0]}-单位净值",
        f"{show_day[0]}-累计净值",
        f"{show_day[1]}-单位净值",
        f"{show_day[1]}-累计净值",
        "日增长值",
        "日增长率",
        "申购状态",
        "赎回状态",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "手续费",
        "-",
        "-",
        "-",
    ]
    data_df = temp_df[
        [
            "基金代码",
            "基金简称",
            f"{show_day[0]}-单位净值",
            f"{show_day[0]}-累计净值",
            f"{show_day[1]}-单位净值",
            f"{show_day[1]}-累计净值",
            "日增长值",
            "日增长率",
            "申购状态",
            "赎回状态",
            "手续费",
        ]
    ]
    data_df = data_df.loc[data_df['申购状态'] != '暂停申购']
    return data_df


def fund_open_fund_info_em(fund, indicator,return_type):
    """
    东方财富网-天天基金网-基金数据-开放式基金净值
    http://fund.eastmoney.com/fund.html#os_0;isall_0;ft_;pt_1
    :param fund: 基金代码; 可以通过调用 fund_open_fund_daily_em 获取所有开放式基金代码
    :type fund: str
    :param indicator: 需要获取的指标
    :type indicator: str
    :return: 指定基金指定指标的数据
    :rtype: pandas.DataFrame
    """
    # url = f"http://fundgz.1234567.com.cn/js/{fund}.js"  # 描述信息
    url = f"http://fund.eastmoney.com/pingzhongdata/{fund}.js"  # 各类数据都在里面
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
    }
    r = requests.get(url, headers=headers)
    data_text = r.text
    # 单位净值走势
    if indicator == "单位净值+累计净值":
        # 单位净值
        try:
            data_json1 = demjson.decode(
                data_text[
                    data_text.find("Data_netWorthTrend")
                    + 21 : data_text.find("Data_ACWorthTrend")
                    - 15
                ]
            )
        except:
            return pd.DataFrame()
        # 累计净值
        try:
            data_json2 = demjson.decode(
                data_text[
                    data_text.find("Data_ACWorthTrend")
                    + 20 : data_text.find("Data_grandTotal")
                    - 16
                ]
            )
        except:
            return pd.DataFrame()
        # 累计收益率走势
        data_json3 = demjson.decode(
            data_text[
                data_text.find("Data_grandTotal")
                + 18 : data_text.find("Data_rateInSimilarType")
                - 15
            ]
        )
        # 同类排名走势
        data_json4 = demjson.decode(
            data_text[
                data_text.find("Data_rateInSimilarType")
                + 25 : data_text.find("Data_rateInSimilarPersent")
                - 16
            ]
        )
        # 同类排名百分比
        data_json5 = demjson.decode(
            data_text[
                data_text.find("Data_rateInSimilarPersent")
                + 26 : data_text.find("Data_fluctuationScale")
                - 23
            ]
        )
        # 内容转换并格式化
        temp_df1 = pd.DataFrame(data_json1)       
        temp_df2 = pd.DataFrame(data_json2)

        # 解析JSON data3数据并转换为DataFrame
        df_list = []
        for item in data_json3:
            temp_df = pd.DataFrame(item['data'], columns=['x', 'value'])
            temp_df['name'] = item['name']
            df_list.append(temp_df)
        df = pd.concat(df_list).reset_index(drop=True)
        # 将数据透视（pivot）为时间戳作为索引，基金名称作为列名，净值作为值
        temp_df3 = df.pivot(index='x', columns='name', values='value')
        temp_df3.reset_index(inplace=True)
        temp_df4 = pd.DataFrame(data_json4)
        temp_df5 = pd.DataFrame(data_json5)
        temp_df1.columns = ["x", "unit_value","equity_return","unit_money"]
        temp_df2.columns = ["x", "cumulative_value"]
        temp_df3.columns = ["x", fund,"similar_type_average","HS300"]
        temp_df4.columns = ["x", "similar_type_rank_by_day","all_rank_by_day"]
        temp_df5.columns = ["x", "similar_type_persent"]
        temp_df = pd.merge(temp_df1,temp_df2,on=['x'],how='left')
        temp_df = pd.merge(temp_df,temp_df3,on=['x'],how='left')
        temp_df = pd.merge(temp_df,temp_df4,on=['x'],how='left')
        temp_df = pd.merge(temp_df,temp_df5,on=['x'],how='left')

        temp_df["x"] = pd.to_datetime(
            temp_df["x"], unit="ms", utc=True
        ).dt.tz_convert("Asia/Shanghai")
        temp_df["x"] = temp_df["x"].dt.date
        temp_df.rename(columns={'x':'date'},inplace=True)
        # temp_df.columns = [
        #     "date",
        #     "unit_value",
        #     "daily_growth_rate",
        #     "-",
        #     "cumulative_value",
        #     "cumulative_earning_ratio",
        #     "similar_type_rank",
        #     "similar_type_persent"
        # ]
        # temp_df = temp_df[
        #     [
        #         "date",
        #         "unit_value",
        #         "daily_growth_rate",
        #         "cumulative_value",
        #         "cumulative_earning_ratio",
        #         "similar_type_rank",
        #         "similar_type_persent",
        #     ]
        # ]
        # temp_df["date"] = pd.to_datetime(temp_df["date"]).dt.date
        # temp_df["unit_value"] = pd.to_numeric(temp_df["unit_value"])
        # temp_df["daily_growth_rate"] = pd.to_numeric(temp_df["daily_growth_rate"])
        # temp_df["cumulative_value"] = pd.to_numeric(temp_df["cumulative_value"])
        # temp_df["cumulative_earning_ratio"] = pd.to_numeric(temp_df["cumulative_earning_ratio"])
        # temp_df["similar_type_rank"] = pd.to_numeric(temp_df["similar_type_rank"])
        # temp_df["similar_type_persent"] = pd.to_numeric(temp_df["similar_type_persent"])

        return temp_df

    # 累计净值走势
    # if indicator == "累计净值走势":
    #     try:
    #         data_json = demjson.decode(
    #             data_text[
    #                 data_text.find("Data_ACWorthTrend")
    #                 + 20 : data_text.find("Data_grandTotal")
    #                 - 16
    #             ]
    #         )
    #     except:
    #         return pd.DataFrame()
    #     temp_df = pd.DataFrame(data_json)
    #     print(temp_df.head())
    #     if temp_df.empty:
    #         return pd.DataFrame()
    #     temp_df.columns = ["x", "y"]
    #     temp_df["x"] = pd.to_datetime(
    #         temp_df["x"], unit="ms", utc=True
    #     ).dt.tz_convert("Asia/Shanghai")
    #     temp_df["x"] = temp_df["x"].dt.date
    #     temp_df.columns = [
    #         "净值日期",
    #         "累计净值",
    #     ]
    #     temp_df = temp_df[
    #         [
    #             "净值日期",
    #             "累计净值",
    #         ]
    #     ]
    #     temp_df["净值日期"] = pd.to_datetime(temp_df["净值日期"]).dt.date
    #     temp_df["累计净值"] = pd.to_numeric(temp_df["累计净值"])
    #     return temp_df
    # 累计收益率走势
    if indicator == "累计收益率走势":
        data_json = demjson.decode(
            data_text[
                data_text.find("Data_grandTotal")
                + 18 : data_text.find("Data_rateInSimilarType")
                - 15
            ]
        )
        temp_df_main = pd.DataFrame(data_json[0]["data"])  # 本产品
        # temp_df_mean = pd.DataFrame(data_json[1]["data"])  # 同类平均
        # temp_df_hs = pd.DataFrame(data_json[2]["data"])  # 沪深300
        temp_df_main.columns = ["x", "y"]
        temp_df_main["x"] = pd.to_datetime(
            temp_df_main["x"], unit="ms", utc=True
        ).dt.tz_convert("Asia/Shanghai")
        temp_df_main["x"] = temp_df_main["x"].dt.date
        temp_df_main.columns = [
            "净值日期",
            "累计收益率",
        ]
        temp_df_main = temp_df_main[
            [
                "净值日期",
                "累计收益率",
            ]
        ]
        temp_df_main["净值日期"] = pd.to_datetime(temp_df_main["净值日期"]).dt.date
        temp_df_main["累计收益率"] = pd.to_numeric(temp_df_main["累计收益率"])
        return temp_df_main
    # 同类排名走势
    if indicator == "同类排名走势":
        data_json = demjson.decode(
            data_text[
                data_text.find("Data_rateInSimilarType")
                + 25 : data_text.find("Data_rateInSimilarPersent")
                - 16
            ]
        )
        temp_df = pd.DataFrame(data_json)
        temp_df["x"] = pd.to_datetime(
            temp_df["x"], unit="ms", utc=True
        ).dt.tz_convert("Asia/Shanghai")
        temp_df["x"] = temp_df["x"].dt.date
        temp_df.columns = [
            "报告日期",
            "同类型排名-每日近三月排名",
            "总排名-每日近三月排名",
        ]
        temp_df = temp_df[
            [
                "报告日期",
                "同类型排名-每日近三月排名",
                "总排名-每日近三月排名",
            ]
        ]
        temp_df["报告日期"] = pd.to_datetime(temp_df["报告日期"]).dt.date
        temp_df["同类型排名-每日近三月排名"] = pd.to_numeric(temp_df["同类型排名-每日近三月排名"])
        temp_df["总排名-每日近三月排名"] = pd.to_numeric(temp_df["总排名-每日近三月排名"])
        return temp_df
    # 同类排名百分比
    if indicator == "同类排名百分比":
        data_json = demjson.decode(
            data_text[
                data_text.find("Data_rateInSimilarPersent")
                + 26 : data_text.find("Data_fluctuationScale")
                - 23
            ]
        )
        temp_df = pd.DataFrame(data_json)
        temp_df.columns = ["x", "y"]
        temp_df["x"] = pd.to_datetime(
            temp_df["x"], unit="ms", utc=True
        ).dt.tz_convert("Asia/Shanghai")
        temp_df["x"] = temp_df["x"].dt.date
        temp_df.columns = [
            "报告日期",
            "同类型排名-每日近3月收益排名百分比",
        ]
        temp_df = temp_df[
            [
                "报告日期",
                "同类型排名-每日近3月收益排名百分比",
            ]
        ]
        temp_df["报告日期"] = pd.to_datetime(temp_df["报告日期"]).dt.date
        temp_df["同类型排名-每日近3月收益排名百分比"] = pd.to_numeric(
            temp_df["同类型排名-每日近3月收益排名百分比"]
        )
        return temp_df

    # 分红送配详情
    if indicator == "分红送配详情":
        url = f"http://fundf10.eastmoney.com/fhsp_{fund}.html"
        r = requests.get(url, headers=headers)
        temp_df = pd.read_html(r.text)[1]
        if temp_df.iloc[0, 1] == "暂无分红信息!":
            return None
        else:
            return temp_df

    # 拆分详情
    if indicator == "拆分详情":
        url = f"http://fundf10.eastmoney.com/fhsp_{fund}.html"
        r = requests.get(url, headers=headers)
        temp_df = pd.read_html(r.text)[2]
        if temp_df.iloc[0, 1] == "暂无拆分信息!":
            return None
        else:
            return temp_df

def stock_zh_a_daily(
        symbol: str = "sh603843",
        start_date: str = "19900101",
        end_date: str = "21000118",
        adjust: str = "",
    ) -> pd.DataFrame:
    """
    新浪财经-A 股-个股的历史行情数据, 大量抓取容易封 IP
    https://finance.sina.com.cn/realstock/company/sh603843/nc.shtml
    :param start_date: 20201103; 开始日期
    :type start_date: str
    :param end_date: 20201103; 结束日期
    :type end_date: str
    :param symbol: sh600000
    :type symbol: str
    :param adjust: 默认为空: 返回不复权的数据; qfq: 返回前复权后的数据; hfq: 返回后复权后的数据; hfq-factor: 返回后复权因子; hfq-factor: 返回前复权因子
    :type adjust: str
    :return: specific data
    :rtype: pandas.DataFrame
    """

    def _fq_factor(method: str) -> pd.DataFrame:
        if method == "hfq":
            res = requests.get(zh_sina_a_stock_hfq_url.format(symbol))
            hfq_factor_df = pd.DataFrame(
                eval(res.text.split("=")[1].split("\n")[0])["data"]
            )
            if hfq_factor_df.shape[0] == 0:
                raise ValueError("sina hfq factor not available")
            hfq_factor_df.columns = ["date", "hfq_factor"]
            hfq_factor_df.index = pd.to_datetime(hfq_factor_df.date)
            del hfq_factor_df["date"]
            hfq_factor_df.reset_index(inplace=True)
            return hfq_factor_df
        else:
            res = requests.get(zh_sina_a_stock_qfq_url.format(symbol))
            qfq_factor_df = pd.DataFrame(
                eval(res.text.split("=")[1].split("\n")[0])["data"]
            )
            if qfq_factor_df.shape[0] == 0:
                raise ValueError("sina hfq factor not available")
            qfq_factor_df.columns = ["date", "qfq_factor"]
            qfq_factor_df.index = pd.to_datetime(qfq_factor_df.date)
            del qfq_factor_df["date"]
            qfq_factor_df.reset_index(inplace=True)
            return qfq_factor_df

    if adjust in ("hfq-factor", "qfq-factor"):
        return _fq_factor(adjust.split("-")[0])

    res = requests.get(zh_sina_a_stock_hist_url.format(symbol))
    js_code = py_mini_racer.MiniRacer()
    js_code.eval(hk_js_decode)
    dict_list = js_code.call(
        "d", res.text.split("=")[1].split(";")[0].replace('"', "")
    )  # 执行js解密代码
    data_df = pd.DataFrame(dict_list)
    data_df.index = pd.to_datetime(data_df["date"]).dt.date
    del data_df["date"]
    data_df = data_df.astype("float")
    r = requests.get(zh_sina_a_stock_amount_url.format(symbol, symbol))
    amount_data_json = demjson.decode(
        r.text[r.text.find("[") : r.text.rfind("]") + 1]
    )
    amount_data_df = pd.DataFrame(amount_data_json)
    amount_data_df.index = pd.to_datetime(amount_data_df.date)
    del amount_data_df["date"]
    temp_df = pd.merge(
        data_df, amount_data_df, left_index=True, right_index=True, how="outer"
    )
    # 使用 ffill 替代 fillna(method="ffill") 以避免未来弃用警告
    temp_df.ffill(inplace=True)
    temp_df = temp_df.astype(float)
    temp_df["amount"] = temp_df["amount"] * 10000
    temp_df["turnover"] = temp_df["volume"] / temp_df["amount"]
    temp_df.columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "outstanding_share",
        "turnover",
    ]
    if adjust == "":
        temp_df = temp_df[start_date:end_date]
        temp_df.drop_duplicates(
            subset=["open", "high", "low", "close", "volume"], inplace=True
        )
        temp_df["open"] = round(temp_df["open"], 2)
        temp_df["high"] = round(temp_df["high"], 2)
        temp_df["low"] = round(temp_df["low"], 2)
        temp_df["close"] = round(temp_df["close"], 2)
        temp_df.dropna(inplace=True)
        temp_df.drop_duplicates(inplace=True)
        temp_df.reset_index(inplace=True)
        return temp_df
    if adjust == "hfq":
        res = requests.get(zh_sina_a_stock_hfq_url.format(symbol))
        hfq_factor_df = pd.DataFrame(
            eval(res.text.split("=")[1].split("\n")[0])["data"]
        )
        hfq_factor_df.columns = ["date", "hfq_factor"]
        hfq_factor_df.index = pd.to_datetime(hfq_factor_df.date)
        del hfq_factor_df["date"]
        temp_df = pd.merge(
            temp_df,
            hfq_factor_df,
            left_index=True,
            right_index=True,
            how="outer",
        )
        # 使用 ffill 替代 fillna(method="ffill") 以避免未来弃用警告
        temp_df.ffill(inplace=True)
        temp_df = temp_df.astype(float)
        temp_df.dropna(inplace=True)
        temp_df.drop_duplicates(
            subset=["open", "high", "low", "close", "volume"], inplace=True
        )
        temp_df["open"] = temp_df["open"] * temp_df["hfq_factor"]
        temp_df["high"] = temp_df["high"] * temp_df["hfq_factor"]
        temp_df["close"] = temp_df["close"] * temp_df["hfq_factor"]
        temp_df["low"] = temp_df["low"] * temp_df["hfq_factor"]
        temp_df = temp_df.iloc[:, :-1]
        temp_df = temp_df[start_date:end_date]
        temp_df["open"] = round(temp_df["open"], 2)
        temp_df["high"] = round(temp_df["high"], 2)
        temp_df["low"] = round(temp_df["low"], 2)
        temp_df["close"] = round(temp_df["close"], 2)
        temp_df.dropna(inplace=True)
        temp_df.reset_index(inplace=True)
        return temp_df

    if adjust == "qfq":
        res = requests.get(zh_sina_a_stock_qfq_url.format(symbol))
        qfq_factor_df = pd.DataFrame(
            eval(res.text.split("=")[1].split("\n")[0])["data"]
        )
        qfq_factor_df.columns = ["date", "qfq_factor"]
        qfq_factor_df.index = pd.to_datetime(qfq_factor_df.date)
        del qfq_factor_df["date"]

        temp_df = pd.merge(
            temp_df,
            qfq_factor_df,
            left_index=True,
            right_index=True,
            how="outer",
        )
        # 使用 ffill 替代 fillna(method="ffill") 以避免未来弃用警告
        temp_df.ffill(inplace=True)
        temp_df = temp_df.astype(float)
        temp_df.dropna(inplace=True)
        temp_df.drop_duplicates(
            subset=["open", "high", "low", "close", "volume"], inplace=True
        )
        temp_df["open"] = temp_df["open"] / temp_df["qfq_factor"]
        temp_df["high"] = temp_df["high"] / temp_df["qfq_factor"]
        temp_df["close"] = temp_df["close"] / temp_df["qfq_factor"]
        temp_df["low"] = temp_df["low"] / temp_df["qfq_factor"]
        temp_df = temp_df.iloc[:, :-1]
        temp_df = temp_df[start_date:end_date]
        temp_df["open"] = round(temp_df["open"], 2)
        temp_df["high"] = round(temp_df["high"], 2)
        temp_df["low"] = round(temp_df["low"], 2)
        temp_df["close"] = round(temp_df["close"], 2)
        temp_df.dropna(inplace=True)
        temp_df.reset_index(inplace=True)
        return temp_df

def index_code_id_map_em() -> dict:
    """
    东方财富-股票和市场代码
    http://quote.eastmoney.com/center/gridlist.html#hs_a_board
    :return: 股票和市场代码
    :rtype: dict
    """
    url = "http://80.push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "10000",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:1 t:2,m:1 t:23",
        "fields": "f12",
        "_": "1623833739532",
    }
    r = requests.get(url, params=params)
    data_json = r.json()
    if not data_json["data"]["diff"]:
        return dict()
    temp_df = pd.DataFrame(data_json["data"]["diff"])
    temp_df["market_id"] = 1
    temp_df.columns = ["sh_code", "sh_id"]
    code_id_dict = dict(zip(temp_df["sh_code"], temp_df["sh_id"]))
    params = {
        "pn": "1",
        "pz": "10000",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:0 t:6,m:0 t:80",
        "fields": "f12",
        "_": "1623833739532",
    }
    r = requests.get(url, params=params)
    data_json = r.json()
    if not data_json["data"]["diff"]:
        return dict()
    temp_df_sz = pd.DataFrame(data_json["data"]["diff"])
    temp_df_sz["sz_id"] = 0
    code_id_dict.update(dict(zip(temp_df_sz["f12"], temp_df_sz["sz_id"])))
    params = {
        "pn": "1",
        "pz": "10000",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:0 t:81 s:2048",
        "fields": "f12",
        "_": "1623833739532",
    }
    r = requests.get(url, params=params)
    data_json = r.json()
    if not data_json["data"]["diff"]:
        return dict()
    temp_df_sz = pd.DataFrame(data_json["data"]["diff"])
    temp_df_sz["bj_id"] = 0
    code_id_dict.update(dict(zip(temp_df_sz["f12"], temp_df_sz["bj_id"])))
    code_id_dict = {
        key: value - 1 if value == 1 else value + 1
        for key, value in code_id_dict.items()
    }
    return code_id_dict


def index_zh_a_hist(
    symbol: str = "000859",
    period: str = "daily",
    start_date: str = "19700101",
    end_date: str = "22220101",
) -> pd.DataFrame:
    """
    东方财富网-中国股票指数-行情数据
    https://quote.eastmoney.com/zz/2.000859.html
    :param symbol: 指数代码
    :type symbol: str
    :param period: choice of {'daily', 'weekly', 'monthly'}
    :type period: str
    :param start_date: 开始日期
    :type start_date: str
    :param end_date: 结束日期
    :type end_date: str
    :return: 行情数据
    :rtype: pandas.DataFrame
    """
    code_id_dict = index_code_id_map_em()
    period_dict = {"daily": "101", "weekly": "102", "monthly": "103"}
    url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    try:
        params = {
            "secid": f"{code_id_dict[symbol]}.{symbol}",
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": period_dict[period],
            "fqt": "0",
            "beg": "0",
            "end": "20500000",
            "_": "1623766962675",
        }
    except KeyError:
        params = {
            "secid": f"1.{symbol}",
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": period_dict[period],
            "fqt": "0",
            "beg": "0",
            "end": "20500000",
            "_": "1623766962675",
        }
        r = requests.get(url, params=params)
        data_json = r.json()
        if data_json["data"] is None:
            params = {
                "secid": f"0.{symbol}",
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": period_dict[period],
                "fqt": "0",
                "beg": "0",
                "end": "20500000",
                "_": "1623766962675",
            }
            r = requests.get(url, params=params)
            data_json = r.json()
            if data_json["data"] is None:
                params = {
                    "secid": f"2.{symbol}",
                    "ut": "7eea3edcaed734bea9cbfc24409ed989",
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    "klt": period_dict[period],
                    "fqt": "0",
                    "beg": "0",
                    "end": "20500000",
                    "_": "1623766962675",
                }
                r = requests.get(url, params=params)
                data_json = r.json()
                if data_json["data"] is None:
                    params = {
                        "secid": f"47.{symbol}",
                        "ut": "7eea3edcaed734bea9cbfc24409ed989",
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                        "klt": period_dict[period],
                        "fqt": "0",
                        "beg": "0",
                        "end": "20500000",
                        "_": "1623766962675",
                    }
    r = requests.get(url, params=params)
    data_json = r.json()
    try:
        temp_df = pd.DataFrame(
            [item.split(",") for item in data_json["data"]["klines"]]
        )
    except:
        # 兼容 000859(中证国企一路一带) 和 000861(中证央企创新)
        params = {
            "secid": f"2.{symbol}",
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": period_dict[period],
            "fqt": "0",
            "beg": "0",
            "end": "20500000",
            "_": "1623766962675",
        }
        r = requests.get(url, params=params)
        data_json = r.json()
        temp_df = pd.DataFrame(
            [item.split(",") for item in data_json["data"]["klines"]]
        )
    temp_df.columns = [
        "日期",
        "开盘",
        "收盘",
        "最高",
        "最低",
        "成交量",
        "成交额",
        "振幅",
        "涨跌幅",
        "涨跌额",
        "换手率",
    ]
    temp_df.index = pd.to_datetime(temp_df["日期"])
    temp_df = temp_df[start_date:end_date]
    temp_df.reset_index(inplace=True, drop=True)
    temp_df["开盘"] = pd.to_numeric(temp_df["开盘"])
    temp_df["收盘"] = pd.to_numeric(temp_df["收盘"])
    temp_df["最高"] = pd.to_numeric(temp_df["最高"])
    temp_df["最低"] = pd.to_numeric(temp_df["最低"])
    temp_df["成交量"] = pd.to_numeric(temp_df["成交量"])
    temp_df["成交额"] = pd.to_numeric(temp_df["成交额"])
    temp_df["振幅"] = pd.to_numeric(temp_df["振幅"])
    temp_df["涨跌幅"] = pd.to_numeric(temp_df["涨跌幅"])
    temp_df["涨跌额"] = pd.to_numeric(temp_df["涨跌额"])
    temp_df["换手率"] = pd.to_numeric(temp_df["换手率"])
    return temp_df
    
def main_handler(event,context):
    if event["type"] == 'fund':
        try:
            result = fund_open_fund_info_em(event["code"],"单位净值+累计净值","pandas")
            # print(result.head())
            json_data = result.to_json(orient='records')
            json_object = json.loads(json_data)
            return {'code':200,"data":json_object}
        except:
            print('scf invoke error')
            return {'code':0,'msg':'scf invoke error'}
    elif event["type"] == 'all_fund':
        try:
            result = fund_open_fund_daily_em()
            json_data = result.to_json(orient='records')
            json_object = json.loads(json_data)
            return {'code':200,"data":json_object}
        except:
            print('scf invoke error')
            return {'code':0,'msg':'scf invoke error'}        
    elif event["type"] == 'stock':
        if "start_date" in event:
            start_date = event["start_date"]
        else:
            start_date = "19700101"
        if "end_date" in event:
            end_date = event["end_date"]
        else:
            end_date = "20500101"
        if "adjust" in event:
            adjust = event["adjust"]
        else:
            adjust = ''
        try:
            result = stock_zh_a_daily(event["code"],start_date,end_date,adjust)
            print(result)
            # result = index_zh_a_hist(event["code"],start_date,end_date,adjust)
            # print(result.head())
            json_data = result.to_json(orient='records')
            json_object = json.loads(json_data)
            return {'code':200,"data":json_object}
        except Exception as e:
            print('scf invoke error',str(e))
            return {'code':0,'msg':'scf invoke error'}   
    elif event["type"] == 'index':
        if "start_date" in event:
            start_date = event["start_date"]
        else:
            start_date = "19700101"
        if "end_date" in event:
            end_date = event["end_date"]
        else:
            end_date = "20500101"
        try:
            result = index_zh_a_hist(event["code"],event["period"],start_date,end_date)
            # print(result.head())
            json_data = result.to_json(orient='records')
            json_object = json.loads(json_data)
            return {'code':200,"data":json_object}
        except:
            print('scf invoke error')
            return {'code':0,'msg':'scf invoke error'}             
    else:
        return {'code':0,'msg':'scf invoke error'}     
# x = main_handler({"type":"index","code":"510050","period":"daily"},1)
# print(x)