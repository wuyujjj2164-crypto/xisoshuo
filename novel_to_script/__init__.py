"""
AI 小说转剧本工具

将小说文本自动转换为结构化剧本（YAML 格式）。
"""

__version__ = "1.0.0"
__author__ = "Novel-to-Script Team"

from .models import Screenplay, Act, Scene, Character, SceneElement
from .parser import NovelParser
from .analyzer import NovelAnalyzer
from .converter import ScriptConverter
from .formatter import YAMLFormatter

__all__ = [
    "Screenplay",
    "Act",
    "Scene",
    "Character",
    "SceneElement",
    "NovelParser",
    "NovelAnalyzer",
    "ScriptConverter",
    "YAMLFormatter",
]
