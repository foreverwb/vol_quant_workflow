"""
数据转换模块
处理不同格式数据的转换和标准化
"""
from typing import Dict, Any, Optional
from core.types import MarketData, GEXRegime


def flatten_nested_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    将嵌套格式数据扁平化为统一格式
    
    支持两种输入格式:
    1. 新版嵌套格式 (schema v2.0)
    2. 旧版扁平格式
    
    Returns:
        扁平化字典，使用大写键名
    """
    result = {}
    
    # 检测是否为新版嵌套格式
    if "core_fields" in data:
        # 基础字段
        result["SPOT_PRICE"] = data.get("spot")
        result["TIMESTAMP_ET"] = data.get("timestamp")
        result["SYMBOL"] = data.get("symbol")
        
        core = data.get("core_fields", {})
        
        # gamma_regime
        gamma = core.get("gamma_regime", {})
        result["VOL_TRIGGER"] = gamma.get("vol_trigger")
        result["NET_GEX_SIGN"] = gamma.get("net_gex_sign")
        result["NET_DEX_SIGN"] = gamma.get("net_dex_sign")
        result["TOTAL_NET_GEX"] = gamma.get("total_net_gex")
        
        # key_levels
        levels = core.get("key_levels", {})
        result["GAMMA_WALL"] = levels.get("gamma_wall")
        result["GAMMA_WALL_2"] = levels.get("gamma_wall_2")
        result["CALL_WALL"] = levels.get("call_wall")
        result["PUT_WALL"] = levels.get("put_wall")
        result["MAX_PAIN"] = levels.get("max_pain")
        result["MAJOR_OI_STRIKES"] = levels.get("major_oi_strikes")
        
        # iv_hv
        ivhv = core.get("iv_hv", {})
        result["IV_ATM"] = ivhv.get("iv_atm")
        result["IV_FRONT"] = ivhv.get("iv_front") or ivhv.get("iv_atm")
        result["IV_BACK"] = ivhv.get("iv_back")
        result["IV_EVENT_W"] = ivhv.get("iv_event_w")
        result["HV10"] = ivhv.get("hv10")
        result["HV20"] = ivhv.get("hv20")
        result["HV60"] = ivhv.get("hv60")
        
        # structure
        struct = core.get("structure", {})
        result["VEX_NET"] = struct.get("vex_net")
        result["VANNA_ATM"] = struct.get("vanna_atm")
        result["TERM_SLOPE"] = struct.get("term_slope")
        result["PUT_SKEW_25"] = struct.get("put_skew_25")
        result["CALL_SKEW_25"] = struct.get("call_skew_25")
        result["SPREAD_ATM"] = struct.get("spread_atm")
        result["PCR_RATIO"] = struct.get("pcr_ratio")
        result["SMILE_CURVATURE"] = struct.get("smile_curvature")
        
        # enhanced
        enhanced = data.get("enhanced", {})
        result["VVIX"] = enhanced.get("vvix")
        result["VIX9D"] = enhanced.get("vix9d")
        result["VIX"] = enhanced.get("vix")
        result["ASK_PREMIUM_PCT"] = enhanced.get("ask_premium_pct")
        result["CORR_IDX"] = enhanced.get("corr_idx")
        
    else:
        # 旧版扁平格式
        for key, value in data.items():
            if not key.startswith("_"):
                upper_key = key.upper()
                result[upper_key] = value
        
        # 字段名兼容映射
        aliases = {
            "GAMMA_WALL_1": "GAMMA_WALL",
            "VEX_NET": "VEX_NET_5TO60DTE",
            "IV_M1_ATM": "IV_FRONT",
            "IV_M2_ATM": "IV_BACK",
            "IV_PUT_25D": "PUT_SKEW_25",
            "IV_CALL_25D": "CALL_SKEW_25",
        }
        for old_name, new_name in aliases.items():
            if old_name in result and new_name not in result:
                result[new_name] = result[old_name]
            if new_name in result and old_name not in result:
                result[old_name] = result[new_name]
    
    # 过滤 None
    return {k: v for k, v in result.items() if v is not None}


def to_market_data(flat_data: Dict[str, Any]) -> MarketData:
    """
    将扁平数据转换为 MarketData 对象
    """
    # 解析 GEX regime
    net_gex_sign = None
    if flat_data.get("NET_GEX_SIGN"):
        try:
            net_gex_sign = GEXRegime(flat_data["NET_GEX_SIGN"].lower())
        except (ValueError, AttributeError):
            pass
    
    return MarketData(
        symbol=flat_data.get("SYMBOL", "UNKNOWN"),
        spot=flat_data.get("SPOT_PRICE", 0),
        timestamp=flat_data.get("TIMESTAMP_ET"),
        vol_trigger=flat_data.get("VOL_TRIGGER"),
        net_gex_sign=net_gex_sign,
        total_net_gex=flat_data.get("TOTAL_NET_GEX"),
        gamma_wall=flat_data.get("GAMMA_WALL"),
        gamma_wall_2=flat_data.get("GAMMA_WALL_2"),
        call_wall=flat_data.get("CALL_WALL"),
        put_wall=flat_data.get("PUT_WALL"),
        max_pain=flat_data.get("MAX_PAIN"),
        iv_atm=flat_data.get("IV_ATM") or flat_data.get("IV_FRONT"),
        iv_front=flat_data.get("IV_FRONT") or flat_data.get("IV_M1_ATM"),
        iv_back=flat_data.get("IV_BACK") or flat_data.get("IV_M2_ATM"),
        iv_event_w=flat_data.get("IV_EVENT_W") or flat_data.get("IV_EVENT_W_ATM"),
        hv10=flat_data.get("HV10"),
        hv20=flat_data.get("HV20"),
        hv60=flat_data.get("HV60"),
        vex_net=flat_data.get("VEX_NET") or flat_data.get("VEX_NET_5TO60DTE"),
        vanna_atm=flat_data.get("VANNA_ATM"),
        term_slope=flat_data.get("TERM_SLOPE"),
        put_skew_25=flat_data.get("PUT_SKEW_25") or flat_data.get("IV_PUT_25D"),
        call_skew_25=flat_data.get("CALL_SKEW_25") or flat_data.get("IV_CALL_25D"),
        spread_atm=flat_data.get("SPREAD_ATM"),
        pcr_ratio=flat_data.get("PCR_RATIO"),
        vvix=flat_data.get("VVIX"),
        vix9d=flat_data.get("VIX9D"),
        vix=flat_data.get("VIX"),
    )


def to_nested_format(flat_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    将扁平数据转换为嵌套格式 (schema v2.0)
    """
    return {
        "_schema_version": "2.0",
        "symbol": flat_data.get("SYMBOL"),
        "timestamp": flat_data.get("TIMESTAMP_ET"),
        "spot": flat_data.get("SPOT_PRICE"),
        "core_fields": {
            "gamma_regime": {
                "vol_trigger": flat_data.get("VOL_TRIGGER"),
                "net_gex_sign": flat_data.get("NET_GEX_SIGN"),
                "net_dex_sign": flat_data.get("NET_DEX_SIGN"),
                "total_net_gex": flat_data.get("TOTAL_NET_GEX"),
            },
            "key_levels": {
                "gamma_wall": flat_data.get("GAMMA_WALL"),
                "gamma_wall_2": flat_data.get("GAMMA_WALL_2"),
                "call_wall": flat_data.get("CALL_WALL"),
                "put_wall": flat_data.get("PUT_WALL"),
                "max_pain": flat_data.get("MAX_PAIN"),
                "major_oi_strikes": flat_data.get("MAJOR_OI_STRIKES", []),
            },
            "iv_hv": {
                "iv_atm": flat_data.get("IV_ATM"),
                "iv_front": flat_data.get("IV_FRONT"),
                "iv_back": flat_data.get("IV_BACK"),
                "iv_event_w": flat_data.get("IV_EVENT_W"),
                "hv10": flat_data.get("HV10"),
                "hv20": flat_data.get("HV20"),
                "hv60": flat_data.get("HV60"),
            },
            "structure": {
                "vex_net": flat_data.get("VEX_NET"),
                "vanna_atm": flat_data.get("VANNA_ATM"),
                "term_slope": flat_data.get("TERM_SLOPE"),
                "put_skew_25": flat_data.get("PUT_SKEW_25"),
                "call_skew_25": flat_data.get("CALL_SKEW_25"),
                "spread_atm": flat_data.get("SPREAD_ATM"),
                "pcr_ratio": flat_data.get("PCR_RATIO"),
                "smile_curvature": flat_data.get("SMILE_CURVATURE"),
            },
        },
        "enhanced": {
            "vvix": flat_data.get("VVIX"),
            "vix9d": flat_data.get("VIX9D"),
            "vix": flat_data.get("VIX"),
            "ask_premium_pct": flat_data.get("ASK_PREMIUM_PCT"),
            "corr_idx": flat_data.get("CORR_IDX"),
        },
    }
