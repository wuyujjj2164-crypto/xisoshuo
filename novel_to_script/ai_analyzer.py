"""
AI 智能分析器

调用 LLM API（Claude / DeepSeek / 通义千问等）进行高质量的小说分析。
相比本地规则分析，AI 分析能更准确地识别角色、地点、场景和时间线。
"""

import json
import os
import re
from typing import Any

from .models import Character, CharacterImportance, Novel


ANALYSIS_PROMPT = """你是一位资深文学分析师，擅长分析小说文本的结构、角色和场景。

## 任务
请分析以下小说内容，提取以下信息并以 JSON 格式返回：

1. **characters**: 角色列表（每个角色包含 name, importance, description）
   - name: 角色姓名
   - importance: 角色重要性，可选值 "main"（主角）/ "supporting"（配角）/ "minor"（龙套）
   - description: 角色简短描述（身份、性格特征，30字以内）
   - 注意：只提取有名字的真实角色，不要提取泛称如"老人""女人""男孩"等（除非这是该角色的唯一称呼）

2. **locations**: 地点列表（每个地点包含 name）
   - 提取小说中出现的具体地点名称
   - 如：客厅、客栈、村口、老宅、地下室、洞穴等
   - 不要提取动作描述如"走进屋里""来到镇上"，只提取地点名词

3. **timeline**: 时间线索列表
   - 提取小说中出现的具体时间词，如：清晨、中午、傍晚、深夜、第二天等

## 输出格式
请严格按以下 JSON 格式输出，不要添加任何解释文字：

```json
{
  "characters": [
    {"name": "角色A", "importance": "main", "description": "省报记者，好奇心强"},
    {"name": "角色B", "importance": "supporting", "description": "客栈老板，知道镇上秘密"}
  ],
  "locations": [
    {"name": "镇口"},
    {"name": "客栈"},
    {"name": "老宅"}
  ],
  "timeline": ["清晨", "深夜", "第二天"]
}
```

## 小说内容

{content}
"""

BATCH_ANALYSIS_PROMPT = """你是一位资深文学分析师。请分析以下小说章节（第 {batch_num}/{total_batches} 批）。

提取所有角色、地点和时间线索，以 JSON 格式返回。

## 角色提取规则
- 只提取有明确称呼的角色（人名或特定称谓如"守灵人"）
- 排除泛称：老人、女人、男人、女孩、男孩、孩子、老板（除非这是唯一称呼）
- 为每个角色标注重要性：main（主角，出场最多）、supporting（配角）、minor（龙套）
- 提供简短描述（身份/性格，30字以内）

## 地点提取规则
- 只提取地点名词：客厅、客栈、村口、老宅、地下室
- 排除动作描述片段：不要提取"走进屋里""来到镇上"中的动词部分

## 时间线提取规则
- 提取明确的时间词：清晨、上午、中午、下午、傍晚、晚上、深夜、黎明、半夜、第二天、次日

## 输出格式（严格 JSON，不要解释）

```json
{
  "characters": [
    {"name": "...", "importance": "main|supporting|minor", "description": "..."}
  ],
  "locations": [
    {"name": "..."}
  ],
  "timeline": ["..."]
}
```

## 章节内容

{chapters_content}
"""


