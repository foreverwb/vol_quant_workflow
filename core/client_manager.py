"""
LLM 客户端管理器

负责:
- 根据配置创建 LLM 客户端
- 客户端缓存管理
- 支持多种配置方式 (YAML / NodeModelMapping / 默认)
"""
from typing import Dict, Optional, Set, TYPE_CHECKING, Any

# 类型检查时导入（避免循环导入和运行时问题）
if TYPE_CHECKING:
    from ..config.model_config_loader import ModelsConfig, NodeConfig

try:
    from ..config import ModelConfig, NodeModelMapping, WorkflowConfig
    from ..config.model_config_loader import ModelsConfig as ModelsConfigClass, NodeConfig as NodeConfigClass
    from ..utils.llm_client import LLMClient
except ImportError:
    # 当作为独立脚本运行时的 fallback
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import ModelConfig, NodeModelMapping, WorkflowConfig
    try:
        from config.model_config_loader import ModelsConfig as ModelsConfigClass, NodeConfig as NodeConfigClass
    except ImportError:
        ModelsConfigClass = None
        NodeConfigClass = None
    from utils.llm_client import LLMClient


class ClientManager:
    """
    LLM 客户端管理器
    
    支持三种配置方式:
    1. YAML 配置文件 (ModelsConfig)
    2. 节点模型映射 (NodeModelMapping)
    3. 默认配置 (ModelConfig)
    """
    
    # 默认的视觉节点
    DEFAULT_VISION_NODES: Set[str] = {"data_validator"}
    
    def __init__(
        self,
        config: Any,  # 可以是 WorkflowConfig 或 ModelConfig
        logger: Any = None,
        models_config: Optional["ModelsConfig"] = None,
        node_model_mapping: Optional[NodeModelMapping] = None
    ):
        """
        初始化客户端管理器
        
        Args:
            config: 工作流配置 (WorkflowConfig) 或模型配置 (ModelConfig)
            logger: 日志记录器
            models_config: YAML 配置实例 (优先级最高)
            node_model_mapping: 节点模型映射
        """
        self.logger = logger
        self._models_config = models_config
        self._node_model_mapping = node_model_mapping
        self._initialized = False
        
        # 客户端缓存
        self._cache: Dict[str, LLMClient] = {}
        
        # 处理不同类型的配置
        if isinstance(config, WorkflowConfig):
            self.workflow_config = config
            self.model_config = config.model_config or ModelConfig()
            self.vision_model_config = config.vision_model_config or self.model_config
        elif isinstance(config, ModelConfig):
            self.workflow_config = None
            self.model_config = config
            self.vision_model_config = config
        else:
            # 兜底处理
            self.workflow_config = config
            self.model_config = getattr(config, 'model_config', None) or ModelConfig()
            self.vision_model_config = getattr(config, 'vision_model_config', None) or self.model_config
        
        # 创建默认客户端（延迟初始化）
        self._default_text_client: Optional[LLMClient] = None
        self._default_vision_client: Optional[LLMClient] = None
    
    async def initialize(self) -> None:
        """初始化客户端管理器"""
        if self._initialized:
            return
        
        # 创建默认客户端
        self._default_text_client = LLMClient(self.model_config)
        self._default_vision_client = (
            LLMClient(self.vision_model_config) 
            if self.vision_model_config != self.model_config 
            else self._default_text_client
        )
        
        # 缓存默认客户端
        self._cache[f"default:text:{self.model_config.name}"] = self._default_text_client
        if self.vision_model_config != self.model_config:
            self._cache[f"default:vision:{self.vision_model_config.name}"] = self._default_vision_client
        
        self._initialized = True
        if self.logger:
            self.logger.info("ClientManager initialized")
    
    async def close(self) -> None:
        """关闭所有客户端"""
        await self.close_all()
        self._initialized = False
        if self.logger:
            self.logger.info("ClientManager closed")
    
    @property
    def text_client(self) -> LLMClient:
        """获取默认文本客户端"""
        if self._default_text_client is None:
            self._default_text_client = LLMClient(self.model_config)
        return self._default_text_client
    
    @property
    def vision_client(self) -> LLMClient:
        """获取默认视觉客户端"""
        if self._default_vision_client is None:
            self._default_vision_client = LLMClient(self.vision_model_config)
        return self._default_vision_client
    
    def get_client(self, node_name: str) -> LLMClient:
        """
        获取指定节点的 LLM 客户端
        
        配置优先级:
        1. YAML 配置文件
        2. NodeModelMapping
        3. 默认客户端
        
        Args:
            node_name: 节点名称
            
        Returns:
            LLMClient 实例
        """
        # 优先使用 YAML 配置
        if self._models_config:
            return self._get_client_from_yaml(node_name)
        
        # 退回到 NodeModelMapping
        if self._node_model_mapping:
            return self._get_client_from_mapping(node_name)
        
        # 使用默认客户端
        if node_name in self.DEFAULT_VISION_NODES:
            return self.vision_client
        return self.text_client
    
    async def chat_completion(self, messages: list, **kwargs) -> Any:
        """
        便捷方法：使用默认客户端进行聊天
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            LLM 响应
        """
        from ..utils.llm_client import Message
        
        # 转换消息格式
        msg_objects = []
        for msg in messages:
            if isinstance(msg, dict):
                msg_objects.append(Message(
                    role=msg.get("role", "user"),
                    content=msg.get("content", "")
                ))
            else:
                msg_objects.append(msg)
        
        return await self.text_client.chat(messages=msg_objects, **kwargs)
    
    def _get_client_from_yaml(self, node_name: str) -> LLMClient:
        """从 YAML 配置创建客户端"""
        node_cfg = self._models_config.get_node_config(node_name)
        
        cache_key = f"yaml:{node_name}:{node_cfg.model}:{node_cfg.vision_enabled}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 创建 ModelConfig
        config = ModelConfig(
            name=node_cfg.model,
            api_base=node_cfg.api_base or self.model_config.api_base,
            api_key=node_cfg.api_key or self.model_config.api_key,
            temperature=node_cfg.temperature,
            max_tokens=node_cfg.max_tokens,
            top_p=node_cfg.top_p,
            timeout=node_cfg.timeout,
            retry_count=node_cfg.retry_count,
            vision_enabled=node_cfg.vision_enabled,
            vision_detail=node_cfg.vision_detail
        )
        
        client = LLMClient(config)
        self._cache[cache_key] = client
        return client
    
    def _get_client_from_mapping(self, node_name: str) -> LLMClient:
        """从 NodeModelMapping 创建客户端"""
        model_name = self._node_model_mapping.get_model_for_node(node_name)
        is_vision = self._node_model_mapping.is_vision_node(node_name)
        
        cache_key = f"mapping:{model_name}:{is_vision}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        config = ModelConfig(
            name=model_name,
            api_base=self.model_config.api_base,
            api_key=self.model_config.api_key,
            temperature=self.model_config.temperature,
            max_tokens=self.model_config.max_tokens,
            timeout=self.model_config.timeout,
            retry_count=self.model_config.retry_count,
            vision_enabled=is_vision,
            vision_detail=self.model_config.vision_detail if is_vision else "auto"
        )
        
        client = LLMClient(config)
        self._cache[cache_key] = client
        return client
    
    async def close_all(self):
        """关闭所有客户端"""
        closed_ids = set()
        
        for client in self._cache.values():
            client_id = id(client)
            if client_id not in closed_ids:
                await client.close()
                closed_ids.add(client_id)
        
        self._cache.clear()
        self._default_text_client = None
        self._default_vision_client = None
    
    def get_summary(self) -> str:
        """获取配置摘要"""
        if self._models_config:
            return self._models_config.to_summary()
        
        lines = ["Client Manager Configuration", "=" * 40]
        lines.append(f"\nDefault text model: {self.model_config.name}")
        lines.append(f"Default vision model: {self.vision_model_config.name}")
        
        if self._node_model_mapping:
            lines.append("\nNode mappings:")
            for node, model in self._node_model_mapping.to_dict().items():
                lines.append(f"  {node}: {model}")
        
        lines.append(f"\nCached clients: {len(self._cache)}")
        
        return "\n".join(lines)