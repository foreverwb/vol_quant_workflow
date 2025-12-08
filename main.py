#!/usr/bin/env python3
"""
波动率套利策略工作流 - 主入口
支持命令行和编程接口

使用方法:
    # 命令行 - 处理单个标的
    python main.py --input "NVDA 财报 5-20DTE delta-neutral"
    
    # 命令行 - 处理图表文件夹
    python main.py --folder ./charts --output ./reports
    
    # 命令行 - 处理指定图片
    python main.py --files img1.png img2.png img3.png
    
    # 编程接口
    from main import run_workflow
    result = run_workflow(files=["chart1.png", "chart2.png"])
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional, List

# 支持两种运行方式：作为脚本直接运行，或作为包的一部分
try:
    from .config import ModelConfig, WorkflowConfig
    from .workflow import VolatilityWorkflow, BatchProcessor, create_workflow
except ImportError:
    # 作为脚本直接运行时
    sys.path.insert(0, str(Path(__file__).parent))
    from config import ModelConfig, WorkflowConfig
    from workflow import VolatilityWorkflow, BatchProcessor, create_workflow


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="波动率套利策略工作流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 输入变量，生成命令清单
    python main.py --input "NVDA 财报 5-20DTE delta-neutral"
    
    # 处理图表文件
    python main.py --files chart1.png chart2.png
    
    # 批量处理文件夹
    python main.py --folder ./charts --output ./reports
    
    # 指定模型配置
    python main.py --api-base https://api.openai.com/v1 \\
                   --api-key sk-xxx \\
                   --model gpt-4o \\
                   --files chart1.png chart2.png
        """
    )
    
    # 输入选项
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input", "-i",
        type=str,
        help="输入变量文本 (标的代码、事件类型等)"
    )
    input_group.add_argument(
        "--files", "-f",
        nargs="+",
        help="图表文件路径列表"
    )
    input_group.add_argument(
        "--folder",
        type=str,
        help="图表文件夹路径 (批量处理)"
    )
    
    # 输出选项
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./outputs",
        help="输出目录 (默认: ./outputs)"
    )
    
    # 模型配置
    parser.add_argument(
        "--api-base",
        type=str,
        default=os.getenv("LLM_API_BASE", ""),
        help="API基础URL (或设置 LLM_API_BASE 环境变量)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("LLM_API_KEY", ""),
        help="API密钥 (或设置 LLM_API_KEY 环境变量)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("LLM_MODEL", "gpt-4o"),
        help="模型名称 (默认: gpt-4o)"
    )
    parser.add_argument(
        "--vision-model",
        type=str,
        help="视觉模型名称 (默认与--model相同)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="温度参数 (默认: 0.7)"
    )
    
    # 批量处理选项
    parser.add_argument(
        "--min-files",
        type=int,
        default=10,
        help="批量处理时每个标的最少文件数 (默认: 10)"
    )
    
    # 其他选项
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以JSON格式输出结果"
    )
    
    return parser.parse_args()


def run_workflow(
    user_input: str = "",
    files: Optional[List[str]] = None,
    api_base: str = "",
    api_key: str = "",
    model_name: str = "gpt-4o",
    vision_model_name: Optional[str] = None,
    temperature: float = 0.7,
    output_dir: str = "./outputs"
) -> dict:
    """
    运行工作流的便捷函数
    
    Args:
        user_input: 用户输入文本
        files: 图表文件列表
        api_base: API基础URL
        api_key: API密钥
        model_name: 模型名称
        vision_model_name: 视觉模型名称
        temperature: 温度参数
        output_dir: 输出目录
        
    Returns:
        工作流执行结果
    """
    workflow = create_workflow(
        api_base=api_base,
        api_key=api_key,
        model_name=model_name,
        vision_model_name=vision_model_name,
        temperature=temperature
    )
    
    result = workflow.run_sync(user_input=user_input, files=files)
    
    # 保存输出
    if result.get("status") == "completed":
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        symbol = result.get("summary", {}).get("symbol", "unknown")
        
        # 保存报告
        report_path = output_path / f"{symbol}_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(result.get("report", ""))
        
        result["output_files"] = {
            "report": str(report_path)
        }
    
    return result


def run_batch(
    folder_path: str,
    api_base: str = "",
    api_key: str = "",
    model_name: str = "gpt-4o",
    vision_model_name: Optional[str] = None,
    temperature: float = 0.7,
    output_dir: str = "./outputs",
    min_files: int = 10
) -> dict:
    """
    批量处理文件夹
    
    Args:
        folder_path: 图表文件夹路径
        其他参数同 run_workflow
        
    Returns:
        批量处理结果
    """
    workflow = create_workflow(
        api_base=api_base,
        api_key=api_key,
        model_name=model_name,
        vision_model_name=vision_model_name,
        temperature=temperature
    )
    
    processor = BatchProcessor(workflow, output_dir)
    return processor.process_folder_sync(folder_path, min_files)


def main():
    """主入口"""
    args = parse_args()
    
    # 检查API配置
    if not args.api_base:
        print("错误: 请通过 --api-base 或环境变量 LLM_API_BASE 指定API地址")
        print("示例: export LLM_API_BASE=https://api.openai.com/v1")
        sys.exit(1)
    
    try:
        if args.folder:
            # 批量处理模式
            print(f"批量处理文件夹: {args.folder}")
            result = run_batch(
                folder_path=args.folder,
                api_base=args.api_base,
                api_key=args.api_key,
                model_name=args.model,
                vision_model_name=args.vision_model,
                temperature=args.temperature,
                output_dir=args.output,
                min_files=args.min_files
            )
        else:
            # 单次运行模式
            result = run_workflow(
                user_input=args.input or "",
                files=args.files,
                api_base=args.api_base,
                api_key=args.api_key,
                model_name=args.model,
                vision_model_name=args.vision_model,
                temperature=args.temperature,
                output_dir=args.output
            )
        
        # 输出结果
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            status = result.get("status", "unknown")
            print(f"\n状态: {status}")
            
            if status == "completed":
                print(f"\n{'='*60}")
                print("决策报告:")
                print('='*60)
                print(result.get("report", ""))
                
                summary = result.get("summary", {})
                print(f"\n{'='*60}")
                print("摘要:")
                print(f"  标的: {summary.get('symbol', 'N/A')}")
                print(f"  方向: {summary.get('direction', 'N/A')}")
                print(f"  做多评分: {summary.get('long_score', 'N/A')}")
                print(f"  做空评分: {summary.get('short_score', 'N/A')}")
                print(f"  策略数量: {summary.get('strategies_count', 0)}")
                
            elif status == "waiting_data":
                print(f"\n{result.get('message', '')}")
                print(f"\n命令清单:\n{result.get('commands', '')}")
                
            elif status == "missing_data":
                print(f"\n{result.get('message', '')}")
                missing = result.get('missing_fields', [])
                for field in missing:
                    print(f"  - {field.get('field')}: {field.get('command', 'N/A')}")
                    
            else:
                print(f"\n消息: {result.get('message', 'N/A')}")
                if result.get('errors'):
                    print(f"错误: {result.get('errors')}")
                    
    except Exception as e:
        print(f"错误: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
