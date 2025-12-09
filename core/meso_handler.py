"""
Meso Handler - Meso 平台上下文处理器
负责加载、解析和应用 Meso 上下文
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..workflow import VolatilityWorkflow


@dataclass
class MesoPosition:
    """Meso 仓位信息"""
    symbol: str
    quantity: int
    avg_price: float
    side: str  # "long" or "short"
    pnl: float = 0.0


@dataclass
class MesoAccount:
    """Meso 账户信息"""
    account_id: str
    buying_power: float
    margin_used: float
    positions: List[MesoPosition]


class MesoHandler:
    """Meso 上下文处理器"""
    
    def __init__(self, workflow: "VolatilityWorkflow"):
        self.workflow = workflow
        self.ctx = workflow.context
        self.logger = workflow.logger
        
        self._account: Optional[MesoAccount] = None
        self._preferences: Dict[str, Any] = {}
        self._constraints: Dict[str, Any] = {}
    
    def apply_context(self, meso_context: Dict[str, Any]) -> None:
        """应用 Meso 上下文到工作流"""
        self.logger.info("Applying Meso context...")
        
        # 存储原始上下文
        self.ctx.meso_context = meso_context
        
        # 解析各部分
        self._parse_account(meso_context.get("account", {}))
        self._parse_preferences(meso_context.get("preferences", {}))
        self._parse_constraints(meso_context.get("constraints", {}))
        
        # 应用约束到配置
        self._apply_constraints_to_config()
        
        self.logger.info(f"Meso context applied: account={self._account is not None}")
    
    def get_current_position(self, symbol: str) -> Optional[MesoPosition]:
        """获取指定标的的当前仓位"""
        if not self._account:
            return None
        
        symbol_upper = symbol.upper()
        for pos in self._account.positions:
            if pos.symbol.upper() == symbol_upper:
                return pos
        return None
    
    def get_buying_power(self) -> float:
        """获取可用购买力"""
        return self._account.buying_power if self._account else 0.0
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取用户偏好设置"""
        return self._preferences.get(key, default)
    
    def get_constraint(self, key: str, default: Any = None) -> Any:
        """获取约束条件"""
        return self._constraints.get(key, default)
    
    def has_existing_position(self, symbol: str) -> bool:
        """检查是否有现有仓位"""
        return self.get_current_position(symbol) is not None
    
    def check_position_limit(self, symbol: str, new_quantity: int) -> bool:
        """检查仓位限制"""
        max_position = self._constraints.get("max_position_per_symbol", float("inf"))
        
        current = self.get_current_position(symbol)
        current_qty = current.quantity if current else 0
        
        return (current_qty + new_quantity) <= max_position
    
    # ==================== 私有方法 ====================
    
    def _parse_account(self, account_data: Dict[str, Any]) -> None:
        """解析账户信息"""
        if not account_data:
            return
        
        positions = []
        for pos_data in account_data.get("positions", []):
            positions.append(MesoPosition(
                symbol=pos_data.get("symbol", ""),
                quantity=pos_data.get("quantity", 0),
                avg_price=pos_data.get("avg_price", 0.0),
                side=pos_data.get("side", "long"),
                pnl=pos_data.get("pnl", 0.0),
            ))
        
        self._account = MesoAccount(
            account_id=account_data.get("account_id", ""),
            buying_power=account_data.get("buying_power", 0.0),
            margin_used=account_data.get("margin_used", 0.0),
            positions=positions,
        )
    
    def _parse_preferences(self, pref_data: Dict[str, Any]) -> None:
        """解析用户偏好"""
        self._preferences = {
            "risk_tolerance": pref_data.get("risk_tolerance", "medium"),
            "preferred_strategies": pref_data.get("preferred_strategies", []),
            "max_dte": pref_data.get("max_dte", 45),
            "min_dte": pref_data.get("min_dte", 7),
            "preferred_delta": pref_data.get("preferred_delta", 0.3),
        }
    
    def _parse_constraints(self, constraint_data: Dict[str, Any]) -> None:
        """解析约束条件"""
        self._constraints = {
            "max_position_per_symbol": constraint_data.get("max_position_per_symbol", 100),
            "max_total_exposure": constraint_data.get("max_total_exposure", 100000),
            "blacklist": constraint_data.get("blacklist", []),
            "whitelist": constraint_data.get("whitelist", None),  # None = all allowed
            "max_loss_per_trade": constraint_data.get("max_loss_per_trade", 1000),
        }
    
    def _apply_constraints_to_config(self) -> None:
        """将 Meso 约束应用到工作流配置"""
        config = self.workflow.config
        
        # 合并黑名单
        meso_blacklist = self._constraints.get("blacklist", [])
        if meso_blacklist:
            existing = config.blacklist or []
            config.blacklist = list(set(existing + meso_blacklist))
        
        # 应用仓位限制
        max_pos = self._constraints.get("max_position_per_symbol")
        if max_pos and max_pos < config.max_position_size:
            config.max_position_size = max_pos