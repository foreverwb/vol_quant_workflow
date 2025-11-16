"""
通用LLM客户端 - 支持多模型厂商
"""
import json
import base64
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
import httpx
from config.model_config import ModelConfig

class LLMProvider(ABC):
    """LLM提供商基类"""
    
    @abstractmethod
    async def call(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        structured_output: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """调用LLM API"""
        pass

class OpenAICompatibleProvider(LLMProvider):
    """OpenAI兼容API提供商（包含Qwen、Claude等）"""
    
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def call(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        structured_output: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """调用OpenAI兼容API"""
        payload = {
            "model": model_config.model_name,
            "messages": messages,
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_tokens,
            "top_p": model_config.top_p
        }
        
        # 添加结构化输出支持
        if structured_output and model_config.structured_output:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "output",
                    "schema": structured_output,
                    "strict": True
                }
            }
        
        try:
            response = await self.client.post(
                f"{self.api_base}/v1/chat/completions",
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            
            content = result['choices'][0]['message']['content']
            
            # 尝试解析JSON
            if structured_output:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"raw_content": content}
            
            return {"content": content}
        
        except httpx.HTTPError as e:
            return {
                "error": True,
                "message": f"API调用失败: {str(e)}"
            }

class LLMClient:
    """统一LLM客户端"""
    
    def __init__(
        self,
        api_base: str,
        api_key: str,
        provider_type: str = "openai_compatible"
    ):
        self.api_base = api_base
        self.api_key = api_key
        
        if provider_type == "openai_compatible":
            self.provider = OpenAICompatibleProvider(api_base, api_key)
        else:
            raise ValueError(f"不支持的提供商类型: {provider_type}")
    
    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        model_config: ModelConfig,
        structured_output: Optional[Dict] = None,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        调用LLM进行对话
        
        Args:
            system_prompt: 系统提示
            user_message: 用户消息
            model_config: 模型配置
            structured_output: JSON schema
            images: 图片URL列表
        """
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 构建用户消息（支持多模态）
        user_content = []
        
        if model_config.vision_enabled and images:
            for img_url in images:
                if img_url.startswith("http"):
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": img_url}
                    })
                else:
                    # 本地图片转base64
                    with open(img_url, 'rb') as f:
                        b64_img = base64.b64encode(f.read()).decode()
                        user_content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                        })
            
            user_content.append({
                "type": "text",
                "text": user_message
            })
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": user_message})
        
        # 调用提供商
        return await self.provider.call(
            messages,
            model_config,
            structured_output
        )

# 全局LLM客户端实例
_llm_client: Optional[LLMClient] = None

def init_llm_client(api_base: str, api_key: str):
    """初始化全局LLM客户端"""
    global _llm_client
    _llm_client = LLMClient(api_base, api_key)

def get_llm_client() -> LLMClient:
    """获取全局LLM客户端"""
    if _llm_client is None:
        raise RuntimeError("LLM客户端未初始化，请先调用 init_llm_client()")
    return _llm_client
