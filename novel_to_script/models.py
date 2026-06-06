"""
剧本 YAML Schema 数据模型

使用 Pydantic 定义强类型数据模型，确保数据完整性和可验证性。
这些模型直接映射到 YAML 结构，形成剧本的标准 Schema。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ElementType(str, Enum):
    """场景元素类型"""

    ACTION = "action"           # 动作/场景描述
    DIALOGUE = "dialogue"       # 角色对白
    PARENTHETICAL = "parenthetical"  # 表演指示（括号内）
    TRANSITION = "transition"   # 转场提示
    SOUND = "sound"             # 音效/音乐提示
    NOTE = "note"               # 备注/批注


class CharacterImportance(str, Enum):
    """角色重要性级别"""

    MAIN = "main"           # 主角
    SUPPORTING = "supporting"  # 配角
    MINOR = "minor"         # 龙套/客串


class IntExt(str, Enum):
    """内外景标识"""

    INT = "内景"    # Interior
    EXT = "外景"    # Exterior
    INT_EXT = "内外景"  # 两者皆有


class TimeOfDay(str, Enum):
    """时间段"""

    DAWN = "黎明"
    MORNING = "晨"
    DAY = "日"
    NOON = "正午"
    AFTERNOON = "下午"
    DUSK = "黄昏"
    EVENING = "晚"
    NIGHT = "夜"
    LATE_NIGHT = "深夜"
    CONTINUOUS = "连续"  # 紧接上一场
    SAME_TIME = "同时"   # 与另一场景同时发生
    LATER = "稍后"
    MOMENTS_LATER = "片刻后"


class Metadata(BaseModel):
    """
    剧本元数据

    记录剧本的基本信息和来源信息，便于追溯和管理。
    """

    title: str = Field(description="剧本标题", default="")
    source_title: str = Field(description="原小说标题", default="")
    author: str = Field(description="作者", default="")
    genre: str = Field(description="类型/题材", default="")
    total_scenes: int = Field(description="总场次数", default=0, ge=0)
    total_acts: int = Field(description="总幕数", default=0, ge=0)
    total_characters: int = Field(description="角色总数", default=0, ge=0)
    generated_at: str = Field(
        description="生成时间（ISO 8601 格式）",
        default_factory=lambda: datetime.now().isoformat(),
    )
    version: str = Field(description="Schema 版本", default="1.0.0")


class Character(BaseModel):
    """
    角色定义

    剧本中所有出场角色的集中定义，便于统一管理和一致性检查。
    """

    id: str = Field(description="角色唯一标识符", pattern=r"^char_\d{3}$")
    name: str = Field(description="角色名称", min_length=1)
    aliases: list[str] = Field(description="角色别名/绰号", default_factory=list)
    description: str = Field(description="角色简要描述", default="")
    traits: list[str] = Field(description="性格特征列表", default_factory=list)
    age: str = Field(description="年龄", default="")
    gender: str = Field(description="性别", default="")
    importance: CharacterImportance = Field(
        description="角色重要性级别", default=CharacterImportance.SUPPORTING
    )
    notes: str = Field(description="备注", default="")


class SceneElement(BaseModel):
    """
    场景元素

    构成单场戏的最小单元。每个元素有明确的类型和内容，
    对应剧本中的不同视觉/听觉元素。
    """

    type: ElementType = Field(description="元素类型")
    content: str = Field(description="内容文本", min_length=1)
    character: str | None = Field(description="角色名称（对白类型必填）", default=None)
    parenthetical: str | None = Field(
        description="表演指示（如：低声、愤怒地）", default=None
    )
    notes: str | None = Field(description="内部备注", default=None)

    def model_post_init(self, __context: Any) -> None:
        """验证对白类型必须有角色名"""
        if self.type == ElementType.DIALOGUE and not self.character:
            raise ValueError("对白类型 (dialogue) 必须指定角色名称")


class SceneHeading(BaseModel):
    """
    场景标题

    标准剧本格式中的场景标题行，包含内景/外景、地点和时间。
    """

    int_ext: IntExt = Field(description="内景/外景标识")
    location: str = Field(description="地点", min_length=1)
    time: TimeOfDay | str = Field(description="时间段")

    def to_string(self) -> str:
        """转换为标准场景标题字符串"""
        time_str = self.time.value if isinstance(self.time, TimeOfDay) else self.time
        return f"{self.int_ext.value}. {self.location} - {time_str}"


class Scene(BaseModel):
    """
    单场戏

    剧本的基本单位。一场戏在一个连续的时间和空间内发生，
    由一系列场景元素组成。
    """

    scene_number: int = Field(description="全局场次数", ge=1)
    act_scene_number: int = Field(description="幕内场次数", ge=1)
    heading: str = Field(description="完整场景标题字符串", min_length=1)
    location: str = Field(description="地点", default="")
    time: str = Field(description="时间", default="")
    int_ext: str = Field(description="内景/外景", default="")
    description: str = Field(description="场景简介", default="")
    mood: str = Field(description="场景氛围/基调", default="")
    elements: list[SceneElement] = Field(description="场景元素列表", default_factory=list)
    characters_present: list[str] = Field(description="本场出场角色", default_factory=list)
    estimated_duration: int | None = Field(
        description="预估时长（秒）", default=None, ge=0
    )


class Act(BaseModel):
    """
    一幕

    由多场戏组成的戏剧段落。幕是剧本的结构单位，
    通常对应故事的一个阶段（铺垫、发展、高潮、结局）。
    """

    act_number: int = Field(description="幕号", ge=1)
    title: str = Field(description="幕标题", default="")
    description: str = Field(description="幕内容简述", default="")
    scenes: list[Scene] = Field(description="场景列表", default_factory=list)
    scene_count: int = Field(description="场次数", default=0, ge=0)

    def model_post_init(self, __context: Any) -> None:
        """自动计算场次数"""
        self.scene_count = len(self.scenes)


class Screenplay(BaseModel):
    """
    剧本根对象

    完整的结构化剧本，包含元数据、角色表、幕结构。
    这是 YAML 文件的顶层对象。
    """

    screenplay: dict[str, Any] = Field(description="剧本根节点")

    @classmethod
    def create(
        cls,
        metadata: Metadata,
        characters: list[Character],
        acts: list[Act],
    ) -> "Screenplay":
        """
        创建完整的剧本对象

        Args:
            metadata: 剧本元数据
            characters: 角色列表
            acts: 幕列表

        Returns:
            Screenplay 实例
        """
        metadata.total_acts = len(acts)
        metadata.total_scenes = sum(len(act.scenes) for act in acts)
        metadata.total_characters = len(characters)

        return cls(
            screenplay={
                "version": metadata.version,
                "metadata": metadata.model_dump(mode="json"),
                "characters": [c.model_dump(mode="json") for c in characters],
                "acts": [a.model_dump(mode="json") for a in acts],
            }
        )

    def to_yaml_dict(self) -> dict[str, Any]:
        """转换为纯字典，用于 YAML 序列化"""
        return self.screenplay


class Chapter(BaseModel):
    """
    小说章节（中间处理结构）

    解析阶段使用的章节模型，不输出到最终 YAML。
    """

    number: int = Field(description="章节序号", ge=1)
    title: str = Field(description="章节标题", default="")
    content: str = Field(description="章节正文", min_length=1)
    word_count: int = Field(description="字数", default=0, ge=0)

    def model_post_init(self, __context: Any) -> None:
        """自动计算字数"""
        self.word_count = len(self.content)


class Novel(BaseModel):
    """
    小说对象（中间处理结构）

    解析阶段使用的小说模型，不输出到最终 YAML。
    """

    title: str = Field(description="小说标题", default="")
    author: str = Field(description="作者", default="")
    chapters: list[Chapter] = Field(description="章节列表", default_factory=list)
    total_word_count: int = Field(description="总字数", default=0, ge=0)

    def model_post_init(self, __context: Any) -> None:
        """自动计算总字数"""
        self.total_word_count = sum(c.word_count for c in self.chapters)
