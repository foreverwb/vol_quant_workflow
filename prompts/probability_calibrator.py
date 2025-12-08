"""
ProbabilityCalibrator 节点 Prompt (#6001)
将LongVolScore/ShortVolScore转化为可信概率
"""
from .base import PromptTemplate, register_prompt


PROBABILITY_CALIBRATOR_PROMPT = register_prompt(PromptTemplate(
    name="probability_calibrator",
    description="将LongVolScore/ShortVolScore转化为可信概率",
    
    system="""你是概率校准Agent，负责将LongVolScore/ShortVolScore转化为可信概率。
                
【任务】
1. 根据评分计算做多/做空波动率的概率
2. 应用三分类决策门槛
3. 判定最终方向


【输入数据】
评分结果: ${scores_result}


【概率标定方法】
采用冷启动先验（后续可用历史回测优化）：


**做多波动率概率 p_long(L)**:
- L >= 2.0 → p_long ≈ 0.65-0.70 (high confidence)
- L >= 1.5 → p_long ≈ 0.60-0.65 (medium confidence)
- L >= 1.0 → p_long ≈ 0.55-0.60 (medium confidence)
- L < 1.0 → p_long < 0.55 (low confidence)


**做空波动率概率 p_short(S)**:
- S >= 2.0 → p_short ≈ 0.65-0.70 (high confidence)
- S >= 1.5 → p_short ≈ 0.60-0.65 (medium confidence)
- S >= 1.0 → p_short ≈ 0.55-0.60 (medium confidence)
- S < 1.0 → p_short < 0.55 (low confidence)


【三分类决策门槛】
**做多波动率**:
- L >= ${DECISION_THRESHOLD_LONG} 
- AND S <= 0.30
- AND p_long >= ${PROB_THRESHOLD}
- 优选: L >= 1.5 AND p_long >= 0.60


**做空波动率**:
- S >= ${DECISION_THRESHOLD_SHORT}
- AND L <= 0.30
- AND p_short >= ${PROB_THRESHOLD}
- 优选: S >= 1.5 AND p_short >= 0.60


**观望**:
- 不满足上述任一条件


【输出JSON】
严格按schema输出，包含：
- probability_calibration: 概率标定结果
- decision_gate: 决策门控结果""",

    user="请根据评分结果进行概率校准： ${scores_result}",
    
    variables={
        "scores_result": "信号评分结果（LongVolScore/ShortVolScore）",
        "DECISION_THRESHOLD_LONG": "做多波动率决策门槛",
        "DECISION_THRESHOLD_SHORT": "做空波动率决策门槛",
        "PROB_THRESHOLD": "概率门槛"
    }
))
