"""
利润计算器
用于计算套利利润、回报率、考虑手续费和滑点
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ProfitCalculation:
    """利润计算结果"""
    yes_price: float
    no_price: float
    total_cost: float
    gross_profit: float
    net_profit: float
    gross_return_percentage: float
    net_return_percentage: float
    annualized_return: float
    transaction_fee: float
    slippage_cost: float
    total_cost_with_fees: float
    effective_return: float


class ProfitCalculator:
    """利润计算器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化利润计算器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 默认配置
        self.transaction_fee_rate = self.config.get('transaction_fee', 0.002)  # 0.2%
        self.slippage_rate = self.config.get('max_slippage', 0.001)  # 0.1%
        self.min_profit_threshold = self.config.get('min_profit_threshold', 0.005)  # 0.5%
        
        logger.info(f"ProfitCalculator initialized with config: {self.config}")
    
    def calculate_profit(self, yes_price: float, no_price: float, 
                        investment_amount: float = 1000.0,
                        days_to_expiry: int = 30) -> ProfitCalculation:
        """
        计算套利利润
        
        Args:
            yes_price: YES价格
            no_price: NO价格
            investment_amount: 投资金额
            days_to_expiry: 到期天数
            
        Returns:
            利润计算结果
        """
        try:
            # 计算总成本
            total_cost = yes_price + no_price
            
            # 检查是否满足套利条件
            if total_cost >= 1.0:
                raise ValueError(f"总成本 {total_cost} >= 1.0，无套利机会")
            
            # 计算毛利润
            gross_profit = 1.0 - total_cost
            
            # 计算交易手续费
            transaction_fee = investment_amount * self.transaction_fee_rate * 2  # 两次交易
            
            # 计算滑点成本
            slippage_cost = investment_amount * self.slippage_rate * 2  # 两次交易
            
            # 计算总成本（含费用）
            total_cost_with_fees = total_cost + (transaction_fee + slippage_cost) / investment_amount
            
            # 计算净利润
            net_profit = gross_profit - (transaction_fee + slippage_cost) / investment_amount
            
            # 计算回报率
            gross_return_percentage = (gross_profit / total_cost) * 100 if total_cost > 0 else 0
            net_return_percentage = (net_profit / total_cost_with_fees) * 100 if total_cost_with_fees > 0 else 0
            
            # 计算年化回报
            if days_to_expiry > 0:
                annualized_return = ((1 + net_return_percentage/100) ** (365/days_to_expiry) - 1) * 100
            else:
                annualized_return = 0
            
            # 计算有效回报（考虑机会成本）
            effective_return = net_return_percentage
            
            # 创建计算结果对象
            result = ProfitCalculation(
                yes_price=yes_price,
                no_price=no_price,
                total_cost=total_cost,
                gross_profit=gross_profit,
                net_profit=net_profit,
                gross_return_percentage=gross_return_percentage,
                net_return_percentage=net_return_percentage,
                annualized_return=annualized_return,
                transaction_fee=transaction_fee,
                slippage_cost=slippage_cost,
                total_cost_with_fees=total_cost_with_fees,
                effective_return=effective_return
            )
            
            return result
            
        except Exception as e:
            logger.error(f"计算利润失败: {e}")
            raise
    
    def is_profitable(self, yes_price: float, no_price: float) -> bool:
        """
        检查是否有利润
        
        Args:
            yes_price: YES价格
            no_price: NO价格
            
        Returns:
            是否有利润
        """
        try:
            total_cost = yes_price + no_price
            
            if total_cost >= 1.0:
                return False
            
            # 计算毛利润
            gross_profit = 1.0 - total_cost
            gross_return = gross_profit / total_cost if total_cost > 0 else 0
            
            # 考虑手续费和滑点后的净回报
            net_return = gross_return - (self.transaction_fee_rate * 2 + self.slippage_rate * 2)
            
            return net_return >= self.min_profit_threshold
            
        except Exception as e:
            logger.error(f"检查利润失败: {e}")
            return False
    
    def calculate_optimal_investment(self, yes_price: float, no_price: float,
                                   available_capital: float = 10000.0,
                                   max_position_size: float = 0.1) -> float:
        """
        计算最优投资金额
        
        Args:
            yes_price: YES价格
            no_price: NO价格
            available_capital: 可用资本
            max_position_size: 最大仓位比例
            
        Returns:
            最优投资金额
        """
        try:
            # 计算最大投资金额
            max_investment = available_capital * max_position_size
            
            # 计算套利利润
            result = self.calculate_profit(yes_price, no_price, max_investment)
            
            # 如果净利润为负，返回0
            if result.net_profit <= 0:
                return 0.0
            
            # 计算风险调整后的投资金额
            # 基于夏普比率的概念（简化版）
            risk_adjusted_amount = max_investment * min(result.net_return_percentage / 10, 1.0)
            
            return min(risk_adjusted_amount, max_investment)
            
        except Exception as e:
            logger.error(f"计算最优投资金额失败: {e}")
            return 0.0
    
    def calculate_expected_value(self, yes_price: float, no_price: float,
                               investment_amount: float = 1000.0,
                               probability_estimate: float = 0.5) -> Dict[str, float]:
        """
        计算期望值
        
        Args:
            yes_price: YES价格
            no_price: NO价格
            investment_amount: 投资金额
            probability_estimate: 概率估计（0-1）
            
        Returns:
            期望值计算结果
        """
        try:
            # 计算套利利润
            result = self.calculate_profit(yes_price, no_price, investment_amount)
            
            # 计算期望值
            expected_profit = result.net_profit * investment_amount
            
            # 计算风险调整后的期望值
            risk_adjusted_value = expected_profit * probability_estimate
            
            return {
                'expected_profit': expected_profit,
                'risk_adjusted_value': risk_adjusted_value,
                'probability_estimate': probability_estimate,
                'net_return_percentage': result.net_return_percentage,
                'annualized_return': result.annualized_return
            }
            
        except Exception as e:
            logger.error(f"计算期望值失败: {e}")
            return {
                'expected_profit': 0.0,
                'risk_adjusted_value': 0.0,
                'probability_estimate': probability_estimate,
                'net_return_percentage': 0.0,
                'annualized_return': 0.0
            }
    
    def compare_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """
        比较多个套利机会
        
        Args:
            opportunities: 套利机会列表
            
        Returns:
            排序后的机会列表
        """
        try:
            scored_opportunities = []
            
            for opp in opportunities:
                try:
                    # 计算利润
                    result = self.calculate_profit(
                        opp['yes_price'],
                        opp['no_price'],
                        opp.get('investment_amount', 1000.0),
                        opp.get('days_to_expiry', 30)
                    )
                    
                    # 计算综合分数
                    score = self._calculate_opportunity_score(result, opp)
                    
                    # 添加分数到机会
                    scored_opp = opp.copy()
                    scored_opp['profit_calculation'] = result
                    scored_opp['score'] = score
                    scored_opportunities.append(scored_opp)
                    
                except Exception as e:
                    logger.warning(f"计算机会 {opp.get('market_id', 'unknown')} 失败: {e}")
                    continue
            
            # 按分数排序
            scored_opportunities.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return scored_opportunities
            
        except Exception as e:
            logger.error(f"比较机会失败: {e}")
            return []
    
    def _calculate_opportunity_score(self, result: ProfitCalculation, 
                                   opportunity: Dict) -> float:
        """
        计算机会分数
        
        Args:
            result: 利润计算结果
            opportunity: 机会数据
            
        Returns:
            机会分数 (0-100)
        """
        try:
            # 利润分数 (0-40)
            profit_score = min(result.net_return_percentage * 4, 40)
            
            # 年化回报分数 (0-30)
            annualized_score = min(result.annualized_return / 10, 30)
            
            # 流动性分数 (0-20)
            liquidity = opportunity.get('liquidity', 0)
            liquidity_score = min(liquidity / 5000, 20)
            
            # 交易量分数 (0-10)
            volume = opportunity.get('volume_24h', 0)
            volume_score = min(volume / 10000, 10)
            
            # 总分数
            total_score = profit_score + annualized_score + liquidity_score + volume_score
            
            return round(total_score, 2)
            
        except Exception as e:
            logger.error(f"计算机会分数失败: {e}")
            return 0.0


