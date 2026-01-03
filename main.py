#!/usr/bin/env python3
"""
波动率交易分析系统 v2.0

简化命令:
    cmd AAPL                   # 生成 gexbot 命令
    cmd AAPL -v 18.5           # 带 VIX 参数
    cmd AAPL -t 2026-01-03     # 指定日期
    create AAPL                # 完整分析
    create AAPL -i AAPL_i_2026-01-03.json  # 指定输入
    create AAPL -c AAPL_o_2026-01-03.json  # 指定缓存
    update AAPL                # 快速更新
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import create_pipeline, PipelineContext
from core import Decision
from utils.cache import CacheManager, get_cache_manager
from utils.va_client import VAClient, VAClientError, fetch_market_params, is_va_service_running


def print_header(mode: str, symbols: list):
    """打印头部"""
    symbol_str = ", ".join(symbols)
    print("\n" + "=" * 60)
    print(f"📊 波动率分析系统 v2.0 - {mode}")
    print(f"   Symbol: {symbol_str}")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def print_result(ctx: PipelineContext):
    """打印结果摘要"""
    print("\n" + "-" * 50)
    print("【分析结果】")
    print("-" * 50)
    
    # 数据质量
    if ctx.validation_summary:
        quality = ctx.validation_summary.get("data_quality_score", 0)
        print(f"  数据质量: {quality:.1f}/100")
    
    # 特征
    if ctx.features:
        f = ctx.features
        print(f"\n  【核心特征】")
        if f.vrp_selected is not None:
            print(f"    VRP: {f.vrp_selected:.1f}% ({f.vrp_regime.value if f.vrp_regime else 'N/A'})")
        if f.term_slope is not None:
            print(f"    期限结构: {f.term_regime.value if f.term_regime else 'N/A'} (slope={f.term_slope:.1f}%)")
        if f.net_gex_regime:
            print(f"    GEX: {f.net_gex_regime.value}")
    
    # 评分
    if ctx.scores:
        s = ctx.scores
        print(f"\n  【评分】")
        print(f"    Long Vol Score:  {s.long_vol_score:+.2f}")
        print(f"    Short Vol Score: {s.short_vol_score:+.2f}")
        print(f"    主导方向: {s.dominant_direction}")
    
    # 决策
    if ctx.decision:
        d = ctx.decision
        print(f"\n  【决策】")
        decision_text = {
            Decision.LONG_VOL: "🟢 做多波动率",
            Decision.SHORT_VOL: "🔴 做空波动率",
            Decision.HOLD: "⚪ 观望等待"
        }.get(d.decision, str(d.decision))
        print(f"    {decision_text}")
        print(f"    置信度: {d.confidence.value}")
        print(f"    概率: L={d.probability.p_long:.0%} S={d.probability.p_short:.0%} H={d.probability.p_hold:.0%}")
    
    # 策略
    if ctx.strategy:
        st = ctx.strategy
        print(f"\n  【策略】")
        print(f"    {st.name}")
        print(f"    风险等级: {st.risk_profile.value}")
        print(f"    DTE: {st.dte_min}-{st.dte_max} (optimal: {st.dte_optimal})")
    
    # Edge
    if ctx.edge:
        e = ctx.edge
        print(f"\n  【Edge】")
        print(f"    胜率: {e.win_rate:.0%}")
        print(f"    盈亏比: {e.reward_risk:.1f}:1")
        print(f"    期望收益: ${e.expected_value:.2f}")
        status = "✅ 达标" if e.is_profitable else "❌ 不达标"
        print(f"    {status}")
    
    print("-" * 50)


def serialize_dataclass(obj):
    """将 dataclass 对象序列化为可 JSON 的字典"""
    if hasattr(obj, '__dataclass_fields__'):
        result = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            result[field_name] = serialize_dataclass(value)
        return result
    elif hasattr(obj, 'value'):  # Enum
        return obj.value
    elif isinstance(obj, dict):
        return {k: serialize_dataclass(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_dataclass(v) for v in obj]
    else:
        return obj


def run_cmd(symbols: list, args):
    """执行 CMD 模式 - 生成命令并获取市场参数"""
    date = args.datetime or datetime.now().strftime('%Y-%m-%d')
    vix = args.vix
    
    print_header("CMD", symbols)
    
    # 检查 VA 服务
    va_available = is_va_service_running()
    if va_available:
        print(f"✅ VA 服务已连接")
    else:
        print(f"⚠️  VA 服务未运行 (http://localhost:8668)")
    
    cache_manager = get_cache_manager()
    
    for symbol in symbols:
        print(f"\n📋 {symbol} - gexbot 命令清单:")
        print("-" * 40)
        
        commands = [
            f"!trigger {symbol} 98",
            f"!gexr {symbol} 15 98",
            f"!vexn {symbol} 15 190 *",
            f"!surface {symbol} ivmid 98",
            f"!surface {symbol} spread atm 98",
            f"!skew {symbol} ivmid atm 30",
        ]
        
        if args.event in ["earnings", "fomc"]:
            commands.append(f"!surface {symbol} extrinsic ntm 45 w")
        
        for cmd in commands:
            print(f"  {cmd}")
        
        print("-" * 40)
        
        # 获取市场参数
        market_params = None
        if va_available:
            try:
                print(f"\n📡 获取 {symbol} 市场参数...")
                market_params = fetch_market_params(symbol, vix=vix, date=date)
                
                print(f"  VIX: {market_params.get('vix', 'N/A')}")
                print(f"  IVR: {market_params.get('ivr', 'N/A')}")
                print(f"  IV30: {market_params.get('iv30', 'N/A')}")
                print(f"  HV20: {market_params.get('hv20', 'N/A')}")
                
                # 计算 VRP
                iv30 = market_params.get('iv30')
                hv20 = market_params.get('hv20')
                if iv30 and hv20 and hv20 > 0:
                    vrp = (iv30 - hv20) / hv20
                    market_params['vrp'] = vrp
                    print(f"  VRP: {vrp:.2%}")
                
                # IV Path (简化判断)
                market_params['iv_path'] = "Rising" if market_params.get('ivr', 50) > 50 else "Falling"
                market_params['updated_at'] = datetime.now().isoformat()
                
            except VAClientError as e:
                print(f"  ⚠️  获取参数失败: {e}")
        
        # 创建缓存
        if market_params:
            cache_data = cache_manager.create_initial_cache(
                symbol=symbol,
                date=date,
                market_params=market_params,
                tag="Meso"
            )
            cache_path = cache_manager.get_cache_path(symbol, date)
            print(f"\n💾 已缓存: {cache_path}")
        else:
            # 创建空的缓存结构
            empty_params = {
                'vix': vix,
                'ivr': None,
                'iv30': None,
                'hv20': None,
                'vrp': None,
                'iv_path': None,
                'updated_at': datetime.now().isoformat()
            }
            cache_manager.create_initial_cache(
                symbol=symbol,
                date=date,
                market_params=empty_params,
                tag="Meso"
            )
            cache_path = cache_manager.get_cache_path(symbol, date)
            print(f"\n💾 已创建缓存结构: {cache_path}")
    
    print(f"\n下一步: 执行命令，填充 data/input/{{SYMBOL}}.json，然后运行 create")
    return 0


def resolve_input_path(path: str, data_dir: str = "data/input") -> str:
    """
    解析输入文件路径，支持省略目录前缀
    
    示例:
        TSLA_i_2026-01-03.json -> data/input/TSLA_i_2026-01-03.json
        data/input/TSLA.json -> data/input/TSLA.json (不变)
    """
    if not path:
        return None
    
    # 如果已包含路径分隔符，视为完整路径
    if '/' in path or '\\' in path:
        return path
    
    # 否则添加前缀
    return f"{data_dir}/{path}"


def resolve_cache_path(path: str, output_dir: str = "data/output") -> str:
    """
    解析缓存文件路径，支持省略目录前缀
    
    文件名格式: {symbol}_o_{date}.json
    
    示例:
        TSLA_o_2026-01-03.json -> data/output/TSLA/2026-01-03/TSLA_o_2026-01-03.json
        data/output/TSLA/2026-01-03/TSLA_o_2026-01-03.json -> 不变
    """
    if not path:
        return None
    
    # 如果已包含路径分隔符，视为完整路径
    if '/' in path or '\\' in path:
        return path
    
    # 从文件名解析 symbol 和 date
    # 格式: TSLA_o_2026-01-03.json
    match = re.match(r'^([A-Z]+)_o_(\d{4}-\d{2}-\d{2})\.json$', path, re.IGNORECASE)
    if match:
        symbol = match.group(1).upper()
        date = match.group(2)
        return f"{output_dir}/{symbol}/{date}/{path}"
    
    # 无法解析，返回原路径
    return f"{output_dir}/{path}"


def parse_file_info(path: str) -> tuple:
    """
    从文件路径解析 symbol 和 date
    
    Returns:
        (symbol, date) 或 (None, None)
    """
    filename = Path(path).name
    
    # 尝试匹配 symbol_i_date.json 或 symbol_o_date.json
    match = re.match(r'^([A-Z]+)_[io]_(\d{4}-\d{2}-\d{2})\.json$', filename, re.IGNORECASE)
    if match:
        return match.group(1).upper(), match.group(2)
    
    # 尝试匹配 symbol.json
    match = re.match(r'^([A-Z]+)\.json$', filename, re.IGNORECASE)
    if match:
        return match.group(1).upper(), None
    
    return None, None


def run_create(symbols: list, args):
    """执行 CREATE 模式"""
    date = args.datetime or datetime.now().strftime('%Y-%m-%d')
    data_dir = args.data_dir or "data/input"
    output_dir = args.output_dir or "data/output"
    
    # 解析 -i 和 -c 路径
    input_file = resolve_input_path(args.input, data_dir) if args.input else None
    cache_file = resolve_cache_path(args.cache, output_dir) if args.cache else None
    
    # 如果指定了 -i 或 -c，尝试从文件名解析 symbol 和 date
    if input_file:
        parsed_symbol, parsed_date = parse_file_info(input_file)
        if parsed_symbol and parsed_symbol not in symbols:
            symbols = [parsed_symbol]
        if parsed_date:
            date = parsed_date
    
    if cache_file:
        parsed_symbol, parsed_date = parse_file_info(cache_file)
        if parsed_symbol and parsed_symbol not in symbols:
            symbols = [parsed_symbol]
        if parsed_date:
            date = parsed_date
    
    print_header("CREATE", symbols)
    
    # 显示文件路径
    if input_file:
        print(f"   输入: {input_file}")
    if cache_file:
        print(f"   缓存: {cache_file}")
    
    pipeline = create_pipeline(
        data_dir=data_dir,
        output_dir=output_dir
    )
    
    cache_manager = get_cache_manager(output_dir)
    
    for symbol in symbols:
        if len(symbols) > 1:
            print(f"\n{'='*40}")
            print(f">>> {symbol}")
            print(f"{'='*40}")
        
        # 添加进度钩子
        def progress_hook(stage, ctx):
            stage_names = {
                "load_data": "📂 加载数据",
                "validate": "🔍 校验字段",
                "calculate_features": "📊 计算特征",
                "calculate_scores": "🎯 计算评分",
                "make_decision": "🤖 生成决策",
                "generate_strategy": "🎮 生成策略",
                "estimate_edge": "💰 估计 Edge",
            }
            name = stage_names.get(stage.value, stage.value)
            print(f"\n{name}...")
        
        pipeline.hooks["before_stage"] = [progress_hook]
        
        # 确定数据文件路径
        data_file = input_file or args.data_file
        
        # 执行流程
        ctx = pipeline.run(
            symbol=symbol,
            event_type=args.event or "none",
            data_file=data_file,
            iv=args.iv,
            hv=args.hv,
            skip_edge=args.skip_edge
        )
        
        # 检查错误
        failed_stages = [r for r in ctx.stage_results if not r.success]
        if failed_stages:
            print(f"\n❌ 流程失败于 {failed_stages[0].stage.value}: {failed_stages[0].error}")
            continue
        
        # 打印结果
        print_result(ctx)
        
        # 更新缓存
        try:
            # 检查是否有现有缓存
            cache = cache_manager.load_cache(symbol, date)
            if cache is None:
                # 创建新缓存
                market_params = {
                    'vix': None,
                    'ivr': None,
                    'iv30': ctx.market_data.iv_atm if ctx.market_data else None,
                    'hv20': ctx.market_data.hv20 if ctx.market_data else None,
                    'vrp': ctx.features.vrp_selected if ctx.features else None,
                    'updated_at': datetime.now().isoformat()
                }
                cache = cache_manager.create_initial_cache(symbol, date, market_params)
            
            # 更新各步骤数据
            if ctx.features:
                cache_manager.update_step(symbol, date, "step3_features", serialize_dataclass(ctx.features))
            
            if ctx.scores:
                cache_manager.update_step(symbol, date, "step4_scores", serialize_dataclass(ctx.scores))
            
            if ctx.decision:
                cache_manager.update_step(symbol, date, "step5_decision", serialize_dataclass(ctx.decision))
            
            if ctx.strategy:
                cache_manager.update_step(symbol, date, "step6_strategy", serialize_dataclass(ctx.strategy))
            
            if ctx.edge:
                cache_manager.update_step(symbol, date, "step7_edge", serialize_dataclass(ctx.edge))
            
            # step8_report (汇总)
            report = {
                "symbol": symbol,
                "date": date,
                "decision": ctx.decision.decision.value if ctx.decision else None,
                "confidence": ctx.decision.confidence.value if ctx.decision else None,
                "strategy": ctx.strategy.name if ctx.strategy else None,
                "data_quality": ctx.validation_summary.get("data_quality_score") if ctx.validation_summary else None,
            }
            cache_manager.update_step(symbol, date, "step8_report", report)
            
            cache_path = cache_manager.get_cache_path(symbol, date)
            print(f"\n💾 结果已缓存: {cache_path}")
            
        except Exception as e:
            print(f"\n⚠️  缓存更新失败: {e}")
    
    print("\n✅ 分析完成!")
    return 0


def run_update(symbols: list, args):
    """执行 UPDATE 模式"""
    date = args.datetime or datetime.now().strftime('%Y-%m-%d')
    data_dir = args.data_dir or "data/input"
    output_dir = args.output_dir or "data/output"
    
    # 解析 -i 和 -c 路径
    input_file = resolve_input_path(args.input, data_dir) if args.input else None
    cache_file = resolve_cache_path(args.cache, output_dir) if args.cache else None
    
    # 如果指定了 -i 或 -c，尝试从文件名解析 symbol 和 date
    if input_file:
        parsed_symbol, parsed_date = parse_file_info(input_file)
        if parsed_symbol and parsed_symbol not in symbols:
            symbols = [parsed_symbol]
        if parsed_date:
            date = parsed_date
    
    if cache_file:
        parsed_symbol, parsed_date = parse_file_info(cache_file)
        if parsed_symbol and parsed_symbol not in symbols:
            symbols = [parsed_symbol]
        if parsed_date:
            date = parsed_date
    
    print_header("UPDATE", symbols)
    
    # 显示文件路径
    if input_file:
        print(f"   输入: {input_file}")
    if cache_file:
        print(f"   缓存: {cache_file}")
    
    pipeline = create_pipeline(
        data_dir=data_dir
    )
    
    cache_manager = get_cache_manager(output_dir)
    
    for symbol in symbols:
        if len(symbols) > 1:
            print(f"\n>>> {symbol}")
        
        # 确定数据文件路径
        data_file = input_file or args.data_file
        
        ctx = pipeline.run_update(
            symbol=symbol,
            data_file=data_file
        )
        
        # 检查错误
        failed_stages = [r for r in ctx.stage_results if not r.success]
        if failed_stages:
            print(f"❌ {symbol} 更新失败: {failed_stages[0].error}")
            continue
        
        print_result(ctx)
        
        # 更新缓存
        try:
            cache = cache_manager.load_cache(symbol, date)
            if cache and ctx.scores:
                cache_manager.update_step(symbol, date, "step4_scores", serialize_dataclass(ctx.scores))
                print(f"💾 缓存已更新")
        except Exception as e:
            print(f"⚠️  缓存更新失败: {e}")
    
    print("\n✅ 更新完成!")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="波动率交易分析系统 v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s cmd AAPL                    # 生成命令
  %(prog)s cmd AAPL -v 18.5            # 带 VIX 参数
  %(prog)s create AAPL                 # 完整分析
  %(prog)s create AAPL -i AAPL_i_2026-01-03.json   # 指定输入文件
  %(prog)s create AAPL -c AAPL_o_2026-01-03.json   # 指定缓存文件
  %(prog)s update AAPL -i AAPL.json    # 快速更新

文件路径:
  -i 支持省略 data/input/ 前缀
  -c 支持省略 data/output/SYMBOL/DATE/ 前缀
        """
    )
    
    # 位置参数
    parser.add_argument(
        "command",
        choices=["cmd", "create", "update"],
        help="命令: cmd=生成命令, create=完整分析, update=快速更新"
    )
    parser.add_argument(
        "symbols",
        nargs="+",
        help="股票代码列表"
    )
    
    # 文件参数
    parser.add_argument("-i", "--input", 
                       help="输入文件路径 (可省略 data/input/ 前缀)")
    parser.add_argument("-c", "--cache", 
                       help="缓存文件路径 (可省略 data/output/SYMBOL/DATE/ 前缀)")
    
    # 其他参数
    parser.add_argument("-v", "--vix", type=float, help="VIX 指数")
    parser.add_argument("-t", "--datetime", help="日期 (YYYY-MM-DD)")
    parser.add_argument("-e", "--event", 
                       choices=["earnings", "fomc", "opex", "none"],
                       help="事件类型")
    parser.add_argument("-d", "--data-file", help="数据文件路径 (已废弃，请使用 -i)")
    parser.add_argument("--data-dir", help="数据目录")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--iv", type=float, default=0.28, help="IV (默认 0.28)")
    parser.add_argument("--hv", type=float, default=0.25, help="HV (默认 0.25)")
    parser.add_argument("--skip-edge", action="store_true", help="跳过 Edge 计算")
    
    args = parser.parse_args()
    
    # 转换 symbols 为大写
    symbols = [s.upper() for s in args.symbols]
    
    # 执行命令
    if args.command == "cmd":
        return run_cmd(symbols, args)
    elif args.command == "create":
        return run_create(symbols, args)
    elif args.command == "update":
        return run_update(symbols, args)


if __name__ == "__main__":
    sys.exit(main() or 0)
