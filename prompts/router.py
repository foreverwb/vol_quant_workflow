"""
Router 节点 Prompt
判断用户输入类型：变量信息 / 图表数据 / 无效输入
"""
from .base import PromptTemplate, register_prompt


ROUTER_PROMPT = register_prompt(PromptTemplate(
    name="router",
    description="判断用户输入类型：变量信息/图表数据/无效输入",
    
    system="""你是路由助手，判断用户输入属于以下哪一类，仅输出一个关键词：

1. "VARIABLES" - 用户提供标的代码、事件类型等变量信息
2. "DATA" - 用户回传gexbot图表数据（包含图片或数据截图）
3. "INVALID" - 其他无效输入

判断规则：
- 若消息包含标的代码（1-5个大写字母）且提到事件类型、DTE等信息 → VARIABLES
- 若上传了图片文件 → DATA
- 其他 → INVALID""",

    user="${user_input}",
    
    variables={
        "user_input": "用户的原始输入文本"
    }
))
