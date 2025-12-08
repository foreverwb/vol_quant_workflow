# 波动率套利策略工作流 (Vol Workflow v2)

基于 YAML 工作流配置的期权波动率套利策略分析系统，支持 gexbot 图表解析、信号评分、策略生成等完整流程。

## 目录结构

```
vol_workflow_v2/
├── __init__.py                    # 包入口
├── config.py                      # 配置管理
├── workflow.py                    # 工作流引擎
├── main.py                        # CLI 入口
│
├── prompts/                       # Prompt 模块化管理
│   ├── __init__.py               # 注册表 + 统一导出
│   ├── base.py                   # PromptTemplate 基类
│   ├── router.py                 # Router prompt
│   ├── command_generator.py      # 命令生成 (#2001)
│   ├── data_validator.py         # 数据校验 (#3001)
│   ├── probability_calibrator.py # 概率校准 (#6001)
│   ├── strategy_mapper.py        # 策略映射 (#7001)
│   └── final_report.py           # 最终报告 (#8001)
│
├── schemas/                       # JSON Schema 管理
│   ├── __init__.py               # 注册表 + 验证工具
│   ├── base.py                   # SchemaDefinition 基类
│   ├── data_validator.py         # 数据校验 schema
│   ├── probability_calibrator.py # 概率校准 schema
│   └── strategy_mapper.py        # 策略映射 schema
│
├── nodes/                         # 节点模块
│   ├── __init__.py               # NodeFactory + 统一导出
│   ├── base.py                   # LLMNodeBase 基类
│   ├── router.py                 # 路由节点
│   ├── command_generator.py      # 命令生成节点
│   ├── data_validator.py         # 数据校验节点 (Vision)
│   ├── probability_calibrator.py # 概率校准节点
│   ├── strategy_mapper.py        # 策略映射节点
│   ├── final_report.py           # 最终报告节点
│   └── code/                     # 代码节点
│       ├── __init__.py           # 通用工具
│       ├── feature_calc.py       # CODE1: 特征计算
│       ├── signal_scoring.py     # CODE2: 信号打分
│       ├── strike_calc.py        # CODE3: 行权价计算
│       └── edge_estimation.py    # CODE4: Edge 估算
│
└── utils/
    ├── __init__.py
    └── llm_client.py             # 通用 LLM 客户端
```

## 安装

```bash
# 安装依赖
pip install httpx

# (可选) 安装 scipy 以获得更精确的行权价计算
pip install numpy scipy
```

## 快速开始

### 1. 命令行使用

```bash
# 设置环境变量
export LLM_API_BASE="https://api.openai.com/v1"
export LLM_API_KEY="sk-your-api-key"

# 输入变量，生成 gexbot 命令清单
python main.py --input "NVDA 财报 5-20DTE delta-neutral"

# 处理图表文件
python main.py --files chart1.png chart2.png chart3.png

# 批量处理文件夹
python main.py --folder ./charts --output ./reports --min-files 10
```

### 2. 编程接口

```python
import vol_workflow_v2 as vw

# 创建工作流
workflow = vw.create_workflow(
    api_base="https://api.openai.com/v1",
    api_key="sk-xxx",
    model_name="gpt-4o"
)

# 运行工作流
result = workflow.run_sync(
    user_input="NVDA 财报 5-20DTE",
    files=["chart1.png", "chart2.png"]
)

print(result["report"])
```

### 3. 便捷函数

```python
from vol_workflow_v2 import run_workflow

result = run_workflow(
    files=["chart1.png", "chart2.png"],
    api_base="https://api.openai.com/v1",
    api_key="sk-xxx"
)
```

## 数据流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户输入                                        │
│                    (变量信息 或 gexbot 图表)                                  │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  [Step 1] Router Node                                                        │
│  判断输入类型: VARIABLES / DATA / INVALID                                     │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
┌─────────────────────────┐      ┌─────────────────────────────────────────────┐
│ [Step 2] CommandGenerator│      │  [Step 3] DataValidator (Vision)            │
│ 生成 gexbot 命令清单     │      │  解析图表，提取 22 个核心字段                 │
│                         │      │  - VOL TRIGGER, Gamma Walls                 │
│ 返回命令列表等待         │      │  - IV/HV 数据, 结构性指标                    │
│ 用户执行后回传数据       │      └──────────────────────┬──────────────────────┘
└─────────────────────────┘                             │
                                                        ▼
                               ┌──────────────────────────────────────────────┐
                               │  [Step 4] CODE1: Feature Calculation          │
                               │  计算 VRP, GEX Level, Term Structure 等特征    │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │  [Step 5] CODE2: Signal Scoring               │
                               │  计算 LongVolScore / ShortVolScore            │
                               │  权重加总 15+ 信号因子                         │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │  [Step 6] ProbabilityCalibrator (LLM)         │
                               │  将评分转化为概率                              │
                               │  三分类决策: 做多波动率 / 做空波动率 / 观望     │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │  [Step 7] StrategyMapper (LLM)                │
                               │  生成三档策略 (进取/均衡/保守)                  │
                               │  - Long Straddle/Strangle                    │
                               │  - Iron Condor / Credit Spread               │
                               │  - Calendar / Diagonal                       │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │  [Step 8] CODE3: Strike Calculation           │
                               │  计算具体行权价                                │
                               │  - Delta 法 / 壁垒法 / ATR 法                 │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │  [Step 9] CODE4: Edge Estimation              │
                               │  蒙特卡洛模拟 (10,000 次)                      │
                               │  计算胜率、盈亏比、期望收益                     │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │  [Step 10] FinalReport (LLM)                  │
                               │  生成 Markdown 决策报告                        │
                               │  - 核心结论, 市场状态                          │
                               │  - 信号评分, 推荐策略                          │
                               │  - 风险提示, 监控要点                          │
                               └──────────────────────────────────────────────┘
