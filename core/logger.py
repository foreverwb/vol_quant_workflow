"""
统一日志系统

提供:
- 彩色控制台输出
- 文件日志记录
- 错误收集器
- 节点执行追踪
"""
import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from functools import wraps
from contextlib import contextmanager

# 尝试导入 rich，提供更好的控制台输出
try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# ============================================================
# 日志格式化
# ============================================================

class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器 (不依赖 rich)"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 添加颜色
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON 格式日志 (用于生产环境/日志聚合)"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加额外数据
        if hasattr(record, 'node_name'):
            log_data['node_name'] = record.node_name
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration
        if hasattr(record, 'data'):
            log_data['data'] = record.data
            
        # 异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False, default=str)


# ============================================================
# 错误收集器
# ============================================================

@dataclass
class ErrorRecord:
    """错误记录"""
    timestamp: str
    level: str
    node_name: str
    message: str
    exception: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class ErrorCollector:
    """
    错误收集器
    
    收集工作流执行过程中的所有错误，支持导出和分析
    """
    _instance: Optional['ErrorCollector'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._errors: List[ErrorRecord] = []
            cls._instance._warnings: List[ErrorRecord] = []
        return cls._instance
    
    def add_error(
        self, 
        message: str, 
        node_name: str = "",
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """添加错误记录"""
        record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            level="ERROR",
            node_name=node_name,
            message=message,
            exception=str(exception) if exception else None,
            context=context or {}
        )
        self._errors.append(record)
    
    def add_warning(
        self, 
        message: str, 
        node_name: str = "",
        context: Optional[Dict[str, Any]] = None
    ):
        """添加警告记录"""
        record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            level="WARNING",
            node_name=node_name,
            message=message,
            context=context or {}
        )
        self._warnings.append(record)
    
    def get_errors(self) -> List[ErrorRecord]:
        """获取所有错误"""
        return self._errors.copy()
    
    def get_warnings(self) -> List[ErrorRecord]:
        """获取所有警告"""
        return self._warnings.copy()
    
    def get_all(self) -> List[ErrorRecord]:
        """获取所有记录"""
        return self._errors + self._warnings
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self._errors) > 0
    
    def clear(self):
        """清空所有记录"""
        self._errors.clear()
        self._warnings.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "error_count": len(self._errors),
            "warning_count": len(self._warnings),
            "errors": [
                {
                    "timestamp": e.timestamp,
                    "node": e.node_name,
                    "message": e.message,
                    "exception": e.exception,
                    "context": e.context
                }
                for e in self._errors
            ],
            "warnings": [
                {
                    "timestamp": w.timestamp,
                    "node": w.node_name,
                    "message": w.message,
                    "context": w.context
                }
                for w in self._warnings
            ]
        }
    
    def export_to_file(self, filepath: str):
        """导出到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


# 全局错误收集器实例
error_collector = ErrorCollector()


# ============================================================
# 日志配置
# ============================================================

class LogConfig:
    """日志配置"""
    
    def __init__(
        self,
        level: str = "INFO",
        log_to_file: bool = False,
        log_dir: str = "./logs",
        log_filename: Optional[str] = None,
        json_format: bool = False,
        show_data: bool = True,
        max_data_length: int = 500
    ):
        """
        初始化日志配置
        
        Args:
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
            log_to_file: 是否写入文件
            log_dir: 日志目录
            log_filename: 日志文件名 (默认按日期)
            json_format: 是否使用 JSON 格式
            show_data: 是否显示详细数据
            max_data_length: 数据显示最大长度
        """
        self.level = level.upper()
        self.log_to_file = log_to_file
        self.log_dir = Path(log_dir)
        self.log_filename = log_filename
        self.json_format = json_format
        self.show_data = show_data
        self.max_data_length = max_data_length


def setup_logging(config: Optional[LogConfig] = None) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        config: 日志配置，默认为 INFO 级别控制台输出
        
    Returns:
        配置好的 logger 实例
    """
    config = config or LogConfig()
    
    # 创建 logger
    logger = logging.getLogger("vol_workflow")
    logger.setLevel(getattr(logging, config.level))
    
    # 清除已有 handlers
    logger.handlers.clear()
    
    # 控制台 Handler
    if RICH_AVAILABLE and not config.json_format:
        # 使用 Rich 美化输出
        console_handler = RichHandler(
            console=Console(stderr=True),
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=True
        )
        console_handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        if config.json_format:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(ColoredFormatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%H:%M:%S"
            ))
    
    console_handler.setLevel(getattr(logging, config.level))
    logger.addHandler(console_handler)
    
    # 文件 Handler
    if config.log_to_file:
        config.log_dir.mkdir(parents=True, exist_ok=True)
        
        if config.log_filename:
            log_file = config.log_dir / config.log_filename
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = config.log_dir / f"workflow_{date_str}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        
        if config.json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
        
        logger.addHandler(file_handler)
    
    return logger


