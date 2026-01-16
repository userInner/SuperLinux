"""
Polymarket API客户端
用于获取市场数据、价格信息等
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import time
from dataclasses import dataclass

from .arbitrage_detector import MarketData

logger = logging.getLogger(__name__)


@dataclass
class OrderBook:
    """订单簿数据"""
    market_id: str
    bids: List[Dict[str, float]]  # [{price: 0.45, size: 1000}, ...]
    asks: List[Dict[str, float]]  # [{price: 0.46, size: 800}, ...]
    timestamp: datetime


@dataclass
class Trade:
    """交易数据"""
    market_id: str
    price: float
    size: float
    side: str  # 'buy' or 'sell'
    timestamp: datetime


class PolymarketAPIClient:
    """Polymarket API客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化API客户端
        
        Args:
            config: 配置字典
        """
        self.config = config.get('polymarket', {})
        self.api_base_url = self.config.get('api_base_url', 'https://clob.polymarket.com')
        self.api_key = self.config.get('api_key', '')
        self.api_secret = self.config.get('api_secret', '')
        self.timeout = self.config.get('timeout', 30)
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
        
        # 会话管理
        self.session = None
        self.last_request_time = 0
        self.request_delay = 0.1  # 请求延迟，避免速率限制
        
        logger.info(f"PolymarketAPIClient initialized with base URL: {self.api_base_url}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def connect(self):
        """连接API"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._get_headers()
            )
            logger.info("API客户端已连接")
    
    async def close(self):
        """关闭连接"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("API客户端已关闭")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            'User-Agent': 'PolymarketArbitrageBot/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        
        return headers
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 请求参数
            
        Returns:
            响应数据
        """
        url = f"{self.api_base_url}{endpoint}"
        
        # 速率限制
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        
        for attempt in range(self.retry_attempts):
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    self.last_request_time = time.time()
                    
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:  # 速率限制
                        retry_after = int(response.headers.get('Retry-After', 5))
                        logger.warning(f"速率限制，等待 {retry_after} 秒后重试")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        logger.error(f"请求失败: {response.status} - {await response.text()}")
                        if attempt < self.retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        return None
                        
            except aiohttp.ClientError as e:
                logger.error(f"网络错误: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                return None
            except Exception as e:
                logger.error(f"请求异常: {e}")
                return None
        
        return None
    
    async def get_markets(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取市场列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            市场列表
        """
        endpoint = f"/markets?limit={limit}&offset={offset}"
        data = await self._make_request('GET', endpoint)
        
        if data and 'markets' in data:
            return data['markets']
        return []
    
    async def get_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        获取市场详情
        
        Args:
            market_id: 市场ID
            
        Returns:
            市场详情
        """
        endpoint = f"/markets/{market_id}"
        return await self._make_request('GET', endpoint)
    
    async def get_order_book(self, market_id: str) -> Optional[OrderBook]:
        """
        获取订单簿
        
        Args:
            market_id: 市场ID
            
        Returns:
            订单簿数据
        """
        endpoint = f"/markets/{market_id}/orderbook"
        data = await self._make_request('GET', endpoint)
        
        if data:
            try:
                return OrderBook(
                    market_id=market_id,
                    bids=data.get('bids', []),
                    asks=data.get('asks', []),
                    timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat()))
                )
            except Exception as e:
                logger.error(f"解析订单簿失败: {e}")
        
        return None
    
    async def get_trades(self, market_id: str, limit: int = 100) -> List[Trade]:
        """
        获取交易历史
        
        Args:
            market_id: 市场ID
            limit: 返回数量限制
            
        Returns:
            交易列表
        """
        endpoint = f"/markets/{market_id}/trades?limit={limit}"
        data = await self._make_request('GET', endpoint)
        
        trades = []
        if data and 'trades' in data:
            for trade_data in data['trades']:
                try:
                    trade = Trade(
                        market_id=market_id,
                        price=trade_data.get('price', 0),
                        size=trade_data.get('size', 0),
                        side=trade_data.get('side', ''),
                        timestamp=datetime.fromisoformat(trade_data.get('timestamp', datetime.now().isoformat()))
                    )
                    trades.append(trade)
                except Exception as e:
                    logger.error(f"解析交易数据失败: {e}")
        
        return trades
    
    async def get_market_prices(self, market_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """
        获取多个市场的价格
        
        Args:
            market_ids: 市场ID列表
            
        Returns:
            市场价格字典 {market_id: {yes_price: 0.45, no_price: 0.55}}
        """
        prices = {}
        
        for market_id in market_ids:
            order_book = await self.get_order_book(market_id)
            if order_book:
                # 计算最佳买卖价格
                best_bid = max(order_book.bids, key=lambda x: x['price']) if order_book.bids else None
                best_ask = min(order_book.asks, key=lambda x: x['price']) if order_book.asks else None
                
                if best_bid and best_ask:
                    # 使用中间价作为估计价格
                    yes_price = (best_bid['price'] + best_ask['price']) / 2
                    no_price = 1.0 - yes_price
                    
                    prices[market_id] = {
                        'yes_price': yes_price,
                        'no_price': no_price,
                        'bid_price': best_bid['price'],
                        'ask_price': best_ask['price'],
                        'bid_size': best_bid['size'],
                        'ask_size': best_ask['size']
                    }
        
        return prices
    
    async def get_all_market_data(self) -> List[MarketData]:
        """
        获取所有市场数据
        
        Returns:
            市场数据列表
        """
        markets = await self.get_markets(limit=200)
        market_data_list = []
        
        for market in markets:
            try:
                market_id = market.get('id', '')
                market_name = market.get('question', '')
                liquidity = market.get('liquidity', 0)
                volume_24h = market.get('volume_24h', 0)
                
                # 获取价格
                prices = await self.get_market_prices([market_id])
                if market_id in prices:
                    price_data = prices[market_id]
                    
                    # 解析到期时间
                    expiry_str = market.get('expiry_date', '')
                    try:
                        expiry_date = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                    except:
                        expiry_date = datetime.now() + timedelta(days=30)
                    
                    market_data = MarketData(
                        market_id=market_id,
                        market_name=market_name,
                        yes_price=price_data['yes_price'],
                        no_price=price_data['no_price'],
                        liquidity=liquidity,
                        expiry_date=expiry_date,
                        volume_24h=volume_24h,
                        created_at=datetime.fromisoformat(market.get('created_at', datetime.now().isoformat())),
                        updated_at=datetime.fromisoformat(market.get('updated_at', datetime.now().isoformat()))
                    )
                    
                    market_data_list.append(market_data)
                    
            except Exception as e:
                logger.error(f"处理市场数据失败 {market.get('id', 'unknown')}: {e}")
                continue
        
        return market_data_list
    
    async def place_order(self, market_id: str, side: str, price: float, size: float) -> Optional[Dict[str, Any]]:
        """
        下单
        
        Args:
            market_id: 市场ID
            side: 买卖方向 ('buy' or 'sell')
            price: 价格
            size: 数量
            
        Returns:
            订单响应
        """
        if not self.api_key or not self.api_secret:
            logger.error("API密钥未配置，无法下单")
            return None
        
        endpoint = "/orders"
        payload = {
            'market_id': market_id,
            'side': side,
            'price': price,
            'size': size,
            'type': 'limit',
            'time_in_force': 'gtc'
        }
        
        # 这里需要添加签名逻辑
        # 实际实现需要根据Polymarket API文档进行签名
        
        logger.info(f"下单: {market_id} {side} {price} {size}")
        return await self._make_request('POST', endpoint, json=payload)
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            是否成功
        """
        endpoint = f"/orders/{order_id}"
        response = await self._make_request('DELETE', endpoint)
        return response is not None
    
    async def get_account_balance(self) -> Optional[Dict[str, float]]:
        """
        获取账户余额
        
        Returns:
            余额信息
        """
        endpoint = "/account/balance"
        return await self._make_request('GET', endpoint)
    
    async def get_open_orders(self, market_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取未成交订单
        
        Args:
            market_id: 可选的市场ID
            
        Returns:
            未成交订单列表
        """
        endpoint = "/orders/open"
        if market_id:
            endpoint += f"?market_id={market_id}"
        
        data = await self._make_request('GET', endpoint)
        if data and 'orders' in data:
            return data['orders']
        return []
    
    async def get_order_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取订单历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            订单历史
        """
        endpoint = f"/orders/history?limit={limit}"
        data = await self._make_request('GET', endpoint)
        
        if data and 'orders' in data:
            return data['orders']
        return []


class MockAPIClient(PolymarketAPIClient):
    """模拟API客户端，用于测试"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mock_data = self._generate_mock_data()
    
    def _generate_mock_data(self) -> Dict[str, Any]:
        """生成模拟数据"""
        import random
        from datetime import datetime, timedelta
        
        mock_markets = []
        for i in range(20):
            yes_price = round(random.uniform(0.4, 0.6), 3)
            no_price = round(1.0 - yes_price, 3)
            
            # 随机创建套利机会
            if random.random() < 0.3:  # 30%的概率创建套利机会
                adjustment = random.uniform(-0.02, 0.02)
                yes_price = round(yes_price + adjustment, 3)
                no_price = round(1.0 - yes_price, 3)
            
            market = {
                'id': f'market_{i}',
                'question': f'测试市场 {i} - 某事件是否会发生',
                'liquidity': random.uniform(5000, 50000),
                'volume_24h': random.uniform(1000, 20000),
                'expiry_date': (datetime.now() + timedelta(days=random.randint(1, 90))).isoformat(),
                'created_at': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                'updated_at': datetime.now().isoformat(),
                'yes_price': yes_price,
                'no_price': no_price
            }
            mock_markets.append(market)
        
        return {'markets': mock_markets}
    
    async def get_markets(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取模拟市场数据"""
        await asyncio.sleep(0.1)  # 模拟网络延迟
        return self.mock_data['markets'][offset:offset+limit]
    
    async def get_market_prices(self, market_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """获取模拟价格数据"""
        await asyncio.sleep(0.05)
        
        prices = {}
        for market_id in market_ids:
            for market in self.mock_data['markets']:
                if market['id'] == market_id:
                    prices[market_id] = {
                        'yes_price': market['yes_price'],
                        'no_price': market['no_price'],
                        'bid_price': market['yes_price'] - 0.001,
                        'ask_price': market['yes_price'] + 0.001,
                        'bid_size': 1000,
                        'ask_size': 1000
                    }
                    break
        
        return prices