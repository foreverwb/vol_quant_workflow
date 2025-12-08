"""
上下文加载器 - Meso/Micro 系统桥接层

该模块负责：
1. 从 volatility_analysis (Meso) 系统获取市场上下文
2. 根据 Meso 信号动态调整 Micro 系统的配置参数
3. 提供策略黑名单和动态 DTE 建议
"""
import httpx
from dataclasses import dataclass, field, replace
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, date
from enum import Enum


class SqueezeMode(Enum):
    """挤压模式类型"""
    NONE = "none"
    GAMMA_SQUEEZE = "gamma_squeeze"
    SHORT_SQUEEZE = "short_squeeze"


@dataclass
class MarketContext:
    """
    从 Meso 系统获取的市场上下文
    
    用于指导 Micro 系统的参数动态调整
    """
    # 基础信息
    symbol: str = ""
    timestamp: str = ""
    
    # 波动率数据
    iv30: float = 20.0          # 30日隐含波动率
    ivr: float = 50.0           # IV Rank (0-100)
    hv20: float = 20.0          # 20日历史波动率
    ivrv_ratio: float = 1.0     # IV/RV 比率
    
    # Meso 信号
    quadrant: str = "中性/待观察"      # 四象限判断
    direction_score: float = 0.0       # 方向分数 (-3 ~ +3)
    vol_score: float = 0.0             # 波动分数
    direction_bias: str = "中性"       # 方向偏好
    vol_bias: str = "中性"             # 波动偏好
    
    # 状态标记
    is_squeeze: bool = False           # Gamma Squeeze 潜力
    is_index: bool = False             # 是否为指数标的
    
    # 市场环境
    spot_vol_corr_score: float = 0.0   # 价-波相关性 (>0.4逼空, <-0.5恐慌)
    term_structure_ratio: Optional[float] = None  # IV30/IV90 期限结构
    regime_ratio: float = 1.0          # HV20/HV1Y 波动率体制
    
    # 事件
    days_to_earnings: Optional[int] = None  # 距财报天数
    
    # 元数据
    confidence: str = "中"
    data_freshness: str = ""           # 数据新鲜度
    
    def is_high_vol_env(self) -> bool:
        """判断是否为高波动环境"""
        return self.iv30 >= 35 or self.ivr >= 70
    
    def is_low_vol_env(self) -> bool:
        """判断是否为低波动环境"""
        return self.iv30 <= 18 or self.ivr <= 25
    
    def is_earnings_imminent(self, days: int = 14) -> bool:
        """判断是否临近财报"""
        return self.days_to_earnings is not None and 0 < self.days_to_earnings <= days
    
    def is_crash_risk(self) -> bool:
        """判断是否存在 Crash 风险 (偏空 + 买波)"""
        return self.quadrant == "偏空—买波"
    
    def is_melt_up_risk(self) -> bool:
        """判断是否存在逼空风险 (偏多 + 买波 + squeeze)"""
        return self.quadrant == "偏多—买波" and self.is_squeeze
    
    def get_vol_scale_factor(self, base_vol: float = 20.0) -> float:
        """
        获取波动率缩放因子
        
        用于动态调整 Z-Score 的 std 参数
        高波动环境下放大容忍度，低波动环境下收紧
        """
        if self.iv30 <= 0:
            return 1.0
        scale = self.iv30 / base_vol
        # 限制在 0.5 ~ 2.5 之间
        return max(0.5, min(2.5, scale))


@dataclass
class DynamicConfig:
    """
    动态配置 - 根据 Meso 上下文生成
    
    覆盖 WorkflowConfig 中的关键参数
    """
    # 决策阈值
    DECISION_THRESHOLD_LONG: float = 1.0
    DECISION_THRESHOLD_SHORT: float = 1.0
    
    # 做多波动率权重 (归一化后)
    WEIGHT_VRP_LONG: float = 0.25
    WEIGHT_GEX_LONG: float = 0.18
    WEIGHT_VEX_LONG: float = 0.18
    WEIGHT_CARRY_LONG: float = 0.08
    WEIGHT_SKEW_LONG: float = 0.08
    
    # 做空波动率权重
    WEIGHT_VRP_SHORT: float = 0.30
    WEIGHT_GEX_SHORT: float = 0.12
    WEIGHT_CARRY_SHORT: float = 0.18
    
    # 动态 Z-Score 标准差缩放
    vol_scale_factor: float = 1.0
    
    # 策略约束
    strategy_blacklist: Set[str] = field(default_factory=set)
    
    # 动态 DTE 建议
    suggested_dte_min: int = 30
    suggested_dte_max: int = 45
    dte_reason: str = "标准周期"
    
    # 动态 Delta 偏好
    suggested_delta_bias: str = "neutral"  # bullish/bearish/neutral
    
    # 信号增强因子
    gex_signal_multiplier: float = 1.0
    vex_signal_multiplier: float = 1.0