```

## 配置说明

### ModelConfig (模型配置)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| api_base | str | "" | API 基础 URL |
| api_key | str | "" | API 密钥 |
| name | str | "default-model" | 模型名称 |
| vision_model_name | str | None | 视觉模型名称 |
| temperature | float | 0.7 | 温度参数 |
| max_tokens | int | 4096 | 最大 token 数 |
| timeout | float | 120.0 | 请求超时时间 |
| retry_count | int | 3 | 重试次数 |

### WorkflowConfig (工作流配置)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| DECISION_THRESHOLD_LONG | float | 1.0 | 做多波动率决策门槛 |
| DECISION_THRESHOLD_SHORT | float | 1.0 | 做空波动率决策门槛 |
| PROB_THRESHOLD | float | 0.55 | 概率门槛 |
| EDGE_RR_THRESHOLD | float | 1.5 | Edge 盈亏比门槛 |
| WEIGHT_VRP_LONG | float | 0.25 | VRP 做多权重 |
| WEIGHT_GEX_LONG | float | 0.18 | GEX 做多权重 |
| MONTE_CARLO_SIMULATIONS | int | 10000 | 蒙特卡洛模拟次数 |

## 扩展开发

### 添加新 Prompt

```python
# prompts/my_prompt.py
from .base import PromptTemplate, register_prompt

MY_PROMPT = register_prompt(PromptTemplate(
    name="my_prompt",
    description="我的新 prompt",
    system="系统提示词...",
    user="${variable} 用户模板..."
))

# 在 prompts/__init__.py 添加导入
from . import my_prompt
from .my_prompt import MY_PROMPT
```

### 添加新 Schema

```python
# schemas/my_schema.py
from .base import SchemaDefinition, register_schema

MY_SCHEMA = register_schema(SchemaDefinition(
    name="my_schema",
    schema={
        "type": "object",
        "required": ["field1"],
        "properties": {
            "field1": {"type": "string"}
        }
    }
))

# 在 schemas/__init__.py 添加导入
from . import my_schema
from .my_schema import MY_SCHEMA
```

### 添加新 LLM 节点

```python
# nodes/my_node.py
from .base import LLMNodeBase, NodeResult, register_node

try:
    from ..prompts import MY_PROMPT
    from ..schemas import get_schema
except ImportError:
    from prompts import MY_PROMPT
    from schemas import get_schema

@register_node("my_node")
class MyNode(LLMNodeBase):
    async def execute(self, **kwargs) -> NodeResult:
        response = await self.client.chat(
            system_prompt=MY_PROMPT.system,
            user_prompt=MY_PROMPT.format_user(**kwargs),
            json_schema=get_schema("my_schema")
        )
        return NodeResult(
            success=response.success,
            text=response.content,
            structured_output=response.structured_output
        )

# 在 nodes/__init__.py 添加导入
from .my_node import MyNode
```

### 添加新代码节点

```python
# nodes/code/my_calc.py
from . import CodeNodeResult

def my_calculation(input_data: dict, env_vars: dict) -> CodeNodeResult:
    try:
        result = {"calculated": input_data["value"] * 2}
        return CodeNodeResult(success=True, result=result)
    except Exception as e:
        return CodeNodeResult(success=False, result={}, error=str(e))

# 在 nodes/code/__init__.py 导出
from .my_calc import my_calculation
```

## 支持的 LLM 提供商

本项目使用 OpenAI 兼容 API，支持：

- **OpenAI**: `https://api.openai.com/v1`
- **Azure OpenAI**: `https://{resource}.openai.azure.com/openai/deployments/{deployment}`
- **Qwen (通义千问)**: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- **DeepSeek**: `https://api.deepseek.com/v1`
- **Ollama**: `http://localhost:11434/v1`
- **vLLM**: `http://localhost:8000/v1`

## 输出示例

```markdown
# 波动率交易决策报告

**标的**: NVDA | **现价**: 142.50 | **VOL TRIGGER**: 140.00  
**分析时间**: 2024-01-15 10:30:00 (ET)

---

## 1. 核心结论

**决策方向**: 做多波动率  
**概率**: 0.65 (置信度: medium)  
**主要理由**: 现价高于 VOL TRIGGER，处于正 Gamma 区域，但 VRP 为负...

---

## 2. 推荐策略

### 进取版 - Long Straddle

**参数**:
- DTE: 14-21天
- 行权区间:
  - [Leg1]: buy 142.50 call (ATM)
  - [Leg2]: buy 142.50 put (ATM)

**Edge估算**:
- 胜率: 0.58
- 盈亏比: 2.1:1
- 期望收益: $125
- 是否满足门槛: ✅
```

## License

MIT License
