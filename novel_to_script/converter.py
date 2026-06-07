"""
AI 剧本转换引擎

调用 LLM API（Claude / DeepSeek / 通义千问等），将小说文本转换为结构化剧本。
核心功能：场景分割、叙述转对白、动作提取、格式化输出。
"""

import json
import os
from typing import Any

import yaml

from .models import Act, Character, Metadata, Scene, SceneElement, Screenplay


BATCH_PROMPT = """你是一位资深影视编剧，精通将小说改编为可直接拍摄的专业剧本。
请将以下小说章节改编为剧本场景。这是第 {batch_num}/{total_batches} 批章节。

## 改编原则（这是改编，不是简单分块）

### 1. 场景分割
- 地点变化 = 新场景
- 时间变化 = 新场景
- 同一地点内，如果事件/话题发生明显转折，也考虑新场景
- 每个场景要有明确的戏剧目标（人物想做什么）

### 2. 角色识别与对白处理
- **识别说话人**：小说中的直接引语（带引号的内容）→ 转为 dialogue
- 在引语附近找"XX说道/说/问/喊道"等提示，确定说话人姓名
- 如果提示不明确，根据上下文逻辑推断谁在说话
- **多人对话**：依次列出每个人的对白，不要混在一起

### 3. 叙述转动作（核心改编能力）
- 小说的叙述性文字要改编成**可拍摄的动作描述**，不是直接复制
- 心理描写 → 用表情、动作、镜头语言来表现
  - 错误："他很紧张"（不可拍摄）
  - 正确："他攥紧了拳头，指节发白"（可拍摄）
- 环境描写 → 精简为场景氛围，交代时间地点
- 不要大段复制原文叙述，要提炼为视觉化的动作

### 4. 场景元素类型
- **action**: 动作/场景描写（第三人称，现在时，可拍摄的画面）
- **dialogue**: 角色对白（必须有 character 字段）
- **parenthetical**: 表演指示（语气、动作、情绪，附在对白下方括号中）
- **transition**: 转场提示（如"切至"、"淡入"、"叠化"）

### 5. 场景标题格式
内景/外景. 地点 - 时间
时间选项：黎明、晨、日、正午、下午、黄昏、晚、夜、深夜、连续

## 角色参考（供识别说话人使用）

{characters}

## 章节内容

{chapters_content}

## 输出格式

请输出 YAML 格式的场景列表（只输出 acts 下的内容）：

```yaml
acts:
  - act_number: {act_number}
    title: "幕标题（概括本幕核心冲突）"
    description: "幕内容简述"
    scenes:
      - scene_number: 1
        heading: "内景. 客厅 - 日"
        location: "客厅"
        time: "日"
        int_ext: "内景"
        description: "场景一句话概括"
        mood: "氛围（如：紧张、温馨、压抑）"
        characters_present: ["角色A", "角色B"]
        elements:
          - type: action
            content: "可拍摄的动作描述，不要直接复制小说叙述"
          - type: dialogue
            character: "角色A"
            content: "对白内容"
            parenthetical: "低声/愤怒地/犹豫地"
          - type: action
            content: "角色A说完后的动作或反应"
          - type: transition
            content: "切至："
```

## 关键提醒
- 这是**改编**，不是简单分段。要理解故事后重新组织为剧本格式
- 所有 content 必须是**现在时**（剧本用现在时书写）
- 对白要保留角色语言风格，不要擅自改写原意
- 每个场景必须有 heading，每个 dialogue 必须有 character
"""


