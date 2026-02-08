# Vol Quant Workflow

事件驱动的期权波动率策略系统。

## 特性

- **灵活包名**: 目录名即包名，无需修改代码
- **相对导入**: 包内使用相对导入，与目录名解耦
- **动态 setup.py**: 自动检测目录名生成包配置

## 安装

```bash
# 1. 解压到任意目录名（目录名就是包名）
unzip vol_workflow_flex.zip -d my_project
cd my_project

# 2. 创建虚拟环境并安装
python3 -m venv venv
source venv/bin/activate
pip install -e .

# 3. 配置（可选）
cp .env.example .env
# 编辑 .env 填入 API 配置
```

**目录名可以随意**：
```bash
my_project/        → 包名: my_project
vol_workflow/      → 包名: vol_workflow  
vol_quant_workflow/→ 包名: vol_quant_workflow
trading_system/    → 包名: trading_system
```

## 使用

### 命令行

```bash
# 初始化符号
cmd AAPL
cmd AAPL -d 2025-01-05

# 生成 schema_core 命令清单（用于填充 22 核心字段）
cmd AAPL -c schema_core

# 批量初始化（读取 volatility_analysis /api/bridge/batch）
vol-batch -d 2025-01-05 --limit 20
# 指定单个 symbol 批量初始化（由 bridge batch 端过滤）
vol-batch -d 2025-01-05 --symbol AAPL
# 输入/输出缓存写入:
# runtime/inputs/2025-01-05/{SYMBOL}_i_2025-01-05.json
# runtime/outputs/{SYMBOL}/2025-01-05/{SYMBOL}_o_2025-01-05.json

# 完整分析
task -i AAPL_i_2025-01-05 -c AAPL_o_2025-01-05

# 轻量更新
updated -i AAPL_i_2025-01-05 -c AAPL_o_2025-01-05
```

### 执行 batch 命令

```bash
# 方式1：安装后直接执行
vol-batch -d 2025-01-05
vol-batch -d 2025-01-05 --limit 20
vol-batch -d 2025-01-05 --symbol AAPL
vol-batch -d 2025-01-05 --runtime-dir runtime

# 方式2：按模块执行（适合未安装 console_scripts 场景）
python3 -m vol_quant_workflow.cli.batch -d 2025-01-05 --limit 20
python3 -m vol_quant_workflow.cli.batch -d 2025-01-05 --symbol AAPL
```

说明：`vol-batch` 用于避免与 macOS 自带 `/usr/bin/batch` 命令冲突。

参数说明：
- `-d, --date`：必填，格式 `YYYY-MM-DD`
- `--limit`：可选，限制本次处理 symbol 数量
- `--symbol`：可选，仅处理指定 symbol（如 `AAPL`）
- `--runtime-dir`：可选，默认 `runtime`
- 输出目录：`runtime/inputs/{DATE}/` 和 `runtime/outputs/{SYMBOL}/{DATE}/`

### Bridge 市场状态写入

在 `cmd` 生成输入模板时，如果 Bridge API 返回 market_state，将优先写入：
- `volatility.hv20`（仅在该字段为空时）
- `meta.datetime`（优先使用 market_state.as_of）

如果 Bridge 不可用或缺少字段，流程不报错，保持原有行为。

### 无需安装的方式

```bash
./run.sh cmd AAPL
./run.sh batch -d 2025-01-05
./run.sh task -i AAPL_i_2025-01-05 -c AAPL_o_2025-01-05
./run.sh updated -i AAPL_i_2025-01-05 -c AAPL_o_2025-01-05
```

## 项目结构

```
<your_directory>/      ← 目录名即包名
├── setup.py           # 动态包配置
├── run.sh             # 便捷脚本
├── __init__.py
├── cli/               # 命令行接口
├── config/            # 配置管理
├── core/              # 核心模块
├── decision/          # 决策模块
├── execution/         # 执行模块
├── features/          # 特征计算
├── llm/               # LLM 集成
├── prompts/           # 提示词模板
├── schemas/           # 数据结构
├── signals/           # 信号评分
├── runtime/           # 运行时文件
├── .env.example       # 环境变量模板
└── model_config.yaml  # 模型配置
```

## 配置

### 环境变量 (.env)

```bash
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-your-key
PROB_THRESHOLD=0.55
DECISION_THRESHOLD_LONG=1.00
```

### 多模型编排 (model_config.yaml)

```yaml
default:
  model: DeepSeek-V3.2-Thinking
  base_url: "https://www.dmxapi.cn/v1"

agents:
  agent3:  # 数据校验（视觉）
    model: Qwen3-VL-235B-A22B-Instruct
  agent5:  # 场景分析
    model: DeepSeek-V3.2-Thinking
  agent6:  # 策略生成
    model: DeepSeek-V3.2-Thinking
```

## 技术说明

### 相对导入

包内所有模块使用相对导入：
```python
from .core import Config
from ..features import FeatureCalculator
```

### 动态 setup.py

```python
PACKAGE_NAME = os.path.basename(os.path.dirname(__file__))
# 自动获取目录名作为包名
```