# 默认 logger
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """获取全局 logger"""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


# ============================================================
# 节点日志工具
# ============================================================

class NodeLogger:
    """
    节点专用日志器
    
    提供节点执行的详细日志输出
    """
    
    def __init__(self, node_name: str, logger: Optional[logging.Logger] = None):
        self.node_name = node_name
        self.logger = logger or get_logger()
        self.console = Console() if RICH_AVAILABLE else None
        self._start_time: Optional[datetime] = None
    
    def start(self, message: str = ""):
        """记录节点开始执行"""
        self._start_time = datetime.now()
        msg = f"[{self.node_name}] 开始执行"
        if message:
            msg += f": {message}"
        self.logger.info(msg)
    
    def end(self, success: bool = True, message: str = ""):
        """记录节点执行结束"""
        duration = 0.0
        if self._start_time:
            duration = (datetime.now() - self._start_time).total_seconds()
        
        status = "✓ 成功" if success else "✗ 失败"
        msg = f"[{self.node_name}] {status} (耗时: {duration:.2f}s)"
        if message:
            msg += f" - {message}"
        
        if success:
            self.logger.info(msg)
        else:
            self.logger.error(msg)
            error_collector.add_error(message, self.node_name)
    
    def log_input(self, data: Any, label: str = "输入"):
        """记录输入数据"""
        self._log_data(data, label, "cyan")
    
    def log_output(self, data: Any, label: str = "输出"):
        """记录输出数据"""
        self._log_data(data, label, "green")
    
    def log_llm_response(self, response: Any, model: str = ""):
        """记录 LLM 响应"""
        if RICH_AVAILABLE and self.console:
            self.console.print(Panel(
                self._format_data(response),
                title=f"[bold blue]🤖 LLM Response ({model})[/]",
                border_style="blue"
            ))
        else:
            self.logger.info(f"[{self.node_name}] LLM Response ({model}):")
            self.logger.info(self._truncate(str(response)))
    
    def log_code_result(self, result: Any, label: str = "计算结果"):
        """记录代码节点计算结果"""
        if RICH_AVAILABLE and self.console:
            self.console.print(Panel(
                self._format_data(result),
                title=f"[bold yellow]⚙️ {label}[/]",
                border_style="yellow"
            ))
        else:
            self.logger.info(f"[{self.node_name}] {label}:")
            self.logger.info(self._truncate(str(result)))
    
    def log_structured_output(self, data: Dict[str, Any], schema_name: str = ""):
        """记录结构化输出"""
        title = f"📋 Structured Output"
        if schema_name:
            title += f" ({schema_name})"
        
        if RICH_AVAILABLE and self.console:
            # 使用 JSON 语法高亮
            json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            self.console.print(Panel(syntax, title=f"[bold magenta]{title}[/]", border_style="magenta"))
        else:
            self.logger.info(f"[{self.node_name}] {title}:")
            self.logger.info(json.dumps(data, ensure_ascii=False, indent=2, default=str)[:1000])
    
    def log_table(self, headers: List[str], rows: List[List[Any]], title: str = ""):
        """记录表格数据"""
        if RICH_AVAILABLE and self.console:
            table = Table(title=title, show_header=True, header_style="bold cyan")
            for header in headers:
                table.add_column(header)
            for row in rows:
                table.add_row(*[str(cell) for cell in row])
            self.console.print(table)
        else:
            self.logger.info(f"[{self.node_name}] {title}")
            self.logger.info(f"  {' | '.join(headers)}")
            for row in rows:
                self.logger.info(f"  {' | '.join(str(cell) for cell in row)}")
    
    def warning(self, message: str, context: Optional[Dict] = None):
        """记录警告"""
        self.logger.warning(f"[{self.node_name}] ⚠️ {message}")
        error_collector.add_warning(message, self.node_name, context)
    
    def error(self, message: str, exception: Optional[Exception] = None, context: Optional[Dict] = None):
        """记录错误"""
        self.logger.error(f"[{self.node_name}] ❌ {message}")
        if exception:
            self.logger.exception(exception)
        error_collector.add_error(message, self.node_name, exception, context)
    
    def debug(self, message: str):
        """调试日志"""
        self.logger.debug(f"[{self.node_name}] {message}")
    
    def info(self, message: str):
        """信息日志"""
        self.logger.info(f"[{self.node_name}] {message}")
    
    def _log_data(self, data: Any, label: str, color: str):
        """记录数据"""
        if RICH_AVAILABLE and self.console:
            self.console.print(f"[bold {color}][{self.node_name}] {label}:[/]")
            self.console.print(self._format_data(data))
        else:
            self.logger.info(f"[{self.node_name}] {label}:")
            self.logger.info(self._truncate(str(data)))
    
    def _format_data(self, data: Any) -> str:
        """格式化数据用于显示"""
        if isinstance(data, dict):
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        elif isinstance(data, (list, tuple)):
            return json.dumps(list(data), ensure_ascii=False, indent=2, default=str)
        else:
            return str(data)
    
    def _truncate(self, text: str, max_length: int = 500) -> str:
        """截断过长文本"""
        if len(text) > max_length:
            return text[:max_length] + "... [truncated]"
        return text


