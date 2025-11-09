
"""
PostgresHandler: 使用后端Go API读取PG历史数据、通过SCF拉取最新数据、转换为PG列并批量写入（异步版）。

接口参考（postgres-handler/main.go）：
- POST /api/v1/stock-data                -> 插入单条
- POST /api/v1/stock-data/batch          -> 批量插入
- POST /api/v1/stock-data/{symbol}       -> 最近数据（JSON: {type, limit, offset}）
- POST /api/v1/stock-data/{symbol}/range -> 按日期范围查询（JSON: {type, start_date, end_date}, 日期格式 YYYY-MM-DD）
- GET  /health                           -> 服务健康检查

本类职责：
1) 读取PG历史数据（按最新或按日期范围）
2) 使用SCF获取增量最新数据
3) 将数据转换为PG需要的列结构
4) 通过批量接口写入PG
"""

import asyncio, os
import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
ai_functions_dir = os.path.dirname(current_dir)
finance_dir = os.path.dirname(ai_functions_dir)
akshare__server_dir = os.path.join(finance_dir, "akshare-server")
sys.path.append(akshare__server_dir)
from ak_functions import main_handler

# 复用已经实现和验证过的数据获取与转换逻辑
from get_finanial_data import (
    finance_dir,
    get_stock_data_from_scf,
    convert_dataframe_to_api_format,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PostgresHandler:
    def __init__(self, base_url: str = "http://go-api.meetlife.com.cn:8000", timeout: int = 30, api_token: Optional[str] = None, allow_get_fallback: bool = True):
        """初始化PG后端API客户端（异步版，使用 httpx.AsyncClient）"""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_token = api_token or "fintrack-dev-token"
        self.allow_get_fallback = allow_get_fallback
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(f"PostgresHandler 初始化完成，服务地址: {self.base_url}")

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def open(self):
        """创建异步HTTP客户端"""
        if self._client is None:
            # 将 base_url 设置到客户端，后续请求仅传入 path
            # 默认开启 gzip 支持（httpx 默认会添加 Accept-Encoding 并自动解压）
            headers = {
                "Accept-Encoding": "gzip, deflate",
                "X-Token": self.api_token,
            }
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=headers,
            )
            logger.debug("AsyncClient 已创建")

    async def close(self):
        """关闭异步HTTP客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("AsyncClient 已关闭")

    # --------------------------- 基础HTTP方法 ---------------------------
    async def _get(self, path: str, params: Optional[Dict] = None):
        await self.open()
        assert self._client is not None
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _post_json(self, path: str, payload):
        await self.open()
        assert self._client is not None
        resp = await self._client.post(path, json=payload)
        resp.raise_for_status()
        return resp.json()

    # --------------------------- 健康检查 ---------------------------
    async def health_check(self) -> bool:
        try:
            data = await self._get("/health")
            ok = data.get("status") == "ok"
            logger.info(f"API服务健康检查: {'正常' if ok else '异常'}")
            return ok
        except Exception as e:
            logger.error(f"API健康检查失败: {e}")
            return False

    # --------------------------- 读取PG数据 ---------------------------
    async def get_latest(self, symbol: str, stock_type: int = 1, limit: int = 1) -> Optional[Dict]:
        """获取PG中该股票最新一条记录（按datetime降序）。服务端改为 POST JSON 方式。"""
        try:
            payload = {"type": stock_type, "limit": limit, "offset": 0}
            resp = await self._post_json(f"/api/v1/stock-data/{symbol}", payload)
            data = resp.get("data") if isinstance(resp, dict) else resp
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            # 兼容旧服务：尝试 GET 查询
            if self.allow_get_fallback:
                resp_get = await self._get(
                    f"/api/v1/stock-data/{symbol}",
                    params={"type": stock_type, "limit": limit, "offset": 0},
                )
                data_get = resp_get.get("data") if isinstance(resp_get, dict) else resp_get
                if isinstance(data_get, list) and len(data_get) > 0:
                    return data_get[0]
            return None
        except Exception as e:
            logger.error(f"获取最新记录失败: {e}")
            return None

    async def get_by_date_range(self, symbol: str, start_date: str, end_date: str, stock_type: int = 1) -> List[Dict]:
        """
        根据日期范围读取PG数据（YYYY-MM-DD 到 YYYY-MM-DD）。服务端改为 POST JSON 方式。
        返回 Go API 的原始JSON（数组）。
        """
        try:
            payload = {"type": stock_type, "start_date": start_date, "end_date": end_date}
            resp = await self._post_json(f"/api/v1/stock-data/{symbol}/range", payload)
            data = resp.get("data") if isinstance(resp, dict) else resp
            if isinstance(data, list):
                return data
            # 兼容旧服务：尝试 GET 查询
            if self.allow_get_fallback:
                resp_get = await self._get(
                    f"/api/v1/stock-data/{symbol}/range",
                    params={"type": stock_type, "start_date": start_date, "end_date": end_date},
                )
                data_get = resp_get.get("data") if isinstance(resp_get, dict) else resp_get
                if isinstance(data_get, list):
                    return data_get
            return []
        except Exception as e:
            logger.error(f"按日期范围查询失败: {e}")
            return []

    async def get_all(self, symbol: str, stock_type: int = 1) -> List[Dict]:
        """获取PG中该股票所有记录（按datetime升序）"""
        try:
            limit = 10000
            offset = 0
            all_records: List[Dict] = []

            while True:
                payload = {"type": stock_type, "limit": limit, "offset": offset}
                resp = await self._post_json(f"/api/v1/stock-data/{symbol}", payload=payload)
                batch = resp.get("data") if isinstance(resp, dict) else resp

                if not isinstance(batch, list) or len(batch) == 0:
                    # 兼容旧服务：首次空页时，尝试切换为 GET 方式分页
                    if self.allow_get_fallback and offset == 0:
                        while True:
                            resp_get = await self._get(
                                f"/api/v1/stock-data/{symbol}",
                                params={"type": stock_type, "limit": limit, "offset": offset},
                            )
                            batch_get = resp_get.get("data") if isinstance(resp_get, dict) else resp_get
                            if not isinstance(batch_get, list) or len(batch_get) == 0:
                                break
                            all_records.extend(batch_get)
                            if len(batch_get) < limit:
                                break
                            offset += limit
                        break
                    else:
                        break

                all_records.extend(batch)

                # 若不足一页，终止；否则翻页
                if len(batch) < limit:
                    break
                offset += limit

            # 服务端是按 datetime DESC 返回，这里升序排列
            try:
                all_records.sort(key=lambda x: x.get("datetime"))
            except Exception:
                pass

            logger.info(f"获取所有记录: {len(all_records)}")
            return all_records
        except Exception as e:
            logger.error(f"获取所有记录失败: {e}")
            return []

    # --------------------------- DataFrame 辅助与返回DF的方法 ---------------------------
    @staticmethod
    def _records_to_df(records: List[Dict]) -> pd.DataFrame:
        """
        将从PG服务返回的记录列表转换为DataFrame，列对齐 ak_stock_data 输出格式。

        输出列包含（若服务有返回）：
        - datetime（pandas.Timestamp），datetime_int（秒级int）
        - open, close, high, low, volume, amount
        - amplitude, percentage_change, amount_change, turnover_rate
        - type, symbol, created_at, updated_at
        """
        if not records:
            return pd.DataFrame(
                columns=[
                    "datetime",
                    "datetime_int",
                    "open",
                    "close",
                    "high",
                    "low",
                    "volume",
                    "amount",
                    "amplitude",
                    "percentage_change",
                    "amount_change",
                    "turnover_rate",
                    "type",
                    "symbol",
                    "created_at",
                    "updated_at",
                ]
            )

        df = pd.DataFrame.from_records(records)

        # 解析日期为 pandas.Timestamp，并统一为无时区（tz-naive），避免比较或计算时报错
        if "datetime" in df.columns:
            try:
                dt_series = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
                try:
                    # 去除时区信息，统一为 tz-naive
                    dt_series = dt_series.dt.tz_localize(None)
                except Exception:
                    pass
                df["datetime"] = dt_series
            except Exception:
                pass

        # 添加/更新 datetime_int（秒级）
        try:
            if "datetime" in df.columns and pd.api.types.is_datetime64_any_dtype(df["datetime"]):
                df["datetime_int"] = (df["datetime"].astype("int64") // 10**9).astype("Int64")
        except Exception:
            # 尝试从字符串解析后再计算
            try:
                dt = pd.to_datetime(df["datetime"], errors="coerce")
                df["datetime_int"] = (dt.astype("int64") // 10**9).astype("Int64")
                df["datetime"] = dt
            except Exception:
                pass

        # 数值列类型规范化
        float_cols = [
            "open",
            "close",
            "high",
            "low",
            "amount",
            "amplitude",
            "percentage_change",
            "amount_change",
            "turnover_rate",
        ]
        int_cols = ["volume"]

        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        # 升序排列
        if "datetime" in df.columns:
            try:
                df = df.sort_values("datetime")
            except Exception:
                pass

        return df

    async def get_latest_df(self, symbol: str, stock_type: int = 1, limit: int = 1) -> pd.DataFrame:
        """
        获取PG中该股票最新记录并返回DataFrame。
        与 get_latest 相同语义，返回最多 limit 条记录的 DataFrame。
        """
        try:
            payload = {"type": stock_type, "limit": limit, "offset": 0}
            resp = await self._post_json(f"/api/v1/stock-data/{symbol}", payload)
            data = resp.get("data") if isinstance(resp, dict) else resp
            if isinstance(data, list) and len(data) > 0:
                return self._records_to_df(data)
            # GET 兼容回退
            if self.allow_get_fallback:
                resp_get = await self._get(
                    f"/api/v1/stock-data/{symbol}",
                    params={"type": stock_type, "limit": limit, "offset": 0},
                )
                data_get = resp_get.get("data") if isinstance(resp_get, dict) else resp_get
                if isinstance(data_get, list) and len(data_get) > 0:
                    return self._records_to_df(data_get)
            return self._records_to_df([])
        except Exception as e:
            logger.error(f"获取最新记录DF失败: {e}")
            return self._records_to_df([])

    async def get_by_date_range_df(self, symbol: str, start_date: str, end_date: str, stock_type: int = 1) -> pd.DataFrame:
        """
        按日期范围读取PG数据并返回DataFrame。日期格式：YYYY-MM-DD。
        """
        try:
            payload = {"type": stock_type, "start_date": start_date, "end_date": end_date}
            resp = await self._post_json(f"/api/v1/stock-data/{symbol}/range", payload)
            data = resp.get("data") if isinstance(resp, dict) else resp
            if isinstance(data, list):
                return self._records_to_df(data)
            # GET 兼容回退
            if self.allow_get_fallback:
                resp_get = await self._get(
                    f"/api/v1/stock-data/{symbol}/range",
                    params={"type": stock_type, "start_date": start_date, "end_date": end_date},
                )
                data_get = resp_get.get("data") if isinstance(resp_get, dict) else resp_get
                if isinstance(data_get, list):
                    return self._records_to_df(data_get)
            return self._records_to_df([])
        except Exception as e:
            logger.error(f"按日期范围查询DF失败: {e}")
            return self._records_to_df([])

    async def get_all_df(self, symbol: str, stock_type: int = 1) -> pd.DataFrame:
        """
        获取PG中该股票所有记录并返回DataFrame（按datetime升序）。
        """
        try:
            records = await self.get_all(symbol, stock_type=stock_type)
            return self._records_to_df(records)
        except Exception as e:
            logger.error(f"获取所有记录DF失败: {e}")
            return self._records_to_df([])

    async def stock_data_df(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        years: int = 0,
        time_step: Optional[int] = None,
        stock_type: int = 1,
    ) -> pd.DataFrame:
        """
        从PG服务获取股票数据并返回DataFrame，语义对齐 ak_stock_data：
        - 当 end_date 为 None 时，取最近一个交易日（近两个月范围内）作为结束日期
        - 当 years > 0 时，按 years 推算 start_date；否则使用传入的 start_date
        - 支持 time_step 对 datetime 列进行平移（单位：天）

        注意：PG服务的日期范围参数格式为 YYYY-MM-DD。
        """
        try:
            # 规范 end_date
            if end_date is None:
                # 与 ak_stock_data 的默认一致：近 56 天内的最近交易日
                from get_finanial_data import get_previous_trading_days
                end_date_str = get_previous_trading_days(days=56)
            else:
                end_date_str = end_date

            # 计算 start_date
            if years and years > 0:
                end_dt = pd.Timestamp(end_date_str)
                start_dt = end_dt - pd.Timedelta(days=years * 365)
                start_date_str = start_dt.strftime("%Y%m%d")
            else:
                start_date_str = start_date or "19900101"

            # 转换为服务需要的 YYYY-MM-DD
            start_dash = pd.Timestamp(start_date_str).strftime("%Y-%m-%d")
            end_dash = pd.Timestamp(end_date_str).strftime("%Y-%m-%d")

            df = await self.get_by_date_range_df(symbol, start_dash, end_dash, stock_type=stock_type)

            # 应用时间步长偏移
            if time_step is not None and not df.empty and "datetime" in df.columns:
                try:
                    df["datetime"] = df["datetime"] + pd.Timedelta(days=time_step)
                    df["datetime_int"] = (df["datetime"].astype("int64") // 10**9).astype("Int64")
                except Exception:
                    pass

            return df
        except Exception as e:
            logger.error(f"stock_data_df 获取失败: {e}")
            return self._records_to_df([])

    async def ensure_date_range_df(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        stock_type: int = 1,
        batch_size: int = 1000,
        requery: bool = True,
    ) -> pd.DataFrame:
        """
        检查返回数据的最新日期是否覆盖指定区间，如果不覆盖则调用增量同步到PG，并可选重试读取。

        入参日期可为 "YYYY-MM-DD" 或 "YYYYMMDD"，内部自动规范。
        返回：指定区间的 DataFrame。
        """
        try:
            # 规范化日期格式
            start_dash = pd.Timestamp(start_date).strftime("%Y-%m-%d")
            end_dash = pd.Timestamp(end_date).strftime("%Y-%m-%d")
            start_compact = pd.Timestamp(start_date).strftime("%Y%m%d")
            end_compact = pd.Timestamp(end_date).strftime("%Y%m%d")

            # 第一次尝试读取区间数据
            df = await self.get_by_date_range_df(symbol, start_dash, end_dash, stock_type=stock_type)

            # 若为空或无 datetime 列，则直接同步并重读
            if df is None or df.empty or ("datetime" not in df.columns):
                logger.info(f"区间数据为空或缺少datetime列，触发增量同步: {symbol} {start_compact}~{end_compact}")
                await self.sync_stock(symbol, stock_type=stock_type, batch_size=batch_size, start_date=start_compact, end_date=end_compact)
                if requery:
                    return await self.get_by_date_range_df(symbol, start_dash, end_dash, stock_type=stock_type)
                return self._records_to_df([])

            # 检查最新日期是否覆盖到 end_date
            # 统一为 tz-naive，避免比较时报错
            latest_dt = pd.to_datetime(df["datetime"], errors="coerce", utc=True).dt.tz_localize(None).max()
            target_end = pd.Timestamp(end_dash).tz_localize(None) if hasattr(pd.Timestamp(end_dash), 'tz_localize') else pd.Timestamp(end_dash)
            if pd.isna(latest_dt) or latest_dt.normalize() < target_end.normalize():
                # 计算增量开始日期：已经存在最新日期 + 1 天，与 start_date 取较晚者
                if pd.isna(latest_dt):
                    incr_start_compact = start_compact
                else:
                    incr_start_compact = self._to_yyyymmdd(latest_dt.to_pydatetime() + timedelta(days=1))
                    # 若用户给定的 start_date 更晚，则用用户给定的
                    given_start_compact = start_compact
                    if pd.Timestamp(given_start_compact) > pd.Timestamp(incr_start_compact):
                        incr_start_compact = given_start_compact

                logger.info(f"最新日期 {latest_dt} 未覆盖到 {target_end}，增量同步: {symbol} {incr_start_compact}~{end_compact}")
                await self.sync_stock(symbol, stock_type=stock_type, batch_size=batch_size, start_date=incr_start_compact, end_date=end_compact)
                if requery:
                    return await self.get_by_date_range_df(symbol, start_dash, end_dash, stock_type=stock_type)

            return df
        except Exception as e:
            logger.error(f"ensure_date_range_df 失败: {e}")
            return self._records_to_df([])
    # --------------------------- 写入PG数据 ---------------------------
    async def insert_single(self, record: Dict) -> Dict:
        """插入单条PG记录，record需符合StockData JSON结构"""
        return await self._post_json("/api/v1/stock-data", record)

    async def batch_insert(self, records: List[Dict]) -> Dict:
        """批量插入PG记录"""
        return await self._post_json("/api/v1/stock-data/batch", records)

    # --------------------------- SCF增量同步 ---------------------------
    @staticmethod
    def _to_yyyymmdd(dt: datetime) -> str:
        return dt.strftime("%Y%m%d")

    @staticmethod
    def _parse_iso_datetime(dt_str: str) -> Optional[datetime]:
        """支持诸如 '2025-10-31T08:00:00Z' 或 RFC3339/ISO 格式"""
        if not dt_str:
            return None
        try:
            # 处理Z结尾
            if dt_str.endswith("Z"):
                dt_str = dt_str.replace("Z", "+00:00")
            return datetime.fromisoformat(dt_str)
        except Exception:
            try:
                return pd.to_datetime(dt_str).to_pydatetime()
            except Exception:
                return None

    async def sync_stock(self, symbol: str, stock_type: int = 1, batch_size: int = 1000,
                         start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """
        增量同步该股票：读取PG最新日期 -> 使用SCF获取从下一交易日到end_date的数据 -> 转换 -> 批量写入PG
        返回执行统计信息
        """
        result = {
            "symbol": symbol,
            "stock_type": stock_type,
            "success": False,
            "fetched_records": 0,
            "stored_records": 0,
            "batches": 0,
            "error": None,
        }

        if not await self.health_check():
            result["error"] = "API服务不可用"
            return result

        # 计算增量开始日期
        if not start_date:
            latest = await self.get_latest(symbol, stock_type=stock_type, limit=1)
            if latest and latest.get("datetime"):
                latest_dt = self._parse_iso_datetime(latest["datetime"])  # 已存储的最新日期
                if latest_dt:
                    start_dt = latest_dt + timedelta(days=1)
                    start_date = self._to_yyyymmdd(start_dt)
                    logger.info(f"最新PG日期: {latest_dt}, 增量开始: {start_date}")
                else:
                    # 无法解析则回退到较早日期
                    start_date = "19900101"
            else:
                # 数据库没有历史数据，从较早日期开始
                start_date = "19900101"

        # 结束日期默认取昨天
        if not end_date:
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

        try:
            # 使用SCF获取该区间数据（同步函数放入线程，避免阻塞事件循环）
            logger.info(f"从SCF获取数据: symbol={symbol}, start_date={start_date}, end_date={end_date}")
            df = await asyncio.to_thread(get_stock_data_from_scf, symbol, start_date, end_date)
            if df is None or df.empty:
                result["error"] = "SCF未返回数据"
                return result

            result["fetched_records"] = len(df)

            # 转换为PG API需要的列结构
            api_records = convert_dataframe_to_api_format(df, symbol=symbol, stock_type=stock_type)
            if not api_records:
                result["error"] = "数据转换失败或为空"
                return result

            # 按批次写入
            total = len(api_records)
            stored = 0
            batches = 0
            for i in range(0, total, batch_size):
                batch = api_records[i:i + batch_size]
                try:
                    await self.batch_insert(batch)
                    stored += len(batch)
                    batches += 1
                    logger.info(f"批量写入成功: 第 {batches} 批, 记录数={len(batch)}")
                except Exception as e:
                    logger.error(f"第 {batches + 1} 批写入失败: {e}")
                    # 失败批次可选择继续或中断，这里继续尝试后续批次
                    continue

            result.update({
                "stored_records": stored,
                "batches": batches,
                "success": stored > 0,
            })
            return result
        except Exception as e:
            logger.error(f"同步失败: {e}")
            result["error"] = str(e)
            return result

class SyncDataHanlder:
    def __init__(self, base_url: str = "http://8.163.5.7:8000", api_token: str = "fintrack-dev-token"):
        self.pg_handler = PostgresHandler(base_url=base_url, api_token=api_token)

    def update_stock(self, symbol: str, stock_type: int = 1, batch_size: int = 1000,
                         start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """
        增量同步该股票：读取PG最新日期 -> 使用SCF获取从下一交易日到end_date的数据 -> 转换 -> 批量写入PG
        返回执行统计信息
        """
        return self.pg_handler.sync_stock(symbol, stock_type, batch_size, start_date, end_date)


async def _demo():
    # 注意：远端服务端口为 8000，且需要携带固定 X-Token（默认 fintrack-dev-token）
    async with PostgresHandler(base_url="http://8.163.5.7:8000", api_token="fintrack-dev-token") as handler:
        ok = await handler.health_check()
        print("健康检查:", ok)

        latest = await handler.get_latest("600398", stock_type=1, limit=1)
        print("最新记录:", latest)

        # 设置一个有效的日期区间（最近 30 天）
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        print(f"测试日期区间: {start_date} 到 {end_date}")
        # 自动检查区间数据是否覆盖到 end_date，若未覆盖则触发增量同步并重试读取
        df = await handler.ensure_date_range_df(
            symbol="600398",
            start_date=start_date,
            end_date=end_date,
            stock_type=1,
            batch_size=1000,
            requery=True,
        )

        print("区间记录数:", len(df))
        if not df.empty:
            print("区间最新日期:", df["datetime"].max())


if __name__ == "__main__":
    asyncio.run(_demo())
