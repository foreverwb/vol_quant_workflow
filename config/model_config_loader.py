"""
模型配置加载器

从 YAML 文件加载节点模型配置，支持：
- 全局默认配置
- 节点特定配置
- 预设引用
- 环境覆盖
- 环境变量覆盖
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

# 配置文件默认路径
DEFAULT_CONFIG_PATH = Path(__file__).parent / "models.yaml"


@dataclass
class NodeConfig:
    """单个节点的模型配置"""
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    timeout: int = 120
    retry_count: int = 3
    vision_enabled: bool = False
    vision_detail: str = "auto"
    
    # API 配置
    api_base: str = ""
    api_key: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "vision_enabled": self.vision_enabled,
            "vision_detail": self.vision_detail,
            "api_base": self.api_base,
            "api_key": self.api_key,
        }


@dataclass
class ModelsConfig:
    """
    完整的模型配置管理器
    
    使用方式:
        # 从默认配置文件加载
        config = ModelsConfig.load()
        
        # 获取节点配置
        router_config = config.get_node_config("router")
        print(router_config.model)  # gpt-4o-mini
        
        # 指定环境
        config = ModelsConfig.load(env="production")
    """
    defaults: Dict[str, Any] = field(default_factory=dict)
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    presets: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 已解析的节点配置缓存
    _resolved_cache: Dict[str, NodeConfig] = field(default_factory=dict, repr=False)
    
    @classmethod
    def load(
        cls, 
        config_path: Optional[str] = None,
        env: Optional[str] = None
    ) -> 'ModelsConfig':
        """
        从 YAML 文件加载配置
        
        Args:
            config_path: 配置文件路径，默认为 config/models.yaml
            env: 环境名称 (development/production)，
                 默认从 ENV 或 ENVIRONMENT 环境变量读取
        
        Returns:
            ModelsConfig 实例
        """
        # 确定配置文件路径
        if config_path:
            path = Path(config_path)
        else:
            path = DEFAULT_CONFIG_PATH
        
        # 加载 YAML
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f) or {}
        else:
            raw_config = {}
        
        # 确定环境
        if env is None:
            env = os.getenv('ENV') or os.getenv('ENVIRONMENT')
        
        # 提取基础配置
        defaults = raw_config.get('defaults', {})
        nodes = raw_config.get('nodes', {})
        presets = raw_config.get('presets', {})
        
        # 应用环境覆盖
        if env and 'environments' in raw_config:
            env_config = raw_config['environments'].get(env, {})
            
            # 合并环境默认配置
            if 'defaults' in env_config:
                defaults = {**defaults, **env_config['defaults']}
            
            # 合并环境节点配置
            if 'nodes' in env_config:
                for node_name, node_config in env_config['nodes'].items():
                    if node_name in nodes:
                        nodes[node_name] = {**nodes[node_name], **node_config}
                    else:
                        nodes[node_name] = node_config
        
        # 环境变量覆盖 API 配置
        if os.getenv('LLM_API_BASE'):
            defaults['api_base'] = os.getenv('LLM_API_BASE')
        if os.getenv('LLM_API_KEY'):
            defaults['api_key'] = os.getenv('LLM_API_KEY')
        
        return cls(defaults=defaults, nodes=nodes, presets=presets)
    
    def get_node_config(self, node_name: str) -> NodeConfig:
        """
        获取指定节点的完整配置
        
        配置优先级 (从高到低):
        1. 节点特定配置
        2. 预设配置 (如果节点指定了 preset)
        3. 全局默认配置
        
        Args:
            node_name: 节点名称
            
        Returns:
            NodeConfig 实例
        """
        # 检查缓存
        if node_name in self._resolved_cache:
            return self._resolved_cache[node_name]
        
        # 从默认配置开始
        merged = dict(self.defaults)
        
        # 获取节点配置
        node_cfg = self.nodes.get(node_name, {})
        
        # 如果指定了预设，先应用预设
        if 'preset' in node_cfg:
            preset_name = node_cfg['preset']
            if preset_name in self.presets:
                merged.update(self.presets[preset_name])
        
        # 应用节点特定配置
        merged.update(node_cfg)
        
        # 移除非 NodeConfig 字段
        merged.pop('preset', None)
        
        # 创建 NodeConfig
        config = NodeConfig(
            model=merged.get('model', 'gpt-4o'),
            temperature=merged.get('temperature', 0.7),
            max_tokens=merged.get('max_tokens', 4096),
            top_p=merged.get('top_p', 1.0),
            timeout=merged.get('timeout', 120),
            retry_count=merged.get('retry_count', 3),
            vision_enabled=merged.get('vision_enabled', False),
            vision_detail=merged.get('vision_detail', 'auto'),
            api_base=merged.get('api_base', ''),
            api_key=merged.get('api_key', ''),
        )
        
        # 缓存结果
        self._resolved_cache[node_name] = config
        
        return config
    
    def get_all_node_configs(self) -> Dict[str, NodeConfig]:
        """获取所有已定义节点的配置"""
        result = {}
        for node_name in self.nodes.keys():
            result[node_name] = self.get_node_config(node_name)
        return result
    
    def list_nodes(self) -> list:
        """列出所有已配置的节点"""
        return list(self.nodes.keys())
    
    def list_presets(self) -> list:
        """列出所有可用的预设"""
        return list(self.presets.keys())
    
    def to_summary(self) -> str:
        """生成配置摘要"""
        lines = ["Models Configuration Summary", "=" * 40]
        
        lines.append(f"\nDefaults:")
        lines.append(f"  model: {self.defaults.get('model', 'N/A')}")
        lines.append(f"  temperature: {self.defaults.get('temperature', 'N/A')}")
        lines.append(f"  max_tokens: {self.defaults.get('max_tokens', 'N/A')}")
        
        lines.append(f"\nNodes ({len(self.nodes)}):")
        for name in self.nodes:
            cfg = self.get_node_config(name)
            vision_tag = " [vision]" if cfg.vision_enabled else ""
            lines.append(f"  {name}: {cfg.model} (T={cfg.temperature}){vision_tag}")
        
        if self.presets:
            lines.append(f"\nPresets ({len(self.presets)}):")
            for name in self.presets:
                lines.append(f"  {name}")
        
        return "\n".join(lines)


# 便捷函数
def load_models_config(
    config_path: Optional[str] = None,
    env: Optional[str] = None
) -> ModelsConfig:
    """加载模型配置的便捷函数"""
    return ModelsConfig.load(config_path, env)


def get_node_config(
    node_name: str,
    config_path: Optional[str] = None,
    env: Optional[str] = None
) -> NodeConfig:
    """获取单个节点配置的便捷函数"""
    config = ModelsConfig.load(config_path, env)
    return config.get_node_config(node_name)