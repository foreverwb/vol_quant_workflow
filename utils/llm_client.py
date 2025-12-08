"""
通用LLM客户端
支持任意模型厂商，通过OpenAI兼容API进行调用
"""
import json
import base64
import asyncio
import httpx
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from pathlib import Path
import mimetypes

# 支持两种运行方式
try:
    from ..config import ModelConfig
except ImportError:
    from config import ModelConfig


@dataclass
class Message:
    """消息结构"""
    role: str  # system, user, assistant
    content: Union[str, List[Dict[str, Any]]]


@dataclass
class LLMResponse:
    """LLM响应结构"""
    content: str
    raw_response: Dict[str, Any]
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    structured_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return bool(self.content) and not self.error


class LLMClient:
    """
    通用LLM客户端
    支持:
    - OpenAI API
    - OpenAI兼容API (如Qwen、Claude、DeepSeek等)
    - 视觉能力 (图片输入)
    - 结构化输出 (JSON Schema)
    """
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers=self._get_headers()
            )
        return self._client
    
    def _get_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json"
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers
    
    def _get_api_url(self) -> str:
        """获取API URL"""
        base = self.config.api_base.rstrip('/')
        if not base.endswith('/chat/completions'):
            if base.endswith('/v1'):
                return f"{base}/chat/completions"
            else:
                return f"{base}/v1/chat/completions"
        return base
    
    @staticmethod
    def encode_image(image_path: str) -> tuple:
        """
        将图片编码为base64
        返回 (base64_string, mime_type)
        """
        path = Path(image_path)
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type is None:
            mime_type = "image/png"
        
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8"), mime_type
    
    def _build_messages(
        self,
        messages: List[Message],
        images: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        构建API消息格式
        支持文本和图片混合输入
        """
        result = []
        
        for msg in messages:
            if isinstance(msg.content, str):
                # 纯文本消息
                if msg.role == "user" and images and self.config.vision_enabled:
                    # 用户消息带图片
                    content = [{"type": "text", "text": msg.content}]
                    for img_path in images:
                        b64_data, mime_type = self.encode_image(img_path)
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_data}",
                                "detail": self.config.vision_detail
                            }
                        })
                    result.append({"role": msg.role, "content": content})
                else:
                    result.append({"role": msg.role, "content": msg.content})
            else:
                # 已经是复杂格式
                result.append({"role": msg.role, "content": msg.content})
        
        return result
    
    def _build_request_body(
        self,
        messages: List[Dict[str, Any]],
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """构建请求体"""
        body = {
            "model": self.config.name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            "stream": self.config.stream
        }
        
        if response_format:
            body["response_format"] = response_format
        
        return body
    
    async def chat(
        self,
        messages: Optional[List[Message]] = None,
        images: Optional[List[str]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        发送聊天请求
        
        支持两种调用方式:
        1. 使用 messages 参数: client.chat(messages=[Message(...), ...])
        2. 使用 system_prompt/user_prompt: client.chat(system_prompt="...", user_prompt="...")
        
        Args:
            messages: 消息列表 (与 system_prompt/user_prompt 二选一)
            images: 图片路径列表 (需要vision_enabled=True)
            json_schema: JSON Schema (用于结构化输出)
            system_prompt: 系统提示词 (便捷方式)
            user_prompt: 用户提示词 (便捷方式)
            
        Returns:
            LLMResponse
        """
        # 支持便捷调用方式
        if messages is None and (system_prompt or user_prompt):
            messages = []
            if system_prompt:
                messages.append(Message(role="system", content=system_prompt))
            if user_prompt:
                messages.append(Message(role="user", content=user_prompt))
        
        if not messages:
            return LLMResponse(
                content="",
                raw_response={"error": "No messages provided"},
                error="No messages provided"
            )
        
        api_messages = self._build_messages(messages, images)
        
        # 构建response_format
        response_format = None
        if json_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "strict": True,
                    "schema": json_schema
                }
            }
        
        body = self._build_request_body(api_messages, response_format)
        
        # 重试逻辑
        last_error = None
        for attempt in range(self.config.retry_count):
            try:
                response = await self.client.post(
                    self._get_api_url(),
                    json=body
                )
                response.raise_for_status()
                
                data = response.json()
                
                content = ""
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    content = choice.get("message", {}).get("content", "")
                    finish_reason = choice.get("finish_reason")
                else:
                    finish_reason = None
                
                usage = data.get("usage")
                
                # 解析结构化输出
                structured_output = None
                if json_schema and content:
                    try:
                        structured_output = json.loads(content)
                    except json.JSONDecodeError:
                        pass
                
                return LLMResponse(
                    content=content,
                    raw_response=data,
                    usage=usage,
                    finish_reason=finish_reason,
                    structured_output=structured_output
                )
                
            except Exception as e:
                last_error = e
                if attempt < self.config.retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
        
        # 所有重试都失败
        return LLMResponse(
            content="",
            raw_response={"error": str(last_error)},
            finish_reason="error",
            error=str(last_error)
        )
    
    def chat_sync(
        self,
        messages: List[Message],
        images: Optional[List[str]] = None,
        json_schema: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """同步版本的chat"""
        return asyncio.run(self.chat(messages, images, json_schema))
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None


class LLMClientFactory:
    """LLM客户端工厂"""
    
    _instances: Dict[str, LLMClient] = {}
    
    @classmethod
    def create(cls, config: ModelConfig) -> LLMClient:
        """创建或获取LLM客户端实例"""
        key = f"{config.api_base}:{config.name}"
        if key not in cls._instances:
            cls._instances[key] = LLMClient(config)
        return cls._instances[key]
    
    @classmethod
    def get_default(cls) -> LLMClient:
        """获取默认客户端"""
        try:
            from ..config import DEFAULT_MODEL_CONFIG
        except ImportError:
            from config import DEFAULT_MODEL_CONFIG
        return cls.create(DEFAULT_MODEL_CONFIG)
    
    @classmethod
    async def close_all(cls):
        """关闭所有客户端"""
        for client in cls._instances.values():
            await client.close()
        cls._instances.clear()


# 便捷函数
def create_llm_client(
    api_base: str,
    api_key: str = "",
    model_name: str = "default-model",
    temperature: float = 0.7,
    vision_enabled: bool = False,
    **kwargs
) -> LLMClient:
    """
    快速创建LLM客户端
    
    示例:
        # OpenAI
        client = create_llm_client(
            api_base="https://api.openai.com/v1",
            api_key="sk-xxx",
            model_name="gpt-4o"
        )
        
        # Qwen (兼容API)
        client = create_llm_client(
            api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="sk-xxx",
            model_name="qwen-max"
        )
        
        # 本地Ollama
        client = create_llm_client(
            api_base="http://localhost:11434/v1",
            model_name="llama3"
        )
    """
    config = ModelConfig(
        api_base=api_base,
        api_key=api_key,
        name=model_name,
        temperature=temperature,
        vision_enabled=vision_enabled,
        **kwargs
    )
    return LLMClient(config)