class AINovelAnalyzer:
    """
    AI 智能小说分析器

    使用 LLM API 进行高质量的小说结构分析。
    支持 Anthropic Claude 和 OpenAI 兼容格式的 API（DeepSeek、通义千问等）。
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        provider: str = "anthropic",
        base_url: str | None = None,
    ):
        """
        初始化 AI 分析器

        Args:
            api_key: API 密钥（默认从环境变量读取）
            model: 使用的模型名称
            max_tokens: 单次请求最大输出 token 数
            temperature: 创造性程度 (0.0-1.0)
            provider: API 提供商，可选 "anthropic" / "openai" / "kimi"
            base_url: OpenAI 兼容 API 的基础 URL（如 DeepSeek、通义千问、Kimi）
        """
        self.provider = provider.lower()
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
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

    def analyze(self, novel: Novel) -> dict:
        """
        使用 AI 全面分析小说

        Args:
            novel: Novel 对象

        Returns:
            分析结果字典，格式与 NovelAnalyzer.analyze() 一致
        """
        # 如果小说较短（< 8000 字），直接一次性分析
        total_text = "\n\n".join(
            f"第 {ch.number} 章：{ch.title}\n{ch.content}"
            for ch in novel.chapters
        )

        if len(total_text) < 8000:
            return self._analyze_single(total_text)

        # 长文本分批分析后合并
        return self._analyze_batches(novel)

    def _analyze_single(self, text: str) -> dict:
        """单次分析短文本"""
        prompt = ANALYSIS_PROMPT.format(content=text)
        response = self._call_api(prompt)
        return self._parse_response(response)

    def _analyze_batches(self, novel: Novel) -> dict:
        """分批分析长文本并合并结果"""
        all_characters: dict[str, dict] = {}
        all_locations: dict[str, int] = {}
        all_timeline: set[str] = set()

        # 每批 3 个章节
        batch_size = 3
        chapters = novel.chapters

        for i in range(0, len(chapters), batch_size):
            batch = chapters[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(chapters) + batch_size - 1) // batch_size

            chapters_content = "\n\n".join(
                f"第 {ch.number} 章：{ch.title}\n{ch.content[:3000]}"
                for ch in batch
            )

            prompt = BATCH_ANALYSIS_PROMPT.format(
                batch_num=batch_num,
                total_batches=total_batches,
                chapters_content=chapters_content,
            )

            response = self._call_api(prompt)
            result = self._parse_response(response)

            # 合并角色（按名字去重，保留重要性最高的）
            for char in result.get("characters", []):
                name = char["name"]
                if name not in all_characters:
                    all_characters[name] = char
                else:
                    # 如果新结果是主角，覆盖旧的
                    importance_order = {"main": 3, "supporting": 2, "minor": 1}
                    old_imp = importance_order.get(all_characters[name].get("importance", "minor"), 1)
                    new_imp = importance_order.get(char.get("importance", "minor"), 1)
                    if new_imp > old_imp:
                        all_characters[name] = char

            # 合并地点
            for loc in result.get("locations", []):
                name = loc["name"]
                all_locations[name] = all_locations.get(name, 0) + 1

            # 合并时间线
            all_timeline.update(result.get("timeline", []))

        # 转换为标准格式
        characters = self._build_characters(all_characters)
        locations = [{"name": name, "mentions": count} for name, count in sorted(
            all_locations.items(), key=lambda x: x[1], reverse=True
        )]
        timeline = sorted(all_timeline)

        return {
            "characters": characters,
            "locations": locations,
            "timeline": timeline,
            "dialogue_samples": {},  # AI 分析暂不提供对话样本
            "chapter_summaries": [],  # AI 分析暂不提供章节摘要
        }

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

    def _parse_response(self, text: str) -> dict:
        """
        解析 API 响应，提取 JSON 数据
        """
        # 尝试从 markdown 代码块中提取 JSON
        patterns = [
            r"```json\s*(.*?)\s*```",  # ```json ... ```
            r"```\s*(\{.*?\})\s*```",  # ``` { ... } ```
            r"(\{[\s\S]*\"characters\"[\s\S]*\})",  # 最宽松的 JSON 匹配
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        # 如果都没匹配到，尝试直接解析整个文本
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # 兜底：返回空结构
        return {
            "characters": [],
            "locations": [],
            "timeline": [],
        }

    def _build_characters(self, char_dict: dict[str, dict]) -> list[Character]:
        """将字典转换为 Character 对象列表"""
        # 按重要性排序
        importance_order = {"main": 3, "supporting": 2, "minor": 1}
        sorted_chars = sorted(
            char_dict.items(),
            key=lambda x: importance_order.get(x[1].get("importance", "minor"), 1),
            reverse=True,
        )

        characters = []
        for i, (name, data) in enumerate(sorted_chars[:30], 1):
            imp_str = data.get("importance", "minor")
            try:
                importance = CharacterImportance(imp_str)
            except ValueError:
                importance = CharacterImportance.MINOR

            characters.append(
                Character(
                    id=f"char_{i:03d}",
                    name=name,
                    description=data.get("description", ""),
                    importance=importance,
                )
            )

        return characters
