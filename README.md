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

# 完整分析
task -i AAPL_i_2025-01-05 -c AAPL_o_2025-01-05

# 轻量更新
update -i AAPL_i_2025-01-05 -c AAPL_o_2025-01-05
```

### 无需安装的方式

```bash
./run.sh cmd AAPL
./run.sh task -i AAPL_i_2025-01-05 -c AAPL_o_2025-01-05
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
