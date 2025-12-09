"""
LLM 客户端管理器

负责:
- 根据配置创建 LLM 客户端
- 客户端缓存管理
- 支持多种配置方式 (YAML / NodeModelMapping / 默认)
"""
from typing import Dict, Optional, Set

try:
    from ..config import ModelConfig, NodeModelMapping
    from ..config.model_config_loader import ModelsConfig, NodeConfig
    from ..utils.llm_client import LLMClient
except ImportError:
    from config import ModelConfig, NodeModelMapping
    try:
        from config.model_config_loader import ModelsConfig, NodeConfig
    except ImportError:
        ModelsConfig = None
        NodeConfig = None
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
        model_config: ModelConfig,
        vision_model_config: Optional[ModelConfig] = None,
        models_config: Optional[ModelsConfig] = None,
        node_model_mapping: Optional[NodeModelMapping] = None
    ):
        """
        初始化客户端管理器
        
        Args:
            model_config: 默认模型配置
            vision_model_config: 视觉模型配置
            models_config: YAML 配置实例 (优先级最高)
            node_model_mapping: 节点模型映射
        """
        self.model_config = model_config
        self.vision_model_config = vision_model_config or model_config
        self._models_config = models_config
        self._node_model_mapping = node_model_mapping
        
        # 客户端缓存
        self._cache: Dict[str, LLMClient] = {}
        
        # 创建默认客户端
        self._default_text_client = LLMClient(model_config)
        self._default_vision_client = (
            LLMClient(vision_model_config) 
            if vision_model_config else self._default_text_client
        )
        
        # 缓存默认客户端
        self._cache[f"default:text:{model_config.name}"] = self._default_text_client
        if vision_model_config:
            self._cache[f"default:vision:{vision_model_config.name}"] = self._default_vision_client
    
    @property
    def text_client(self) -> LLMClient:
        """获取默认文本客户端"""
        return self._default_text_client
    
    @property
    def vision_client(self) -> LLMClient:
        """获取默认视觉客户端"""
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
            return self._default_vision_client
        return self._default_text_client
    
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