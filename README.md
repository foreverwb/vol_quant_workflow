# vol_quant_workflow
```
vol_quant_workflow
├─ README.md
├── config/
│   ├── __init__.py
│   ├── prompts.py          # 所有LLM prompts集中管理
│   ├── schemas.py          # 所有JSON schemas集中管理
│   ├── env_config.py       # 环境变量管理
│   └── model_config.py     # 模型配置
├── models/
│   ├── __init__.py
│   ├── data_models.py      # 数据模型定义
│   └── types.py            # 类型定义
├── agents/
│   ├── __init__.py
│   ├── base_agent.py       # 基础Agent类
│   ├── router_agent.py     # 路由Agent
│   ├── data_validation.py  # 数据校验Agent
│   ├── probability_calibration.py  # 概率校准Agent
│   ├── strategy_mapping.py # 策略映射Agent
│   ├── final_decision.py   # 最终决策Agent
│   └── command_generator.py # 命令生成Agent
├── core/
│   ├── __init__.py
│   ├── feature_calculator.py      # 特征计算
│   ├── signal_calculator.py       # 信号打分
│   ├── strike_calculator.py       # 行权价计算
│   └── edge_estimator.py          # Edge估算
├── llm/
│   ├── __init__.py
│   └── llm_client.py      # 通用LLM客户端
├── utils/
│   ├── __init__.py
│   ├── file_handler.py    # 文件处理
│   └── logger.py          # 日志
├── workflow.py            # 主工作流
├── batch_processor.py     # 批量处理器
├── requirements.txt
└── app.py

```