# 工具函数
def format_currency(amount: float) -> str:
    """格式化货币金额"""
    if amount >= 1000000:
        return f"${amount/1000000:.2f}M"
    elif amount >= 1000:
        return f"${amount/1000:.1f}K"
    else:
        return f"${amount:.2f}"


def format_percentage(percentage: float) -> str:
    """格式化百分比"""
    return f"{percentage:.2f}%"


def calculate_compound_return(initial_amount: float, return_rate: float, 
                            periods: int) -> float:
    """
    计算复利回报
    
    Args:
        initial_amount: 初始金额
        return_rate: 每期回报率
        periods: 期数
        
    Returns:
        最终金额
    """
    return initial_amount * ((1 + return_rate) ** periods)


if __name__ == "__main__":
    # 测试代码
    calculator = ProfitCalculator()
    
    # 测试套利机会
    test_cases = [
        (0.45, 0.50),  # 5% 利润
        (0.48, 0.49),  # 3% 利润
        (0.60, 0.35),  # 5% 利润
        (0.55, 0.40),  # 5% 利润
    ]
    
    print("利润计算器测试")
    print("=" * 50)
    
    for i, (yes_price, no_price) in enumerate(test_cases, 1):
        try:
            result = calculator.calculate_profit(yes_price, no_price)
            print(f"测试案例 {i}:")
            print(f"  YES价格: ${yes_price:.2f}")
            print(f"  NO价格: ${no_price:.2f}")
            print(f"  总成本: ${result.total_cost:.2f}")
            print(f"  毛利润: ${result.gross_profit:.2f} ({result.gross_return_percentage:.2f}%)")
            print(f"  净利润: ${result.net_profit:.2f} ({result.net_return_percentage:.2f}%)")
            print(f"  年化回报: {result.annualized_return:.2f}%")
            print(f"  是否有利可图: {calculator.is_profitable(yes_price, no_price)}")
            print("-" * 30)
        except Exception as e:
            print(f"测试案例 {i} 失败: {e}")