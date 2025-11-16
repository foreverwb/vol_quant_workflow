"""
文件处理工具
"""
import os
import base64
from pathlib import Path
from typing import List, Optional

def validate_image_file(file_path: str) -> bool:
    """验证图片文件"""
    
    # 支持的图片格式
    supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
    
    # 检查文件存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 检查文件格式
    file_ext = Path(file_path).suffix.lower()
    if file_ext not in supported_formats:
        raise ValueError(f"不支持的文件格式: {file_ext}")
    
    return True


def encode_image_to_base64(file_path: str) -> str:
    """将图片编码为base64"""
    
    validate_image_file(file_path)
    
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_file_list(folder_path: str, pattern: str = "*") -> List[str]:
    """
    获取文件列表
    
    Args:
        folder_path: 文件夹路径
        pattern: 文件名模式（如 "*.png"）
    """
    
    folder = Path(folder_path)
    
    if not folder.is_dir():
        raise ValueError(f"文件夹不存在: {folder_path}")
    
    files = list(folder.glob(pattern))
    return [str(f) for f in files if f.is_file()]


def create_output_directory(output_dir: str) -> str:
    """创建输出目录"""
    
    os.makedirs(output_dir, exist_ok=True)
    return output_dir
