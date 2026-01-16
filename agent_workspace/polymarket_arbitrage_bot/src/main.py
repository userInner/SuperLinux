#!/usr/bin/env python3
"""
Polymarket套利机器人主程序
"""

import asyncio
import logging
import sys
import os
import yaml
from datetime import datetime
from typing import Dict, List, Optional
import argparse

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity, MarketData
from src.api_client import PolymarketAPIClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/arbitrage.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml") -> Dict:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"配置文件加载成功: {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"配置文件不存在: {config_path}")
        logger.info("请复制 config/config.example.yaml 为 config/config.yaml 并配置")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"配置文件格式错误: {e}")
        sys.exit(1)


async def fetch_market_data(api_client: PolymarketAPIClient) -> List[MarketData]:
    """获取市场数据"""
    try:
        logger.info("开始获取市场数据...")
        
        # 这里应该调用实际的API获取市场数据
        # 为了演示，我们创建一些模拟数据
        markets = []
        
        # 模拟一些市场数据
        sample_markets = [
            {
                "market_id": "market_001",
                "market_name": "美联储12月是否降息25bp?",
                "yes_price": 0.45,
                "no_price": 0.50,
                "liquidity": 50000,
                "expiry_date": datetime(2024, 12, 31),
                "volume_24h": 25000,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "market_id": "market_002",
                "market_name": "比特币年底是否超过10万美元?",
                "yes_price": 0.60,
                "no_price": 0.35,
                "liquidity": 100000,
                "expiry_date": datetime(2024, 12, 31),
                "volume_24h": 50000,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "market_id": "market_003",
                "market_name": "川普是否赢得2024大选?",
                "yes_price": 0.48,
                "no_price": 0.49,
                "liquidity": 75000,
                "expiry_date": datetime(2024, 11, 5),
                "volume_24h": 30000,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "market_id": "market_004",
                "market_name": "以太坊年底是否超过5000美元?",
                "yes_price": 0.55,
                "no_price": 0.40,
                "liquidity": 30000,
                "expiry_date": datetime(2024, 12, 31),
                "volume_24h": 15000,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "market_id": "market_005",
                "market_name": "标普500年底是否超过6000点?",
                "yes_price": 0.30,
                "no_price": 0.65,
                "liquidity": 80000,
                "expiry_date": datetime(2024, 12, 31),
                "volume_24h": 40000,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        
        for market_data in sample_markets:
            market = MarketData(**market_data)
            markets.append(market)
        
        logger.info(f"获取到 {len(markets)} 个市场数据")
        return markets
        
    except Exception as e:
        logger.error(f"获取市场数据失败: {e}")
        return []


async def run_single_scan(config: Dict):
    """运行单次套利扫描"""
    try:
        # 初始化API客户端
        api_client = PolymarketAPIClient(config)
        
        # 初始化套利检测器
        detector_config = config.get('arbitrage', {})
        detector = ArbitrageDetector(api_client, detector_config)
        
        # 获取市场数据
        markets = await fetch_market_data(api_client)
        
        if not markets:
            logger.warning("未获取到市场数据")
            return
        
        # 检测套利机会
        opportunities = await detector.detect_opportunities(markets)
        
        # 过滤机会
        filtered_opportunities = detector.filter_opportunities(opportunities)
        
        # 生成报告
        report = detector.generate_report(filtered_opportunities)
        print(report)
        
        # 保存机会到文件
        detector.save_opportunities_to_file(filtered_opportunities)
        
        logger.info(f"扫描完成，发现 {len(filtered_opportunities)} 个套利机会")
        
    except Exception as e:
        logger.error(f"套利扫描失败: {e}")


async def run_realtime_monitoring(config: Dict, check_interval: int = 5):
    """运行实时监控"""
    logger.info(f"开始实时监控，检查间隔: {check_interval}秒")
    
    try:
        # 初始化API客户端
        api_client = PolymarketAPIClient(config)
        
        # 初始化套利检测器
        detector_config = config.get('arbitrage', {})
        detector = ArbitrageDetector(api_client, detector_config)
        
        scan_count = 0
        
        while True:
            scan_count += 1
            logger.info(f"开始第 {scan_count} 次扫描...")
            
            try:
                # 获取市场数据
                markets = await fetch_market_data(api_client)
                
                if markets:
                    # 检测套利机会
                    opportunities = await detector.detect_opportunities(markets)
                    
                    # 过滤机会
                    filtered_opportunities = detector.filter_opportunities(opportunities)
                    
                    if filtered_opportunities:
                        # 生成报告
                        report = detector.generate_report(filtered_opportunities)
                        print(report)
                        
                        # 保存机会到文件
                        detector.save_opportunities_to_file(filtered_opportunities)
                    
                    logger.info(f"第 {scan_count} 次扫描完成，发现 {len(filtered_opportunities)} 个套利机会")
                else:
                    logger.warning(f"第 {scan_count} 次扫描未获取到市场数据")
                
            except Exception as e:
                logger.error(f"第 {scan_count} 次扫描失败: {e}")
            
            # 等待下一次扫描
            await asyncio.sleep(check_interval)
            
    except KeyboardInterrupt:
        logger.info("实时监控已停止")
    except Exception as e:
        logger.error(f"实时监控失败: {e}")


def print_opportunity_details(opportunity: ArbitrageOpportunity):
    """打印套利机会详情"""
    print(f"市场: {opportunity.market_name}")
    print(f"市场ID: {opportunity.market_id}")
    print(f"YES价格: ${opportunity.yes_price:.4f}")
    print(f"NO价格: ${opportunity.no_price:.4f}")
    print(f"总成本: ${opportunity.total_cost:.4f}")
    print(f"利润: ${opportunity.profit:.4f}")
    print(f"利润百分比: {opportunity.profit_percentage:.2f}%")
    print(f"年化回报: {opportunity.annualized_return:.2f}%")
    print(f"流动性: ${opportunity.liquidity:,.0f}")
    print(f"到期天数: {opportunity.days_to_expiry}天")
    print(f"置信度: {opportunity.confidence_score:.3f}")
    print("-" * 50)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Polymarket套利机器人')
    parser.add_argument('--mode', choices=['single', 'realtime'], default='single',
                       help='运行模式: single(单次扫描) 或 realtime(实时监控)')
    parser.add_argument('--config', default='config/config.yaml',
                       help='配置文件路径')
    parser.add_argument('--interval', type=int, default=5,
                       help='实时监控的检查间隔(秒)')
    parser.add_argument('--min-profit', type=float, default=0.005,
                       help='最小利润阈值(默认0.5%%)')
    parser.add_argument('--max-opportunities', type=int, default=10,
                       help='最大显示机会数')
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 更新配置参数
    if 'arbitrage' not in config:
        config['arbitrage'] = {}
    
    config['arbitrage']['min_profit_threshold'] = args.min_profit
    config['arbitrage']['check_interval'] = args.interval
    
    logger.info(f"启动Polymarket套利机器人，模式: {args.mode}")
    
    if args.mode == 'single':
        # 运行单次扫描
        asyncio.run(run_single_scan(config))
    elif args.mode == 'realtime':
        # 运行实时监控
        asyncio.run(run_realtime_monitoring(config, args.interval))
    else:
        logger.error(f"未知模式: {args.mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()