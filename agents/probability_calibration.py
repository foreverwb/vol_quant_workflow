"""
概率校准Agent
"""
import json
from agents.base_agent import BaseAgent
from models.data_models import (
    ProbabilityCalibration, DecisionGate, Direction, Scores
)
from typing import Dict, Any

class ProbabilityCalibrationAgent(BaseAgent):
    """概率校准Agent"""
    
    def __init__(self):
        super().__init__("probability_calibration")
    
    async def run(
        self,
        scores: Scores,
        env_config: Dict[str, Any]
    ) -> tuple[ProbabilityCalibration, DecisionGate]:
        """
        校准概率并进行决策门控
        
        Returns:
            (ProbabilityCalibration, DecisionGate)
        """
        
        long_score = scores.long_vol_score
        short_score = scores.short_vol_score
        
        # 概率标定（冷启动先验）
        p_long = self._calibrate_probability(long_score, "long")
        p_short = self._calibrate_probability(short_score, "short")
        
        # 置信度判定
        if max(long_score, short_score) >= 2.0:
            confidence = "high"
        elif max(long_score, short_score) >= 1.5:
            confidence = "medium"
        else:
            confidence = "low"
        
        probability = ProbabilityCalibration(
            p_long=round(p_long, 3),
            p_short=round(p_short, 3),
            confidence=confidence,
            method="冷启动先验",
            rationale=f"基于LongScore={long_score:.2f}, ShortScore={short_score:.2f}"
        )
        
        # 决策门控
        decision_threshold_long = float(env_config.get('DECISION_THRESHOLD_LONG', 1.0))
        decision_threshold_short = float(env_config.get('DECISION_THRESHOLD_SHORT', 1.0))
        prob_threshold = float(env_config.get('PROB_THRESHOLD', 0.55))
        
        long_vol_pass = (
            long_score >= decision_threshold_long and
            short_score <= 0.30 and
            p_long >= prob_threshold
        )
        
        short_vol_pass = (
            short_score >= decision_threshold_short and
            long_score <= 0.30 and
            p_short >= prob_threshold
        )
        
        # 最终方向判定
        if long_vol_pass and not short_vol_pass:
            final_direction = Direction.LONG_VOL
        elif short_vol_pass and not long_vol_pass:
            final_direction = Direction.SHORT_VOL
        else:
            final_direction = Direction.NEUTRAL
        
        decision_gate = DecisionGate(
            long_vol_pass=long_vol_pass,
            short_vol_pass=short_vol_pass,
            final_direction=final_direction,
            gate_check={
                'long_score_check': f"{long_score:.2f} vs threshold {decision_threshold_long}",
                'short_score_check': f"{short_score:.2f} vs threshold {decision_threshold_short}",
                'prob_check': f"p_long={p_long:.2%}, p_short={p_short:.2%}",
                'conflict_check': 'no' if final_direction != Direction.NEUTRAL else 'yes'
            }
        )
        
        return probability, decision_gate
    
    @staticmethod
    def _calibrate_probability(score: float, direction: str) -> float:
        """概率标定"""
        if score >= 2.0:
            return 0.68 if direction == "long" else 0.65
        elif score >= 1.5:
            return 0.62 if direction == "long" else 0.60
        elif score >= 1.0:
            return 0.58 if direction == "long" else 0.55
        else:
            return 0.50
