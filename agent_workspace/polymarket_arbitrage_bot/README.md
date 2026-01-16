# Polymarket 套利机器人

一个基于Python的Polymarket套利检测机器人，专门用于检测二元市场中的套利机会。

## 🎯 核心功能

- **实时套利检测**：监控Polymarket二元市场的价格
- **套利机会识别**：基于公式 `YES价格 + NO价格 < 1.00`
- **利润计算**：自动计算套利利润和回报率
- **风险控制**：内置手续费和滑点考虑
- **数据可视化**：提供套利机会的可视化报告

## 📊 套利原理

### 核心公式
```
套利条件：YES价格 + NO价格 < 1.00
利润 = 1.00 - (YES价格 + NO价格)
回报率 = 利润 / 总成本 × 100%
```

### 示例
```
YES价格：$0.45
NO价格：$0.50
总成本：$0.95
保证收益：$0.05（5.3%回报）
```

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置API密钥
```bash
cp config/config.example.yaml config/config.yaml
# 编辑config.yaml文件，添加您的API密钥
```

### 3. 运行套利检测
```bash
python src/main.py
```

### 4. 运行测试
```bash
pytest tests/
```

## 📁 项目结构

```
polymarket_arbitrage_bot/
├── src/
│   ├── __init__.py
│   ├── main.py              # 主程序入口
│   ├── arbitrage_detector.py # 套利检测核心逻辑
│   ├── polymarket_api.py    # Polymarket API接口
│   ├── calculator.py        # 利润计算器
│   └── visualizer.py        # 数据可视化
├── tests/
│   ├── __init__.py
│   ├── test_arbitrage_detector.py
│   └── test_calculator.py
├── config/
│   ├── config.example.yaml
│   └── config.yaml
├── data/
│   └── markets.json         # 市场数据缓存
├── logs/
│   └── arbitrage.log        # 日志文件
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🔧 核心模块

### 1. ArbitrageDetector
检测二元市场中的套利机会，支持：
- 实时价格监控
- 套利条件验证
- 机会过滤和排序

### 2. ProfitCalculator
计算套利利润和回报率，考虑：
- 交易手续费
- 滑点成本
- 最小利润阈值

### 3. PolymarketAPI
与Polymarket API交互，获取：
- 市场列表
- 实时价格
- 订单簿数据

### 4. DataVisualizer
生成可视化报告：
- 套利机会分布图
- 利润趋势图
- 市场热度图

## ⚙️ 配置说明

### 配置文件 (config/config.yaml)
```yaml
polymarket:
  api_base_url: "https://clob.polymarket.com"
  api_key: "your_api_key_here"
  api_secret: "your_api_secret_here"

arbitrage:
  min_profit_threshold: 0.005  # 最小利润阈值（0.5%）
  max_slippage: 0.001          # 最大滑点（0.1%）
  transaction_fee: 0.002       # 交易手续费（0.2%）
  check_interval: 5            # 检查间隔（秒）

logging:
  level: "INFO"
  file: "logs/arbitrage.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 📈 使用示例

### 基本使用
```python
from src.arbitrage_detector import ArbitrageDetector
from src.polymarket_api import PolymarketAPI

# 初始化API客户端
api = PolymarketAPI()

# 初始化套利检测器
detector = ArbitrageDetector(api)

# 检测套利机会
opportunities = detector.detect_arbitrage_opportunities()

# 打印结果
for opp in opportunities:
    print(f"市场: {opp['market_name']}")
    print(f"YES价格: ${opp['yes_price']:.4f}")
    print(f"NO价格: ${opp['no_price']:.4f}")
    print(f"总成本: ${opp['total_cost']:.4f}")
    print(f"利润: ${opp['profit']:.4f} ({opp['profit_percentage']:.2f}%)")
    print("-" * 50)
```

### 高级使用：实时监控
```python
from src.main import run_realtime_monitoring

# 运行实时监控
run_realtime_monitoring(
    check_interval=5,      # 每5秒检查一次
    min_profit=0.01,       # 最小利润1%
    max_opportunities=10   # 显示最多10个机会
)
```

## 🧪 测试

运行所有测试：
```bash
pytest tests/ -v
```

运行特定测试：
```bash
pytest tests/test_arbitrage_detector.py -v
pytest tests/test_calculator.py -v
```

## 📊 输出示例

```
===========================================
Polymarket 套利检测报告
===========================================
检测时间: 2024-01-15 10:30:25
总市场数: 150
套利机会: 3个

机会 #1:
市场: "美联储12月是否降息25bp?"
YES价格: $0.45
NO价格: $0.50
总成本: $0.95
利润: $0.05 (5.26%)
年化回报: 384% (30天到期)

机会 #2:
市场: "比特币年底是否超过10万美元?"
YES价格: $0.60
NO价格: $0.35
总成本: $0.95
利润: $0.05 (5.26%)
年化回报: 64% (30天到期)

机会 #3:
市场: "川普是否赢得2024大选?"
YES价格: $0.48
NO价格: $0.49
总成本: $0.97
利润: $0.03 (3.09%)
年化回报: 113% (10天到期)
===========================================
```

## ⚠️ 风险提示

1. **市场风险**：价格可能快速变化
2. **流动性风险**：大额交易可能影响价格
3. **执行风险**：套利机会可能稍纵即逝
4. **技术风险**：API故障或网络延迟
5. **监管风险**：不同地区法律限制

## 🔍 套利策略优化

### 1. 多市场扫描
同时监控多个市场，提高机会发现率

### 2. 动态阈值调整
根据市场波动性调整最小利润阈值

### 3. 智能过滤
过滤掉流动性差或即将到期的市场

### 4. 风险分散
分散投资多个套利机会，降低单一风险

## 📚 学习资源

1. [Polymarket官方文档](https://docs.polymarket.com)
2. [预测市场套利原理](https://arxiv.org/abs/2508.03474)
3. [Python量化交易教程](https://github.com/MaxW3n/polymarket-arbitrage-bot)

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件到: your-email@example.com

---

**免责声明**：本项目仅供学习和研究使用。实际交易存在风险，请谨慎决策。作者不对任何投资损失负责。