# ============================================================
# 装饰器和上下文管理器
# ============================================================

def log_node_execution(node_name: str):
    """
    节点执行日志装饰器
    
    Usage:
        @log_node_execution("router")
        async def execute(self, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            node_logger = NodeLogger(node_name)
            node_logger.start()
            try:
                result = await func(*args, **kwargs)
                node_logger.end(success=True)
                return result
            except Exception as e:
                node_logger.end(success=False, message=str(e))
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            node_logger = NodeLogger(node_name)
            node_logger.start()
            try:
                result = func(*args, **kwargs)
                node_logger.end(success=True)
                return result
            except Exception as e:
                node_logger.end(success=False, message=str(e))
                raise
        
        # 判断是否为异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


@contextmanager
def log_step(step_name: str, node_name: str = "workflow"):
    """
    步骤日志上下文管理器
    
    Usage:
        with log_step("Step 1: Router", "workflow"):
            result = await router.execute(...)
    """
    node_logger = NodeLogger(node_name)
    node_logger.start(step_name)
    try:
        yield node_logger
        node_logger.end(success=True)
    except Exception as e:
        node_logger.end(success=False, message=str(e))
        raise


# ============================================================
# 便捷函数
# ============================================================

def print_workflow_summary(context: Any):
    """
    打印工作流执行摘要
    
    Args:
        context: WorkflowContext 实例
    """
    logger = get_logger()
    
    if RICH_AVAILABLE:
        console = Console()
        console.print("\n")
        console.print(Panel(
            f"[bold]Status:[/] {context.status.value}\n"
            f"[bold]Route:[/] {context.route_type}\n"
            f"[bold]Timestamp:[/] {context.timestamp}\n"
            f"[bold]Errors:[/] {len(context.errors)}",
            title="[bold green]📊 Workflow Summary[/]",
            border_style="green"
        ))
    else:
        logger.info("=" * 50)
        logger.info("Workflow Summary")
        logger.info(f"  Status: {context.status.value}")
        logger.info(f"  Route: {context.route_type}")
        logger.info(f"  Timestamp: {context.timestamp}")
        logger.info(f"  Errors: {len(context.errors)}")
        logger.info("=" * 50)


def print_error_summary():
    """打印错误摘要"""
    logger = get_logger()
    errors = error_collector.get_errors()
    warnings = error_collector.get_warnings()
    
    if not errors and not warnings:
        logger.info("✅ No errors or warnings")
        return
    
    if RICH_AVAILABLE:
        console = Console()
        
        if errors:
            table = Table(title="❌ Errors", show_header=True, header_style="bold red")
            table.add_column("Time", style="dim")
            table.add_column("Node")
            table.add_column("Message")
            
            for e in errors:
                table.add_row(e.timestamp.split("T")[1][:8], e.node_name, e.message[:50])
            
            console.print(table)
        
        if warnings:
            table = Table(title="⚠️ Warnings", show_header=True, header_style="bold yellow")
            table.add_column("Time", style="dim")
            table.add_column("Node")
            table.add_column("Message")
            
            for w in warnings:
                table.add_row(w.timestamp.split("T")[1][:8], w.node_name, w.message[:50])
            
            console.print(table)
    else:
        if errors:
            logger.error(f"Errors ({len(errors)}):")
            for e in errors:
                logger.error(f"  [{e.node_name}] {e.message}")
        
        if warnings:
            logger.warning(f"Warnings ({len(warnings)}):")
            for w in warnings:
                logger.warning(f"  [{w.node_name}] {w.message}")