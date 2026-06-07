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

## 核心原则：改写，不是复制

你的唯一任务是**把小说叙述翻译成镜头语言**。

**绝对禁止直接复制原文。** 小说原文在 prompt 里只是供你理解的素材，不是让你粘贴到 action 里的。如果你把原文段落原封不动放进 content，这次改编就是零分。

**改写工作流（必须执行）：**
1. 读一段原文 → 2. 判断它是什么类型（心理/环境/动作/对话） → 3. 按对应规则翻译成现在时的动作 → 4. 输出

## 1. 叙述转动作（最关键）

**A. 心理描写 → 镜头化动作**
不要写"他觉得""她心里""他想"——这些观众看不见。只写能拍出来的。

原文（心理）：
> 于国祥心里很不是滋味，自从兄弟国瑞死后他的心就一直紧揪着，就像被一根细麻绳捆绑着，勒得很疼，透不过气来。

❌ 错误（复制）：
content: "于国祥心里很不是滋味，自从兄弟国瑞死后他的心就一直紧揪着，就像被一根细麻绳捆绑着，勒得很疼，透不过气来。"

✅ 正确（镜头化）：
content: "他深吸一口气，手不自觉地按住胸口。"

原文（心理）：
> 他感到一阵恐惧，浑身发冷，双腿像灌了铅一样沉重。

❌ 错误：
content: "他感到一阵恐惧，浑身发冷，双腿像灌了铅一样沉重。"

✅ 正确：
content: "他后退半步，脊背抵住墙壁。双手攥紧，指节发白。"

**B. 环境/氛围描写 → 精简画面**
不要大段风景描写，只保留能烘托情绪的画面。

原文：
> 出了村头，满眼映进碧绿田野和青色山脉，春天的暖意阵阵扑面。

❌ 错误：
content: "出了村头，满眼映进碧绿田野和青色山脉，春天的暖意阵阵扑面。"

✅ 正确：
content: "村外。麦浪起伏，远山青黛。"

**C. 动作叙述 → 去冗余、现在时**
删除"了""着""于是""然后"，删除说话引导词。

原文：
> 李明放下了手中的杯子，然后站起身来，走到了窗前。

❌ 错误：
content: "李明放下了手中的杯子，然后站起身来，走到了窗前。"

✅ 正确：
content: "李明放下杯子，起身走向窗前。"

原文：
> 老人说道："雾隐镇不欢迎外来人。"说完他转身走进了屋里。

❌ 错误：
content: "老人说道：雾隐镇不欢迎外来人。说完他转身走进了屋里。"

✅ 正确：
content: "老人吐出一口烟圈。"
（然后是对白元素）
content: "老人转身进屋，门板在身后关上。"

**D. 对话+叙述混合 → 拆开**
小说常把对话和叙述混在一起，你要把它们拆开：对话给 dialogue，动作给 action。

原文：
> "你走吧。"苗家起点点头说，"老师想开点儿啊。"

❌ 错误：
content: "苗家起点点头说，老师想开点儿啊。"

✅ 正确：
- action: "苗家起点点头。"
- dialogue (苗家起): "老师想开点儿啊。"

## 2. 对白处理

- 保留角色原话，不要改
- 说话人从"XX说道/说/问"中提取
- 表演指示（低声、愤怒地）放进 parenthetical
- 多人对话交替列出，不要混成一段
- 如果原文没有明确说话人，根据上下文推断

## 3. 场景分割

- **地点变化** = 新场景
- **时间变化** = 新场景
- **话题/情绪转折** = 新场景
- **对话被打断** = 新场景

**地点提取规则：**
- 真实的地点名词才能用（客厅、村口、河边、车上）
- 比喻/抽象表达不能当地点：❌"嗓子眼里"❌"口袋里"❌"冥世里"❌"别人眼里"
- 如果地点不明确，用"路上""某处"代替

## 4. 质量标准

每条 action content 必须满足：
1. **不超过 50 个中文字**（超出就是复制原文）
2. **不含"觉得""心想""感到"等心理动词**
3. **不含"了""着"等过去时态标志**
4. **不含"说道""问道"等叙事词**
5. **必须是现在时**（"他坐下"不是"他坐下了"）
6. **必须是可拍摄的画面**（观众能从银幕上看到）

**如果你不知道怎么改写一段原文，宁可删掉它，也不要复制粘贴。**

## 角色参考

{characters}

## 章节内容

{chapters_content}

## 输出格式

```yaml
acts:
  - act_number: {act_number}
    title: "幕标题"
    description: "幕内容简述"
    scenes:
      - scene_number: 1
        heading: "外景. 村道 - 日"
        location: "村道"
        time: "日"
        int_ext: "外景"
        description: "一句话概括这场戏"
        mood: "氛围"
        characters_present: ["角色A", "角色B"]
        elements:
          - type: action
            content: "精简的动作描述，现在时，可拍摄"
          - type: dialogue
            character: "角色A"
            content: "对白内容"
            parenthetical: "低声"
          - type: action
            content: "对白后的动作"
```

## 输出前自检（必须逐项回答）

1. 有没有任何 action content 超过 50 字？如果有，缩短它。
2. 有没有直接复制原文超过 10 个字？如果有，重写它。
3. 有没有"觉得""心想""感到"？如果有，改成动作。
4. 地点有没有比喻/抽象词？如果有，改成真实地点。
5. 所有 content 都是现在时吗？如果不是，改。
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
        temperature: float = 0.5,
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
