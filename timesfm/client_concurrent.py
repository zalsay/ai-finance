#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TimesFM 分组并发客户端
实现对GPU0和GPU1两个容器的分组并发调用
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TimesFMConcurrentClient:
    """TimesFM 并发客户端"""
    
    def __init__(self, gpu0_url: str = "http://localhost:8000", gpu1_url: str = "http://localhost:8001"):
        self.gpu0_url = gpu0_url
        self.gpu1_url = gpu1_url
        self.gpu_urls = [gpu0_url, gpu1_url]
        
    async def check_service_health(self, session: aiohttp.ClientSession, url: str) -> bool:
        """检查服务健康状态"""
        try:
            async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"服务 {url} 健康状态: {data}")
                    return data.get('model_loaded', False)
                else:
                    logger.warning(f"服务 {url} 健康检查失败，状态码: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"检查服务 {url} 健康状态失败: {e}")
            return False
    
    async def wait_for_services(self, max_wait_time: int = 300) -> bool:
        """等待服务启动"""
        logger.info("等待服务启动...")
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < max_wait_time:
                gpu0_ready = await self.check_service_health(session, self.gpu0_url)
                gpu1_ready = await self.check_service_health(session, self.gpu1_url)
                
                if gpu0_ready and gpu1_ready:
                    logger.info("所有服务已就绪")
                    return True
                
                logger.info(f"等待服务就绪... GPU0: {gpu0_ready}, GPU1: {gpu1_ready}")
                await asyncio.sleep(10)
        
        logger.error(f"等待 {max_wait_time} 秒后服务仍未就绪")
        return False
    
    async def predict_single_stock(self, session: aiohttp.ClientSession, url: str, stock_code: str, **kwargs) -> Dict[str, Any]:
        """单个股票预测"""
        request_data = {
            "stock_code": stock_code,
            "stock_type": kwargs.get("stock_type", "stock"),
            "time_step": kwargs.get("time_step", 0),
            "years": kwargs.get("years", 10),
            "horizon_len": kwargs.get("horizon_len", 5),
            "context_len": kwargs.get("context_len", 2048),
            "include_technical_indicators": kwargs.get("include_technical_indicators", True)
        }
        
        start_time = time.time()
        
        try:
            async with session.post(
                f"{url}/predict",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                result = await response.json()
                processing_time = time.time() - start_time
                
                result['client_processing_time'] = processing_time
                result['service_url'] = url
                
                if response.status == 200:
                    logger.info(f"股票 {stock_code} 在 {url} 预测成功，耗时: {processing_time:.2f}秒")
                else:
                    logger.error(f"股票 {stock_code} 在 {url} 预测失败，状态码: {response.status}")
                
                return result
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"股票 {stock_code} 在 {url} 预测异常: {e}")
            
            return {
                "success": False,
                "stock_code": stock_code,
                "error": str(e),
                "client_processing_time": processing_time,
                "service_url": url
            }
    
    async def predict_batch_on_service(self, session: aiohttp.ClientSession, url: str, stock_codes: List[str], **kwargs) -> Dict[str, Any]:
        """在单个服务上批量预测"""
        request_data = {
            "stock_codes": stock_codes,
            "stock_type": kwargs.get("stock_type", "stock"),
            "time_step": kwargs.get("time_step", 0),
            "years": kwargs.get("years", 10),
            "horizon_len": kwargs.get("horizon_len", 5),
            "context_len": kwargs.get("context_len", 2048),
            "include_technical_indicators": kwargs.get("include_technical_indicators", True)
        }
        
        start_time = time.time()
        
        try:
            async with session.post(
                f"{url}/predict/batch",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=600)
            ) as response:
                result = await response.json()
                processing_time = time.time() - start_time
                
                result['client_processing_time'] = processing_time
                result['service_url'] = url
                
                if response.status == 200:
                    logger.info(f"批量预测在 {url} 完成，{len(stock_codes)} 只股票，耗时: {processing_time:.2f}秒")
                else:
                    logger.error(f"批量预测在 {url} 失败，状态码: {response.status}")
                
                return result
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"批量预测在 {url} 异常: {e}")
            
            return {
                "success": False,
                "stock_codes": stock_codes,
                "error": str(e),
                "client_processing_time": processing_time,
                "service_url": url
            }
    
    def split_stocks_for_gpus(self, stock_codes: List[str]) -> Tuple[List[str], List[str]]:
        """将股票列表分配给两个GPU"""
        mid_point = len(stock_codes) // 2
        gpu0_stocks = stock_codes[:mid_point]
        gpu1_stocks = stock_codes[mid_point:]
        
        logger.info(f"股票分配: GPU0 ({len(gpu0_stocks)}只): {gpu0_stocks}")
        logger.info(f"股票分配: GPU1 ({len(gpu1_stocks)}只): {gpu1_stocks}")
        
        return gpu0_stocks, gpu1_stocks
    
    async def predict_concurrent_individual(self, stock_codes: List[str], **kwargs) -> Dict[str, Any]:
        """并发预测 - 单个股票模式"""
        logger.info(f"开始并发预测 {len(stock_codes)} 只股票（单个模式）")
        start_time = time.time()
        
        # 分配股票到两个GPU
        gpu0_stocks, gpu1_stocks = self.split_stocks_for_gpus(stock_codes)
        
        async with aiohttp.ClientSession() as session:
            # 创建所有预测任务
            tasks = []
            
            # GPU0 任务
            for stock_code in gpu0_stocks:
                task = self.predict_single_stock(session, self.gpu0_url, stock_code, **kwargs)
                tasks.append(task)
            
            # GPU1 任务
            for stock_code in gpu1_stocks:
                task = self.predict_single_stock(session, self.gpu1_url, stock_code, **kwargs)
                tasks.append(task)
            
            # 并发执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_results.append({"error": str(result)})
            elif result.get("success", False):
                successful_results.append(result)
            else:
                failed_results.append(result)
        
        total_time = time.time() - start_time
        
        summary = {
            "mode": "concurrent_individual",
            "total_stocks": len(stock_codes),
            "successful_predictions": len(successful_results),
            "failed_predictions": len(failed_results),
            "success_rate": len(successful_results) / len(stock_codes) * 100,
            "total_processing_time": total_time,
            "average_time_per_stock": total_time / len(stock_codes),
            "gpu0_stocks_count": len(gpu0_stocks),
            "gpu1_stocks_count": len(gpu1_stocks),
            "successful_results": successful_results,
            "failed_results": failed_results
        }
        
        logger.info(f"并发预测完成: {len(successful_results)}/{len(stock_codes)} 成功, 耗时: {total_time:.2f}秒")
        
        return summary
    
    async def predict_concurrent_batch(self, stock_codes: List[str], **kwargs) -> Dict[str, Any]:
        """并发预测 - 批量模式"""
        logger.info(f"开始并发预测 {len(stock_codes)} 只股票（批量模式）")
        start_time = time.time()
        
        # 分配股票到两个GPU
        gpu0_stocks, gpu1_stocks = self.split_stocks_for_gpus(stock_codes)
        
        async with aiohttp.ClientSession() as session:
            # 创建批量预测任务
            tasks = []
            
            if gpu0_stocks:
                task0 = self.predict_batch_on_service(session, self.gpu0_url, gpu0_stocks, **kwargs)
                tasks.append(task0)
            
            if gpu1_stocks:
                task1 = self.predict_batch_on_service(session, self.gpu1_url, gpu1_stocks, **kwargs)
                tasks.append(task1)
            
            # 并发执行批量任务
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_results = []
        total_successful = 0
        total_failed = 0
        
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"批量任务异常: {batch_result}")
                continue
            
            if batch_result.get("success", False) and "results" in batch_result:
                all_results.extend(batch_result["results"])
                total_successful += batch_result.get("successful_predictions", 0)
                total_failed += batch_result.get("failed_predictions", 0)
            else:
                logger.error(f"批量任务失败: {batch_result.get('error', '未知错误')}")
        
        total_time = time.time() - start_time
        
        summary = {
            "mode": "concurrent_batch",
            "total_stocks": len(stock_codes),
            "successful_predictions": total_successful,
            "failed_predictions": total_failed,
            "success_rate": total_successful / len(stock_codes) * 100 if stock_codes else 0,
            "total_processing_time": total_time,
            "average_time_per_stock": total_time / len(stock_codes) if stock_codes else 0,
            "gpu0_stocks_count": len(gpu0_stocks),
            "gpu1_stocks_count": len(gpu1_stocks),
            "batch_results": batch_results,
            "all_results": all_results
        }
        
        logger.info(f"批量并发预测完成: {total_successful}/{len(stock_codes)} 成功, 耗时: {total_time:.2f}秒")
        
        return summary
    
    def save_results_to_file(self, results: Dict[str, Any], filename: str = None):
        """保存预测结果到文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prediction_results_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            print(f"结果已保存到: {filename}")
        except Exception as e:
            print(f"保存结果失败: {e}")
    
    def save_results(self, results: List[Dict], filename: str = None):
        """保存预测结果到文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prediction_results_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            print(f"结果已保存到: {filename}")
        except Exception as e:
            print(f"保存结果失败: {e}")
    
    async def test_chunked_prediction(self, stock_code: str = "000001", 
                                     horizon_len: int = 30, 
                                     fixed_end_date: str = "20250630"):
        """测试分块预测功能"""
        print(f"\n=== 测试分块预测功能 ===")
        print(f"股票代码: {stock_code}")
        print(f"分块大小: {horizon_len}")
        print(f"固定训练结束日期: {fixed_end_date}")
        
        # 构建请求数据
        request_data = {
            "stock_code": stock_code,
            "stock_type": "stock",
            "time_step": 1,
            "years": 3,
            "horizon_len": horizon_len,
            "context_len": 512,
            "include_technical_indicators": True,
            "fixed_end_date": fixed_end_date
        }
        
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                # 发送分块预测请求
                async with session.post(
                    f"{self.gpu0_url}/predict/chunked",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5分钟超时
                ) as response:
                    result = await response.json()
                    end_time = time.time()
                    
                    if response.status == 200:
                        print(f"✅ 分块预测成功!")
                        print(f"总耗时: {end_time - start_time:.2f}秒")
                        print(f"总分块数: {result['total_chunks']}")
                        print(f"成功分块数: {result['successful_chunks']}")
                        print(f"失败分块数: {result['failed_chunks']}")
                        print(f"成功率: {result['summary']['success_rate']:.2f}%")
                        
                        if 'average_best_score' in result['summary']:
                            print(f"平均最佳评分: {result['summary']['average_best_score']:.4f}")
                        
                        # 保存结果
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"chunked_prediction_{stock_code}_{timestamp}.json"
                        self.save_results([result], filename)
                        
                        return result
                        
                    else:
                        print(f"❌ 分块预测失败: {response.status}")
                        print(f"错误信息: {await response.text()}")
                        return None
                
        except asyncio.TimeoutError:
            print("❌ 请求超时")
            return None
        except Exception as e:
            print(f"❌ 分块预测异常: {e}")
            return None