class ScriptConverter:
    """
    剧本转换引擎

    使用 LLM API 将小说分析结果转换为结构化剧本。
    支持 Anthropic Claude 和 OpenAI 兼容格式的 API（DeepSeek、通义千问等）。
    支持分批处理长文本，避免超出 token 限制。
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        chapters_per_batch: int = 3,
        provider: str = "anthropic",
        base_url: str | None = None,
    ):
        """
        初始化转换器

        Args:
            api_key: API 密钥（默认从环境变量读取）
            model: 使用的模型名称
            max_tokens: 单次请求最大输出 token 数
            temperature: 创造性程度 (0.0-1.0)
            chapters_per_batch: 每批处理的章节数
            provider: API 提供商，可选 "anthropic" / "openai"
            base_url: OpenAI 兼容 API 的基础 URL（如 DeepSeek、通义千问）
        """
        self.provider = provider.lower()
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.chapters_per_batch = chapters_per_batch
        self.base_url = base_url

        # 初始化 API 客户端
        if self.provider == "anthropic":
            self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "必须提供 API 密钥或通过 ANTHROPIC_API_KEY 环境变量设置"
                )
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "使用 Anthropic 需要先安装: pip install anthropic"
                )

        elif self.provider in ("openai", "kimi"):
            # Kimi 使用 OpenAI 兼容格式
            env_var = "MOONSHOT_API_KEY" if self.provider == "kimi" else "OPENAI_API_KEY"
            self.api_key = api_key or os.environ.get(env_var)
            if not self.api_key:
                raise ValueError(
                    f"必须提供 API 密钥或通过 {env_var} 环境变量设置"
                )
            try:
                import openai
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=base_url,
                )
            except ImportError:
                raise ImportError(
                    "使用 OpenAI 兼容 API 需要先安装: pip install openai"
                )
        else:
            raise ValueError(f"不支持的 provider: {provider}，可选: anthropic, openai, kimi")

    def convert(
        self,
        chapters: list,
        characters: list[Character],
        title: str = "",
        author: str = "",
    ) -> Screenplay:
        """
        转换小说为剧本

        Args:
            chapters: 章节列表（来自 NovelParser 的 Chapter 对象）
            characters: 角色列表
            title: 小说标题
            author: 作者

        Returns:
            Screenplay 对象
        """
        character_info = self._format_characters(characters)

        # 分批处理
        batches = self._create_batches(chapters)

        all_acts: list[Act] = []
        scene_counter = 1

        for i, batch in enumerate(batches, 1):
            batch_content = self._format_batch(batch)
            act_number = i

            prompt = BATCH_PROMPT.format(
                batch_num=i,
                total_batches=len(batches),
                chapters_content=batch_content,
                characters=character_info,
                act_number=act_number,
            )

            response = self._call_api(prompt)
            parsed = self._parse_response(response)

            if parsed and "acts" in parsed:
                for act_data in parsed["acts"]:
                    # 更新场景编号为全局编号
                    for scene_data in act_data.get("scenes", []):
                        scene_data["scene_number"] = scene_counter
                        scene_counter += 1

                    act = self._dict_to_act(act_data)
                    all_acts.append(act)

        metadata = Metadata(
            title=title or "未命名剧本",
            source_title=title or "",
            author=author or "",
        )

        return Screenplay.create(
            metadata=metadata,
            characters=characters,
            acts=all_acts,
        )

    def _call_api(self, prompt: str) -> str:
        """调用 LLM API"""
        if self.provider == "anthropic":
            return self._call_anthropic(prompt)
        else:
            return self._call_openai(prompt)

    def _call_anthropic(self, prompt: str) -> str:
        """调用 Anthropic Claude API"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _call_openai(self, prompt: str) -> str:
        """调用 OpenAI 兼容 API（DeepSeek、通义千问等）"""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    def _parse_response(self, response: str) -> dict[str, Any] | None:
        """
        解析 API 响应

        从响应文本中提取 YAML 内容并解析为字典。

        Args:
            response: API 响应文本

        Returns:
            解析后的字典，或 None 如果解析失败
        """
        # 提取 YAML 代码块
        yaml_text = response

        # 去除 markdown 代码块标记
        if "```yaml" in yaml_text:
            yaml_text = yaml_text.split("```yaml")[1]
        elif "```" in yaml_text:
            yaml_text = yaml_text.split("```")[1]

        yaml_text = yaml_text.replace("```", "").strip()

        try:
            return yaml.safe_load(yaml_text)
        except yaml.YAMLError as e:
            # 尝试修复常见 YAML 问题
            fixed = self._fix_yaml(yaml_text)
            try:
                return yaml.safe_load(fixed)
            except yaml.YAMLError:
                raise ValueError(f"无法解析 API 响应为 YAML: {e}") from e

    def _fix_yaml(self, text: str) -> str:
        """
        修复常见的 YAML 格式问题

        Args:
            text: 原始 YAML 文本

        Returns:
            修复后的文本
        """
        lines = text.split("\n")
        fixed = []

        for line in lines:
            # 修复缩进问题
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            # 确保列表项正确缩进
            if stripped.startswith("- ") and indent % 2 != 0:
                indent = (indent // 2) * 2

            fixed.append(" " * indent + stripped)

        return "\n".join(fixed)

    def _dict_to_act(self, data: dict[str, Any]) -> Act:
        """
        将字典转换为 Act 对象

        Args:
            data: 包含 act 数据的字典

        Returns:
            Act 对象
        """
        scenes = []
        for scene_data in data.get("scenes", []):
            elements = []
            for elem_data in scene_data.get("elements", []):
                elements.append(SceneElement(**elem_data))

            scene = Scene(
                scene_number=scene_data.get("scene_number", 0),
                act_scene_number=scene_data.get("act_scene_number", 0),
                heading=scene_data.get("heading", ""),
                location=scene_data.get("location", ""),
                time=scene_data.get("time", ""),
                int_ext=scene_data.get("int_ext", ""),
                description=scene_data.get("description", ""),
                mood=scene_data.get("mood", ""),
                elements=elements,
                characters_present=scene_data.get("characters_present", []),
            )
            scenes.append(scene)

        return Act(
            act_number=data.get("act_number", 0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            scenes=scenes,
        )

    def _format_characters(self, characters: list[Character]) -> str:
        """格式化角色信息为字符串"""
        lines = []
        for char in characters[:10]:  # 最多 10 个主要角色
            lines.append(
                f"- {char.name} ({char.importance.value}): {char.description[:60]}"
            )
        return "\n".join(lines)

    def _create_batches(self, chapters: list) -> list[list]:
        """将章节分批"""
        batches = []
        for i in range(0, len(chapters), self.chapters_per_batch):
            batch = chapters[i : i + self.chapters_per_batch]
            batches.append(batch)
        return batches

    def _format_batch(self, batch: list) -> str:
        """格式化批次内容"""
        lines = []
        for ch in batch:
            lines.append(f"## {ch.title}")
            # 每章限制 5000 字，给 LLM 更多上下文理解故事
            content = ch.content[:5000]
            lines.append(content)
            if len(ch.content) > 5000:
                lines.append("...（章节较长，以上为前 5000 字）")
            lines.append("")
        return "\n\n".join(lines)
