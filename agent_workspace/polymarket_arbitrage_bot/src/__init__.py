"""
Polymarket 套利机器人
基于公式 YES价格 + NO价格 < 1.00 检测套利机会
"""

__version__ = "1.0.0"
__author__ = "Polymarket Arbitrage Bot Team"
__email__ = "your-email@example.com"

from .arbitrage_detector import ArbitrageDetector
from .profit_calculator import ProfitCalculator
from .polymarket_api import PolymarketAPI
from .data_visualizer import DataVisualizer

__all__ = [
    "ArbitrageDetector",
    "ProfitCalculator", 
    "PolymarketAPI",
    "DataVisualizer",
]