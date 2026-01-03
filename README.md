# 波动率交易分析系统 v2.0

基于 GEX/VRP/Term Structure 等多维度信号的波动率交易决策系统。

## 📑 目录

- [快速开始](#-快速开始)
- [核心功能](#-核心功能)
- [工作流程](#-工作流程)
- [命令参考](#-命令参考)
- [缓存结构](#-缓存结构)
- [环境变量配置](#-环境变量配置)
- [输入数据格式](#-输入数据格式)
- [项目结构](#-项目结构)
- [代码调用](#-代码调用)
- [核心概念](#-核心概念)
- [输出示例](#-输出示例)

---

## 🚀 快速开始

### 安装

```bash
# 1. 解压
unzip vol_analyzer_v2.zip
cd vol_analyzer_v2

# 2. 运行安装脚本 (自动配置 PATH)
chmod +x setup.sh && ./setup.sh
source ~/.bashrc  # 或 source ~/.zshrc

# 3. 安装依赖
pip install numpy scipy pyyaml requests
```

### 基本使用

```bash
# 生成 gexbot 命令
cmd AAPL                     # 基本用法
cmd AAPL -v 18.5             # 带 VIX 参数
cmd AAPL -t 2026-01-03       # 指定日期

# 完整分析
create AAPL                  # 单个分析
create AAPL NVDA META        # 批量分析
create AAPL -e earnings      # 带事件
create AAPL -i AAPL_i_2026-01-03.json   # 指定输入文件
create AAPL -c AAPL_o_2026-01-03.json   # 指定缓存文件

# 快速更新
update AAPL                  # 更新评分
update AAPL -i AAPL.json     # 指定输入文件
```

---

## 🎯 核心功能

| 功能 | 说明 |
|------|------|
| **多维度信号分析** | VRP、GEX、VEX、Term Structure、Skew、流动性等 |
| **智能决策引擎** | 基于加权评分的 Long/Short/Hold 决策 |
| **策略生成** | 根据市场环境推荐具体期权策略 |
| **Edge 估计** | 蒙特卡洛模拟计算期望收益 |
| **缓存管理** | 自动保存分析过程数据 |
| **VA 服务集成** | 自动获取 IVR/IV30/HV20 等市场参数 |

---

## 📋 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                      完整工作流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. cmd AAPL -v 18.5           生成命令 + 创建缓存           │
│         │                                                   │
│         ▼                                                   │
│  2. 执行 gexbot 命令            在 Discord 获取数据          │
│         │                                                   │
│         ▼                                                   │
│  3. 填充 data/input/AAPL.json   整理数据到 JSON 文件         │
│         │                                                   │
│         ▼                                                   │
│  4. create AAPL                 运行完整分析流程             │
│         │                                                   │
│         ├── Step 1: 加载数据                                │
│         ├── Step 2: 校验字段                                │
│         ├── Step 3: 计算特征 (VRP/GEX/Term/Skew...)         │
│         ├── Step 4: 计算评分 (Long Score / Short Score)     │
│         ├── Step 5: 生成决策 (Long/Short/Hold)              │
│         ├── Step 6: 生成策略                                │
│         └── Step 7: 估计 Edge                               │
│         │                                                   │
│         ▼                                                   │
│  5. 查看结果                    缓存在 data/output/          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 快速更新流程

```bash
# 当市场数据变化，只需更新评分
update AAPL
```

---

## 📖 命令参考

### cmd - 生成 gexbot 命令

```bash
cmd SYMBOL [OPTIONS]
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `SYMBOL` | 股票代码 (必填) | `cmd AAPL` |
| `-v, --vix` | VIX 指数 | `cmd AAPL -v 18.5` |
| `-t, --datetime` | 日期 (YYYY-MM-DD) | `cmd AAPL -t 2026-01-03` |
| `-e, --event` | 事件类型 | `cmd AAPL -e earnings` |

**输出示例：**
```
📋 AAPL - gexbot 命令清单:
----------------------------------------
  !trigger AAPL 98
  !gexr AAPL 15 98
  !vexn AAPL 15 190 *
  !surface AAPL ivmid 98
  !surface AAPL spread atm 98
  !skew AAPL ivmid atm 30
----------------------------------------
```

### create - 完整分析

```bash
create SYMBOL [SYMBOL2 ...] [OPTIONS]
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `SYMBOL` | 股票代码 (支持多个) | `create AAPL NVDA` |
| `-i, --input` | 输入文件 | `create AAPL -i AAPL_i_2026-01-03.json` |
| `-c, --cache` | 缓存文件 | `create AAPL -c AAPL_o_2026-01-03.json` |
| `-e, --event` | 事件类型 | `create AAPL -e earnings` |
| `-t, --datetime` | 日期 | `create AAPL -t 2026-01-03` |
| `--skip-edge` | 跳过 Edge 计算 | `create AAPL --skip-edge` |
| `--data-dir` | 数据目录 | `--data-dir ./mydata` |
| `--output-dir` | 输出目录 | `--output-dir ./results` |
| `--iv` | 手动指定 IV | `--iv 0.35` |
| `--hv` | 手动指定 HV | `--hv 0.30` |

**文件路径省略规则：**
- `-i` 可省略 `data/input/` 前缀
- `-c` 可省略 `data/output/SYMBOL/DATE/` 前缀

```bash
# 以下两种写法等效
create TSLA -i TSLA_i_2026-01-03.json
create TSLA -i data/input/TSLA_i_2026-01-03.json

# 以下两种写法等效
create TSLA -c TSLA_o_2026-01-03.json
create TSLA -c data/output/TSLA/2026-01-03/TSLA_o_2026-01-03.json
```

**事件类型：**
- `earnings` - 财报事件
- `fomc` - 美联储会议
- `opex` - 期权到期
- `none` - 无事件 (默认)

### update - 快速更新

```bash
update SYMBOL [OPTIONS]
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `SYMBOL` | 股票代码 | `update AAPL` |
| `-i, --input` | 输入文件 | `update AAPL -i AAPL.json` |
| `-c, --cache` | 缓存文件 | `update AAPL -c AAPL_o_2026-01-03.json` |

仅重新计算评分，跳过策略生成和 Edge 计算。

---

## 📦 缓存结构

### 目录结构

```
data/output/
└── {SYMBOL}/
    └── {DATE}/
        └── {SYMBOL}_o_{DATE}.json
```

**示例：** `data/output/AAPL/2026-01-03/AAPL_o_2026-01-03.json`

### 缓存文件格式

```json
{
  "symbol": "AAPL",
  "date": "2026-01-03",
  "tag": "Meso",
  "created_at": "2026-01-03T14:22:28",
  "updated_at": "2026-01-03T14:35:42",
  
  "market_params": {
    "vix": 18.5,
    "ivr": 27.0,
    "iv30": 36.1,
    "hv20": 30.8,
    "vrp": 0.172,
    "iv_path": "Rising",
    "updated_at": "2026-01-03T14:22:28"
  },
  
  "source_target": {
    "step3_features": {
      "vrp_selected": 5.5,
      "vrp_regime": "short_bias",
      "term_slope": 2.0,
      "term_regime": "flat",
      "net_gex_regime": "positive",
      "skew_regime": "balanced",
      "liquidity_score": 70.0
    },
    "step4_scores": {
      "long_vol_score": -0.13,
      "short_vol_score": 0.21,
      "dominant_direction": "short",
      "confidence_pct": 11.45
    },
    "step5_decision": {
      "decision": "hold",
      "confidence": "low",
      "probability": {
        "p_long": 0.25,
        "p_short": 0.25,
        "p_hold": 0.50
      }
    },
    "step6_strategy": {
      "name": "Calendar Spread",
      "risk_profile": "conservative",
      "dte_optimal": 45
    },
    "step7_edge": {
      "win_rate": 0.52,
      "reward_risk": 1.8,
      "expected_value": 15.50,
      "is_profitable": true
    },
    "step8_report": {
      "decision": "hold",
      "confidence": "low",
      "strategy": "Calendar Spread",
      "data_quality": 100.0
    }
  }
}
```

---

## 🔧 环境变量配置

复制 `.env.example` 为 `.env` 可自定义策略参数：

```bash
cp .env.example .env
vim .env  # 编辑配置
```

### 完整配置项

#### 蒙特卡洛模拟

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MONTE_CARLO_SIMULATIONS` | 10000 | 模拟次数 |
| `RISK_FREE_RATE` | 0.05 | 无风险利率 |

#### 概率门槛

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PROB_LONG_L1_0` | 0.55 | L≥1.0 时概率下限 |
| `PROB_LONG_L1_5` | 0.60 | L≥1.5 时概率下限 |
| `PROB_LONG_L2_0` | 0.65 | L≥2.0 时概率下限 |

#### 评分权重

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEIGHT_VRP_LONG` | 0.25 | VRP 做多权重 |
| `WEIGHT_GEX_LONG` | 0.18 | GEX 做多权重 |
| `WEIGHT_VEX_LONG` | 0.18 | VEX 做多权重 |
| `WEIGHT_VRP_SHORT` | 0.30 | VRP 做空权重 |
| `WEIGHT_GEX_SHORT` | 0.12 | GEX 做空权重 |
| `WEIGHT_CARRY_SHORT` | 0.18 | Carry 做空权重 |

#### 决策门槛

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DECISION_THRESHOLD_LONG` | 1.0 | 做多分数门槛 |
| `DECISION_THRESHOLD_SHORT` | 1.0 | 做空分数门槛 |
| `PROB_THRESHOLD` | 0.55 | 概率门槛 |

#### Edge 门槛

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EDGE_EV_THRESHOLD` | 0 | 期望值门槛 |
| `EDGE_RR_THRESHOLD` | 1.5 | 盈亏比门槛 |

#### 技术指标

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TRIGGER_NEUTRAL_PCT` | 0.002 | Vol Trigger 中性阈值 (±0.2%) |
| `GAMMA_WALL_PROX_THRESHOLD` | 0.005 | Gamma Wall 接近阈值 (0.5%) |
| `RIM_ACTIVE_THRESHOLD` | 0.6 | RIM 有效阈值 |
| `RIM_WEAK_THRESHOLD` | 0.4 | RIM 弱势阈值 |

#### 日志

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LOG_LEVEL` | INFO | 日志级别 |
| `LOG_FILE` | vol_quant.log | 日志文件 |

---

## 📊 输入数据格式

### Schema v2.0 (嵌套结构)

`data/input/{SYMBOL}.json`:

```json
{
  "_schema_version": "2.0",
  "symbol": "AAPL",
  "timestamp": "2026-01-03 10:30:00",
  "spot": 185.50,
  
  "core_fields": {
    "gamma_regime": {
      "vol_trigger": 184.00,
      "net_gex_sign": "positive",
      "total_net_gex": 850000000
    },
    "key_levels": {
      "gamma_wall": 185.00,
      "gamma_wall_2": 190.00,
      "call_wall": 190.00,
      "put_wall": 180.00,
      "max_pain": 185.00
    },
    "iv_hv": {
      "iv_atm": 28.5,
      "iv_front": 29.0,
      "iv_back": 27.0,
      "iv_event_w": 32.0,
      "hv10": 25.0,
      "hv20": 23.0,
      "hv60": 22.0
    },
    "structure": {
      "vex_net": -0.15,
      "vanna_atm": 0.02,
      "term_slope": 2.0,
      "put_skew_25": 3.5,
      "call_skew_25": -1.0,
      "spread_atm": 0.03,
      "pcr_ratio": 0.85
    }
  },
  
  "enhanced": {
    "vvix": 18.5,
    "vix9d": 16.0,
    "vix": 15.5
  }
}
```

### 字段说明

#### 核心字段 (必填)

| 字段 | 说明 | 范围 |
|------|------|------|
| `spot` | 现价 | 0.01 - 100000 |
| `vol_trigger` | 波动率触发线 | 0.01 - 100000 |
| `gamma_wall` | Gamma 墙 | 0.01 - 100000 |
| `iv_atm` | ATM 隐含波动率 (%) | 1 - 500 |
| `hv20` | 20日历史波动率 (%) | 1 - 500 |

#### 重要字段 (建议填写)

| 字段 | 说明 |
|------|------|
| `call_wall` / `put_wall` | Call/Put 墙 |
| `iv_front` / `iv_back` | 前/后月 IV |
| `vex_net` | VEX 净值 |
| `hv10` / `hv60` | 10/60日 HV |

#### 可选字段

| 字段 | 说明 |
|------|------|
| `vanna_atm` | ATM Vanna |
| `put_skew_25` / `call_skew_25` | 25 Delta Skew |
| `spread_atm` | ATM 价差 |
| `vvix` / `vix9d` / `vix` | VIX 相关 |

---

## 📁 项目结构

```
vol_analyzer_v2/
├── cmd                      # 生成命令脚本
├── create                   # 完整分析脚本
├── update                   # 快速更新脚本
├── main.py                  # CLI 入口
├── setup.sh                 # 安装脚本
├── .env.example             # 环境变量模板
│
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── types.py             # 类型定义 (枚举、数据类)
│   ├── constants.py         # 常量配置 (支持 .env 覆盖)
│   └── exceptions.py        # 自定义异常
│
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── loader.py            # 数据加载器
│   ├── transformer.py       # 格式转换 (嵌套↔扁平)
│   ├── validator.py         # 字段校验
│   ├── cache.py             # 缓存管理器
│   └── va_client.py         # VA API 客户端
│
├── analysis/                # 分析计算
│   ├── __init__.py
│   ├── features/            # 特征计算
│   │   ├── vrp.py           # VRP (波动率风险溢价)
│   │   ├── gex.py           # GEX (Gamma 暴露)
│   │   ├── term_structure.py # 期限结构
│   │   ├── skew.py          # Skew 分析
│   │   └── liquidity.py     # 流动性评分
│   ├── scoring/             # 评分系统
│   │   └── scorer.py        # 信号计算器
│   └── monte_carlo/         # 蒙特卡洛模拟
│       └── simulator.py
│
├── strategy/                # 策略模块
│   ├── __init__.py
│   ├── decision.py          # 决策引擎
│   └── generator.py         # 策略生成器
│
├── pipeline/                # 流程编排
│   ├── __init__.py
│   └── orchestrator.py      # Pipeline 编排器
│
├── config/prompts/          # Prompt 配置
│   ├── field_schema.yaml
│   ├── step5_decision.yaml
│   ├── step6_strategy.yaml
│   └── step8_report.yaml
│
└── data/
    ├── input/               # 输入数据
    │   ├── AAPL.json
    │   ├── NVDA.json
    │   └── _TEMPLATE.json
    └── output/              # 缓存输出
```

---

## 🔧 代码调用

### 基本使用

```python
from pipeline import create_pipeline

# 创建 pipeline
pipeline = create_pipeline()

# 运行分析
ctx = pipeline.run("AAPL", skip_edge=True)

# 访问结果
print(ctx.features.vrp_selected)      # VRP 值
print(ctx.features.vrp_regime)        # VRP 状态
print(ctx.scores.long_vol_score)      # 做多评分
print(ctx.scores.short_vol_score)     # 做空评分
print(ctx.decision.decision)          # 决策结果
print(ctx.strategy.name)              # 策略名称
```

### 使用缓存

```python
from utils.cache import get_cache_manager

cache_manager = get_cache_manager()

# 加载缓存
cache = cache_manager.load_cache("AAPL", "2026-01-03")

# 创建/更新缓存
cache_manager.create_initial_cache("AAPL", "2026-01-03", market_params)
cache_manager.update_step("AAPL", "2026-01-03", "step4_scores", scores_data)

# 列出缓存
symbols = cache_manager.list_cached_symbols()
dates = cache_manager.list_cached_dates("AAPL")
```

### 使用 VA 客户端

```python
from utils.va_client import VAClient, fetch_market_params

# 方式 1: 使用便捷函数
params = fetch_market_params("AAPL", vix=18.5)

# 方式 2: 使用客户端类
client = VAClient(base_url="http://localhost:8668")
params = client.get_params("AAPL", vix=18.5, date="2026-01-03")

# 批量获取
results = client.get_params_batch(["AAPL", "NVDA", "META"], vix=18.5)
```

### 单独计算特征

```python
from analysis.features import (
    calculate_vrp,
    calculate_gex_features,
    calculate_term_structure,
    calculate_skew_features,
    calculate_all_features
)

# 计算单个特征
vrp, regime = calculate_vrp(iv_atm=28.5, hv20=23.0)

# 计算所有特征
features = calculate_all_features(market_data)
```

### 添加 Pipeline 钩子

```python
def log_progress(stage, ctx):
    print(f"Starting: {stage.value}")

def handle_error(stage, error, ctx):
    print(f"Error at {stage.value}: {error}")

pipeline.add_hook("before_stage", log_progress)
pipeline.add_hook("on_error", handle_error)
```

---

## 📚 核心概念

### VRP (Volatility Risk Premium)

波动率风险溢价 = (IV - HV) / HV

| VRP | 状态 | 信号 |
|-----|------|------|
| < -3% | `long_bias` | 做多波动率 |
| -3% ~ 3% | `neutral` | 中性 |
| > 3% | `short_bias` | 做空波动率 |

### GEX (Gamma Exposure)

| 状态 | 说明 | 市场影响 |
|------|------|----------|
| `positive` | 正 Gamma | 波动率压缩，市场稳定 |
| `negative` | 负 Gamma | 波动率扩张，市场波动 |
| `neutral` | 中性 | 无明显倾向 |

### Term Structure (期限结构)

| 状态 | Slope | 说明 |
|------|-------|------|
| `backwardation` | > 2% | 前月 IV > 后月 IV |
| `flat` | -2% ~ 2% | 平坦 |
| `contango` | < -2% | 前月 IV < 后月 IV |

### 决策流程

```
特征 → 信号评分 → 加权汇总 → Long/Short Score → 决策 + 概率
```

| 决策 | 条件 |
|------|------|
| `LONG_VOL` | Long Score ≥ 1.0 且 概率 ≥ 55% |
| `SHORT_VOL` | Short Score ≥ 1.0 且 概率 ≥ 55% |
| `HOLD` | 不满足以上条件 |

---

## 📈 输出示例

```
============================================================
📊 波动率分析系统 v2.0 - CREATE
   Symbol: AAPL
   时间: 2026-01-03 14:30:00
============================================================

📂 加载数据...
🔍 校验字段...
📊 计算特征...
🎯 计算评分...
🤖 生成决策...
🎮 生成策略...
💰 估计 Edge...

--------------------------------------------------
【分析结果】
--------------------------------------------------
  数据质量: 100.0/100

  【核心特征】
    VRP: 5.5% (short_bias)
    期限结构: flat (slope=2.0%)
    GEX: positive

  【评分】
    Long Vol Score:  -0.13
    Short Vol Score: +0.21
    主导方向: short

  【决策】
    ⚪ 观望等待
    置信度: low
    概率: L=25% S=25% H=50%

  【策略】
    Calendar Spread (备选)
    风险等级: conservative
    DTE: 30-60 (optimal: 45)

  【Edge】
    胜率: 52%
    盈亏比: 1.8:1
    期望收益: $15.50
    ✅ 达标
--------------------------------------------------

💾 结果已缓存: data/output/AAPL/2026-01-03/AAPL_o_2026-01-03.json

✅ 分析完成!
```

---

## 🔌 VA 服务集成

系统支持从 VA 服务自动获取市场参数：

```bash
# 启动 VA 服务 (另一个终端)
cd volatility_analysis && python app.py

# cmd 命令会自动获取参数
cmd AAPL -v 18.5

# 输出:
# ✅ VA 服务已连接
# 📡 获取 AAPL 市场参数...
#   VIX: 18.5
#   IVR: 27.0
#   IV30: 36.1
#   HV20: 30.8
#   VRP: 17.21%
```

VA 服务 API 端点：
- `GET /api/swing/params/{symbol}` - 获取单个参数
- `POST /api/swing/params/batch` - 批量获取
- `GET /api/swing/symbols` - 列出可用 symbols
- `GET /api/swing/dates/{symbol}` - 列出可用日期

---

## 📝 License

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系

如有问题，请通过 Issue 联系。