class ContextLoader:
    """
    上下文加载器
    
    负责从 Meso 系统获取数据并生成动态配置
    """
    
    def __init__(self, meso_api_url: str = "http://localhost:8668"):
        """
        初始化
        
        Args:
            meso_api_url: volatility_analysis 系统的 API 地址
        """
        self.base_url = meso_api_url.rstrip('/')
        self._cache: Dict[str, MarketContext] = {}
        self._cache_ttl = 300  # 缓存5分钟
    
    async def fetch_context(self, symbol: str, vix: Optional[float] = None) -> Optional[MarketContext]:
        """
        从 Meso 系统获取市场上下文
        
        Args:
            symbol: 股票代码
            vix: 可选的 VIX 值
            
        Returns:
            MarketContext 或 None (如果获取失败)
        """
        symbol = symbol.upper()
        
        try:
            url = f"{self.base_url}/api/swing/params/{symbol}"
            if vix is not None:
                url += f"?vix={vix}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    if not data.get('success'):
                        print(f"[ContextLoader] API 返回失败: {data.get('error')}")
                        return None
                    
                    params = data.get('params', {})
                    source = data.get('_source', {})
                    
                    context = MarketContext(
                        symbol=symbol,
                        timestamp=source.get('timestamp', ''),
                        
                        # 波动率数据
                        iv30=float(params.get('iv30') or 20.0),
                        ivr=float(params.get('ivr') or 50.0),
                        hv20=float(params.get('hv20') or 20.0),
                        ivrv_ratio=float(source.get('ivrv_ratio') or 1.0),
                        
                        # Meso 信号
                        quadrant=source.get('quadrant', '中性/待观察'),
                        direction_score=float(source.get('direction_score', 0.0) or 0.0),
                        vol_score=float(source.get('vol_score', 0.0) or 0.0),
                        direction_bias=source.get('direction_bias', '中性'),
                        vol_bias=source.get('vol_bias', '中性'),
                        
                        # 状态标记
                        is_squeeze=source.get('is_squeeze', False),
                        is_index=source.get('is_index', False),
                        
                        # 市场环境
                        spot_vol_corr_score=float(source.get('spot_vol_corr_score', 0.0) or 0.0),
                        term_structure_ratio=source.get('term_structure_ratio'),
                        regime_ratio=float(source.get('regime_ratio', 1.0) or 1.0),
                        
                        # 事件
                        days_to_earnings=source.get('days_to_earnings'),
                        
                        # 元数据
                        confidence=source.get('confidence', '中'),
                        data_freshness=source.get('timestamp', '')[:10] if source.get('timestamp') else ''
                    )
                    
                    # 缓存
                    self._cache[symbol] = context
                    
                    return context
                    
                elif resp.status_code == 404:
                    print(f"[ContextLoader] Symbol {symbol} 未找到")
                    return None
                else:
                    print(f"[ContextLoader] API 错误: {resp.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            print(f"[ContextLoader] 请求超时: {symbol}")
            return self._cache.get(symbol)  # 返回缓存
            
        except Exception as e:
            print(f"[ContextLoader] 获取上下文失败: {e}")
            return self._cache.get(symbol)
    
    def generate_dynamic_config(
        self, 
        base_config: Any,  # WorkflowConfig
        context: MarketContext
    ) -> DynamicConfig:
        """
        根据 Meso 上下文生成动态配置
        
        核心逻辑：
        1. 根据方向分数调整决策阈值 (贝叶斯门槛)
        2. 根据 Squeeze 状态调整权重 (情境加权)
        3. 根据 IV 水平调整 Z-Score 缩放 (自适应波动率)
        4. 根据事件和状态生成策略约束
        
        Args:
            base_config: 基础 WorkflowConfig
            context: 市场上下文
            
        Returns:
            DynamicConfig 动态配置
        """
        config = DynamicConfig()
        
        # ===== 1. 贝叶斯门槛调整 =====
        # Meso 方向越强，对应方向的 Micro 门槛越低
        # 例如: Meso direction_score=2.0 (强看多) → Long 门槛降至 0.6, Short 门槛升至 1.4
        direction_bias = context.direction_score * 0.2
        base_threshold = getattr(base_config, 'DECISION_THRESHOLD_LONG', 1.0)
        
        config.DECISION_THRESHOLD_LONG = max(0.5, base_threshold - direction_bias)
        config.DECISION_THRESHOLD_SHORT = max(0.5, base_threshold + direction_bias)
        
        # ===== 2. 情境加权 (Squeeze 模式) =====
        if context.is_squeeze:
            # Gamma Squeeze: 大幅提升 GEX/VEX 权重，降低 Carry/VRP
            config.WEIGHT_GEX_LONG = 0.35
            config.WEIGHT_VEX_LONG = 0.25
            config.WEIGHT_VRP_LONG = 0.12
            config.WEIGHT_CARRY_LONG = 0.05
            config.WEIGHT_SKEW_LONG = 0.05
            
            # 信号增强
            config.gex_signal_multiplier = 1.5
            config.vex_signal_multiplier = 1.3
            
        elif context.is_high_vol_env():
            # 高波动环境: 提高 VRP 权重 (均值回归更可靠)
            config.WEIGHT_VRP_LONG = 0.30
            config.WEIGHT_VRP_SHORT = 0.35
            config.WEIGHT_GEX_LONG = 0.15
            config.WEIGHT_GEX_SHORT = 0.10
            
        elif context.is_low_vol_env():
            # 低波动环境: 提高 Carry 和 Skew 权重
            config.WEIGHT_CARRY_LONG = 0.12
            config.WEIGHT_SKEW_LONG = 0.12
            config.WEIGHT_CARRY_SHORT = 0.22
            
        # 归一化检查 (Long 权重)
        long_weights_sum = (
            config.WEIGHT_VRP_LONG + 
            config.WEIGHT_GEX_LONG + 
            config.WEIGHT_VEX_LONG + 
            config.WEIGHT_CARRY_LONG + 
            config.WEIGHT_SKEW_LONG
        )
        # 其余权重由固定部分占据 (vanna, rv, liq 等约 0.23)
        # 主因子权重目标约 0.77，允许一定误差
        
        # ===== 3. 自适应波动率缩放 =====
        config.vol_scale_factor = context.get_vol_scale_factor()
        
        # ===== 4. 策略黑名单 =====
        blacklist: Set[str] = set()
        
        if context.is_crash_risk():
            # Crash 风险: 禁用裸卖 Put 和宽跨
            blacklist.add("short_put")
            blacklist.add("short_strangle")
            blacklist.add("iron_condor")  # 也禁止，因为下行风险大
            
        if context.is_melt_up_risk():
            # 逼空风险: 禁用裸卖 Call
            blacklist.add("short_call")
            blacklist.add("covered_call")  # 限制备兑
            
        if context.is_earnings_imminent(days=7):
            # 财报周: 禁用卖波策略
            blacklist.add("short_strangle")
            blacklist.add("short_straddle")
            blacklist.add("iron_condor")
            
        config.strategy_blacklist = blacklist
        
        # ===== 5. 动态 DTE 建议 =====
        if context.is_squeeze:
            config.suggested_dte_min = 7
            config.suggested_dte_max = 21
            config.dte_reason = "Squeeze 模式 - 短周期捕捉 Gamma"
            
        elif context.is_earnings_imminent():
            dte = context.days_to_earnings or 14
            config.suggested_dte_min = dte + 5
            config.suggested_dte_max = dte + 14
            config.dte_reason = f"覆盖财报 ({dte}天后)"
            
        elif context.is_high_vol_env():
            config.suggested_dte_min = 21
            config.suggested_dte_max = 35
            config.dte_reason = "高波动 - 缩短周期控制 Vega 风险"
            
        elif context.is_low_vol_env():
            config.suggested_dte_min = 45
            config.suggested_dte_max = 60
            config.dte_reason = "低波动 - 延长周期等待波动回归"
            
        # ===== 6. Delta 偏好 =====
        if context.direction_score >= 1.0:
            config.suggested_delta_bias = "bullish"
        elif context.direction_score <= -1.0:
            config.suggested_delta_bias = "bearish"
        else:
            config.suggested_delta_bias = "neutral"
            
        return config
    
    def get_context_summary(self, context: MarketContext) -> str:
        """
        生成上下文摘要 (用于日志和报告)
        """
        lines = [
            f"=== Meso Context: {context.symbol} ===",
            f"象限: {context.quadrant} | 置信度: {context.confidence}",
            f"方向分: {context.direction_score:.2f} | 波动分: {context.vol_score:.2f}",
            f"IV30: {context.iv30:.1f}% | IVR: {context.ivr:.0f}% | IVRV: {context.ivrv_ratio:.2f}",
        ]
        
        flags = []
        if context.is_squeeze:
            flags.append("🔥Squeeze")
        if context.is_crash_risk():
            flags.append("⚠️CrashRisk")
        if context.is_earnings_imminent():
            flags.append(f"📅财报{context.days_to_earnings}D")
            
        if flags:
            lines.append(f"标记: {' '.join(flags)}")
            
        return "\n".join(lines)


# 便捷函数
async def load_market_context(
    symbol: str, 
    meso_url: str = "http://localhost:8668",
    vix: Optional[float] = None
) -> Optional[MarketContext]:
    """
    便捷函数：加载市场上下文
    
    Args:
        symbol: 股票代码
        meso_url: Meso API 地址
        vix: VIX 值
        
    Returns:
        MarketContext 或 None
    """
    loader = ContextLoader(meso_url)
    return await loader.fetch_context(symbol, vix)