async def main():
    """主函数 - 演示并发预测"""
    # 初始化客户端
    client = TimesFMConcurrentClient()
    
    # 等待服务启动
    if not await client.wait_for_services():
        logger.error("服务未就绪，退出")
        return
    
    # 测试股票列表
    test_stocks = [
        "600398",  # 海澜之家
        "000001",  # 平安银行
        "000002",  # 万科A
        "000858",  # 五粮液
        "002415",  # 海康威视
        "600036",  # 招商银行
        "000858",  # 五粮液
        "002594"   # 比亚迪
    ]
    
    logger.info(f"开始测试，股票列表: {test_stocks}")
    
    # 测试1: 并发单个预测
    logger.info("\n=== 测试1: 并发单个预测 ===")
    individual_results = await client.predict_concurrent_individual(
        test_stocks,
        horizon_len=5,
        years=5,
        include_technical_indicators=True
    )
    
    # 保存单个预测结果
    client.save_results_to_file(individual_results, "individual_concurrent_results.json")
    
    # 等待一段时间
    await asyncio.sleep(5)
    
    # 测试2: 并发批量预测
    logger.info("\n=== 测试2: 并发批量预测 ===")
    batch_results = await client.predict_concurrent_batch(
        test_stocks,
        horizon_len=5,
        years=5,
        include_technical_indicators=True
    )
    
    # 保存批量预测结果
    client.save_results_to_file(batch_results, "batch_concurrent_results.json")
    
    # 测试3: 分块预测功能
    logger.info("\n=== 测试3: 分块预测功能 ===")
    chunked_result = await client.test_chunked_prediction(
        stock_code="000001",
        horizon_len=30,
        fixed_end_date="20250630"
    )
    if chunked_result:
        logger.info("✅ 分块预测成功")
    
    # 性能对比
    logger.info("\n=== 性能对比 ===")
    logger.info(f"单个并发模式: {individual_results['total_processing_time']:.2f}秒, 成功率: {individual_results['success_rate']:.1f}%")
    logger.info(f"批量并发模式: {batch_results['total_processing_time']:.2f}秒, 成功率: {batch_results['success_rate']:.1f}%")
    
    if individual_results['total_processing_time'] > 0 and batch_results['total_processing_time'] > 0:
        speedup = individual_results['total_processing_time'] / batch_results['total_processing_time']
        logger.info(f"批量模式相对单个模式加速比: {speedup:.2f}x")

if __name__ == "__main__":
    asyncio.run(main())