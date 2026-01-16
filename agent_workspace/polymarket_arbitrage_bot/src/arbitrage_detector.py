"""
套利检测器 - 检测Polymarket二元市场中的套利机会
基于公式 YES价格 + NO价格 < 1.00
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """市场数据类"""
    market_id: str
    market_name: str
    yes_price: float
    no_price: float
    liquidity: float
    expiry_date: datetime
    volume_24h: float
    created_at: datetime
    updated_at: datetime


@dataclass
class ArbitrageOpportunity:
    """套利机会类"""
    market_id: str
    market_name: str
    yes_price: float
    no_price: float
    total_cost: float
    profit: float
    profit_percentage: float
    annualized_return: float
    liquidity: float
    expiry_date: datetime
    days_to_expiry: int
    detected_at: datetime
    confidence_score: float


class ArbitrageDetector:
    """套利检测器"""
    
    def __init__(self, api_client=None, config: Optional[Dict] = None):
        """
        初始化套利检测器
        
        Args:
            api_client: API客户端
            config: 配置字典
        """
        self.api_client = api_client
        self.config = config or {}
        
        # 默认配置
        self.min_profit_threshold = self.config.get('min_profit_threshold', 0.005)  # 0.5%
        self.max_slippage = self.config.get('max_slippage', 0.001)  # 0.1%
        self.transaction_fee = self.config.get('transaction_fee', 0.002)  # 0.2%
        self.min_market_liquidity = self.config.get('min_market_liquidity', 10000)  # 10k USDC
        self.max_days_to_expiry = self.config.get('max_days_to_expiry', 365)
        self.min_days_to_expiry = self.config.get('min_days_to_expiry', 1)
        
        # 缓存
        self.market_cache = {}
        self.opportunity_cache = {}
        
        logger.info(f"ArbitrageDetector initialized with config: {self.config}")
    
    def calculate_arbitrage_opportunity(self, market_data: MarketData) -> Optional[ArbitrageOpportunity]:
        """
        计算单个市场的套利机会
        
        Args:
            market_data: 市场数据
            
        Returns:
            套利机会对象，如果没有机会则返回None
        """
        try:
            # 计算总成本
            total_cost = market_data.yes_price + market_data.no_price
            
            # 检查套利条件
            if total_cost >= 1.0:
                return None
            
            # 计算利润
            profit = 1.0 - total_cost
            
            # 计算利润百分比
            profit_percentage = (profit / total_cost) * 100 if total_cost > 0 else 0
            
            # 检查最小利润阈值
            if profit_percentage < (self.min_profit_threshold * 100):
                return None
            
            # 计算年化回报
            days_to_expiry = (market_data.expiry_date - datetime.now()).days
            if days_to_expiry > 0:
                annualized_return = ((1 + profit_percentage/100) ** (365/days_to_expiry) - 1) * 100
            else:
                annualized_return = 0
            
            # 检查市场流动性
            if market_data.liquidity < self.min_market_liquidity:
                return None
            
            # 检查到期时间
            if days_to_expiry > self.max_days_to_expiry or days_to_expiry < self.min_days_to_expiry:
                return None
            
            # 计算置信度分数
            confidence_score = self._calculate_confidence_score(
                profit_percentage, 
                market_data.liquidity,
                market_data.volume_24h,
                days_to_expiry
            )
            
            # 创建套利机会对象
            opportunity = ArbitrageOpportunity(
                market_id=market_data.market_id,
                market_name=market_data.market_name,
                yes_price=market_data.yes_price,
                no_price=market_data.no_price,
                total_cost=total_cost,
                profit=profit,
                profit_percentage=profit_percentage,
                annualized_return=annualized_return,
                liquidity=market_data.liquidity,
                expiry_date=market_data.expiry_date,
                days_to_expiry=days_to_expiry,
                detected_at=datetime.now(),
                confidence_score=confidence_score
            )
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error calculating arbitrage opportunity for market {market_data.market_id}: {e}")
            return None
    
    def _calculate_confidence_score(self, profit_percentage: float, liquidity: float, 
                                   volume_24h: float, days_to_expiry: int) -> float:
        """
        计算套利机会的置信度分数
        
        Args:
            profit_percentage: 利润百分比
            liquidity: 市场流动性
            volume_24h: 24小时交易量
            days_to_expiry: 到期天数
            
        Returns:
            置信度分数 (0-1)
        """
        # 利润分数 (0-1)
        profit_score = min(profit_percentage / 10, 1.0)  # 假设10%为最大利润
        
        # 流动性分数 (0-1)
        liquidity_score = min(liquidity / 100000, 1.0)  # 假设100k为高流动性
        
        # 交易量分数 (0-1)
        volume_score = min(volume_24h / 50000, 1.0)  # 假设50k为高交易量
        
        # 到期时间分数 (0-1)
        expiry_score = 1.0 if 7 <= days_to_expiry <= 90 else 0.5  # 7-90天为最佳
        
        # 加权平均
        weights = {
            'profit': 0.4,
            'liquidity': 0.3,
            'volume': 0.2,
            'expiry': 0.1
        }
        
        confidence = (
            profit_score * weights['profit'] +
            liquidity_score * weights['liquidity'] +
            volume_score * weights['volume'] +
            expiry_score * weights['expiry']
        )
        
        return round(confidence, 3)
    
    async def detect_opportunities(self, markets: List[MarketData]) -> List[ArbitrageOpportunity]:
        """
        检测多个市场的套利机会
        
        Args:
            markets: 市场数据列表
            
        Returns:
            套利机会列表
        """
        opportunities = []
        
        for market in markets:
            opportunity = self.calculate_arbitrage_opportunity(market)
            if opportunity:
                opportunities.append(opportunity)
        
        # 按利润百分比排序
        opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)
        
        return opportunities
    
    def filter_opportunities(self, opportunities: List[ArbitrageOpportunity], 
                           max_opportunities: int = 10) -> List[ArbitrageOpportunity]:
        """
        过滤套利机会
        
        Args:
            opportunities: 套利机会列表
            max_opportunities: 最大返回机会数
            
        Returns:
            过滤后的套利机会列表
        """
        # 过滤掉置信度低的
        filtered = [opp for opp in opportunities if opp.confidence_score >= 0.5]
        
        # 限制数量
        return filtered[:max_opportunities]
    
    def save_opportunities_to_file(self, opportunities: List[ArbitrageOpportunity], 
                                 filename: str = "data/opportunities.json"):
        """
        保存套利机会到文件
        
        Args:
            opportunities: 套利机会列表
            filename: 文件名
        """
        try:
            data = []
            for opp in opportunities:
                data.append({
                    'market_id': opp.market_id,
                    'market_name': opp.market_name,
                    'yes_price': opp.yes_price,
                    'no_price': opp.no_price,
                    'total_cost': opp.total_cost,
                    'profit': opp.profit,
                    'profit_percentage': opp.profit_percentage,
                    'annualized_return': opp.annualized_return,
                    'liquidity': opp.liquidity,
                    'expiry_date': opp.expiry_date.isoformat(),
                    'days_to_expiry': opp.days_to_expiry,
                    'detected_at': opp.detected_at.isoformat(),
                    'confidence_score': opp.confidence_score
                })
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(opportunities)} opportunities to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving opportunities to file: {e}")
    
    def load_opportunities_from_file(self, filename: str = "data/opportunities.json") -> List[ArbitrageOpportunity]:
        """
        从文件加载套利机会
        
        Args:
            filename: 文件名
            
        Returns:
            套利机会列表
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            opportunities = []
            for item in data:
                opportunity = ArbitrageOpportunity(
                    market_id=item['market_id'],
                    market_name=item['market_name'],
                    yes_price=item['yes_price'],
                    no_price=item['no_price'],
                    total_cost=item['total_cost'],
                    profit=item['profit'],
                    profit_percentage=item['profit_percentage'],
                    annualized_return=item['annualized_return'],
                    liquidity=item['liquidity'],
                    expiry_date=datetime.fromisoformat(item['expiry_date']),
                    days_to_expiry=item['days_to_expiry'],
                    detected_at=datetime.fromisoformat(item['detected_at']),
                    confidence_score=item['confidence_score']
                )
                opportunities.append(opportunity)
            
            logger.info(f"Loaded {len(opportunities)} opportunities from {filename}")
            return opportunities
            
        except FileNotFoundError:
            logger.warning(f"File {filename} not found")
            return []
        except Exception as e:
            logger.error(f"Error loading opportunities from file: {e}")
            return []
    
    def generate_report(self, opportunities: List[ArbitrageOpportunity]) -> str:
        """
        生成套利机会报告
        
        Args:
            opportunities: 套利机会列表
            
        Returns:
            报告字符串
        """
        if not opportunities:
            return "未发现套利机会"
        
        report_lines = []
        report_lines.append("=" * 50)
        report_lines.append("Polymarket 套利检测报告")
        report_lines.append("=" * 50)
        report_lines.append(f"检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"套利机会: {len(opportunities)}个")
        report_lines.append("")
        
        for i, opp in enumerate(opportunities, 1):
            report_lines.append(f"机会 #{i}:")
            report_lines.append(f"  市场: {opp.market_name}")
            report_lines.append(f"  YES价格: ${opp.yes_price:.4f}")
            report_lines.append(f"  NO价格: ${opp.no_price:.4f}")
            report_lines.append(f"  总成本: ${opp.total_cost:.4f}")
            report_lines.append(f"  利润: ${opp.profit:.4f} ({opp.profit_percentage:.2f}%)")
            report_lines.append(f"  年化回报: {opp.annualized_return:.2f}% ({opp.days_to_expiry}天到期)")
            report_lines.append(f"  流动性: ${opp.liquidity:,.0f}")
            report_lines.append(f"  置信度: {opp.confidence_score:.3f}")
            report_lines.append("")
        
        report_lines.append("=" * 50)
        
        return "\n".join(report_lines)