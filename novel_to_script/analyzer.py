"""
小说场景和角色分析器

分析小说文本，提取角色信息和场景边界。
为后续的 AI 转换提供结构化输入。
"""

import re

from .models import Chapter, Character, CharacterImportance, Novel


class NovelAnalyzer:
    """
    小说分析器

    分析小说文本，提取：
    1. 角色列表（名称、出场频率、关系）
    2. 场景位置信息（地点、时间）
    3. 对话片段（用于理解角色语言风格）
    """

    def __init__(self):
        self._name_pattern = re.compile(
            r"([一-龥]{2,4})(?:说道|说|问|答道|回答|喊道|叫道|喃喃|低语)"
        )
        self._location_indicators = [
            "在", "来到", "走进", "走出", "站在", "坐在", "回到",
            "离开", "前往", "抵达", "到达",
        ]
        self._time_indicators = [
            "清晨", "早晨", "上午", "中午", "下午", "傍晚", "黄昏",
            "晚上", "夜晚", "深夜", "黎明", "半夜", "午夜",
            "第二天", "次日", "几天后", "数日后",
        ]

    def analyze(self, novel: Novel) -> dict:
        """
        全面分析小说

        Args:
            novel: Novel 对象

        Returns:
            分析结果字典，包含角色、场景、对话等信息
        """
        all_text = "\n\n".join(ch.content for ch in novel.chapters)

        return {
            "characters": self._extract_characters(novel),
            "locations": self._extract_locations(all_text),
            "timeline": self._extract_timeline(all_text),
            "dialogue_samples": self._extract_dialogue_samples(novel),
            "chapter_summaries": self._summarize_chapters(novel),
        }

    def _extract_characters(self, novel: Novel) -> list[Character]:
        """
        提取角色信息

        基于对话动词识别人名，统计出场频率。
        """
        name_counts: dict[str, int] = {}
        name_contexts: dict[str, list[str]] = {}

        for chapter in novel.chapters:
            # 查找说话人
            matches = self._name_pattern.finditer(chapter.content)
            for m in matches:
                name = m.group(1)
                # 过滤常见误识别
                if self._is_valid_name(name):
                    name_counts[name] = name_counts.get(name, 0) + 1

                    # 记录上下文
                    start = max(0, m.start() - 50)
                    end = min(len(chapter.content), m.end() + 50)
                    context = chapter.content[start:end].replace("\n", " ")
                    if name not in name_contexts:
                        name_contexts[name] = []
                    name_contexts[name].append(context)

        # 按出场频率排序
        sorted_names = sorted(name_counts.items(), key=lambda x: x[1], reverse=True)

        characters = []
        for i, (name, count) in enumerate(sorted_names[:30], 1):  # 最多30个角色
            # 确定重要性
            total_mentions = sum(name_counts.values())
            ratio = count / total_mentions if total_mentions > 0 else 0

            if ratio > 0.15:
                importance = CharacterImportance.MAIN
            elif ratio > 0.03:
                importance = CharacterImportance.SUPPORTING
            else:
                importance = CharacterImportance.MINOR

            # 提取描述（从上下文中找形容词）
            description = self._extract_description(name_contexts.get(name, []))

            characters.append(
                Character(
                    id=f"char_{i:03d}",
                    name=name,
                    description=description,
                    importance=importance,
                )
            )

        return characters

    def _is_valid_name(self, name: str) -> bool:
        """验证是否为有效人名（排除常见误识别）"""
        # 排除常见动词和副词
        invalid_names = {
            "于是", "因此", "然而", "但是", "不过", "虽然", "因为",
            "已经", "正在", "将要", "曾经", "忽然", "突然", "慢慢",
            "缓缓", "轻轻", "紧紧", "默默", "悄悄", "暗暗", "纷纷",
            "只见", "只听", "只觉", "心中", "脸上", "眼中",
            "不由得", "忍不住", "不禁", "不觉",
            "或者", "而且", "并且", "况且", "何况", "反而",
            "老人", "女人", "男人", "女孩", "男孩", "孩子",
            "没有", "不是", "不能", "不会", "不要", "不敢",
            "不解地", "也不抬地",
        }
        return name not in invalid_names and len(name) >= 2

    def _extract_description(self, contexts: list[str]) -> str:
        """从上下文中提取角色描述"""
        if not contexts:
            return ""

        # 简单策略：取第一个包含该角色且长度合适的上下文
        for ctx in contexts[:3]:
            if 20 < len(ctx) < 100:
                return ctx.strip()

        return contexts[0][:100].strip() if contexts else ""

    def _extract_locations(self, text: str) -> list[dict]:
        """
        提取场景地点

        识别文本中提到的地点名称。
        """
        locations = []

        # 匹配常见地点模式
        location_patterns = [
            r"(?:来到|走进|走出|站在|坐在|回到|离开|前往)(?:了|到)?\s*([一-龥]{1,8}(?:房间|屋|厅|院|楼|阁|亭|台|庙|寺|府|宅|城|镇|村|街|路|山|河|林|园|室|馆|店|铺|房))",
            r"([一-龥]{1,6}(?:房间|屋|厅|院|楼|阁|亭|府|宅|城|镇|村|街|路|山|河|林|园|室|馆|店|铺))(?:里|中|内|外|上|下|前|后)",
        ]

        loc_counts: dict[str, int] = {}
        for pattern in location_patterns:
            for match in re.finditer(pattern, text):
                loc = match.group(1)
                loc_counts[loc] = loc_counts.get(loc, 0) + 1

        # 按频率排序
        for loc, count in sorted(loc_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            locations.append({"name": loc, "mentions": count})

        return locations

    def _extract_timeline(self, text: str) -> list[str]:
        """提取时间线索"""
        timeline = []
        for indicator in self._time_indicators:
            if indicator in text:
                timeline.append(indicator)
        return list(set(timeline))  # 去重

    def _extract_dialogue_samples(self, novel: Novel, max_per_char: int = 3) -> dict[str, list[str]]:
        """
        提取角色对话样本

        用于理解角色的语言风格和说话方式。
        """
        samples: dict[str, list[str]] = {}

        dialogue_pattern = re.compile(
            r'([一-龥]{2,4})(?:说道|说|问|答道|回答|喊道|叫道)[：:\s]*"([^"]*)"'
        )

        for chapter in novel.chapters:
            for match in dialogue_pattern.finditer(chapter.content):
                name = match.group(1)
                line = match.group(2)

                if not self._is_valid_name(name):
                    continue

                if name not in samples:
                    samples[name] = []

                if len(samples[name]) < max_per_char and len(line) > 5:
                    samples[name].append(line)

        return samples

    def _summarize_chapters(self, novel: Novel) -> list[dict]:
        """
        生成章节概要

        提取每章的关键信息用于 AI 处理。
        """
        summaries = []

        for ch in novel.chapters:
            # 提取首段和尾段作为摘要
            paragraphs = [p.strip() for p in ch.content.split("\n\n") if p.strip()]
            beginning = paragraphs[0][:200] if paragraphs else ""
            ending = paragraphs[-1][:200] if paragraphs else ""

            # 统计本章对话比例（匹配弯引号和直引号，计算字符总数而非段数）
            dialogue_matches = re.findall(r'[""""""]([^""""""]{0,500})[""""""]', ch.content)
            dialogue_chars = sum(len(m) for m in dialogue_matches)
            total_chars = len(ch.content)
            dialogue_ratio = dialogue_chars / total_chars if total_chars > 0 else 0

            summaries.append({
                "number": ch.number,
                "title": ch.title,
                "word_count": ch.word_count,
                "paragraphs": len(paragraphs),
                "dialogue_ratio": round(dialogue_ratio, 3),
                "beginning": beginning,
                "ending": ending,
            })

        return summaries

    def prepare_conversion_input(self, novel: Novel, analysis: dict) -> str:
        """
        准备转换输入

        将小说和分析结果整理为适合 AI 处理的格式。

        Args:
            novel: Novel 对象
            analysis: 分析结果

        Returns:
            格式化后的输入文本
        """
        lines = [
            "# 小说转剧本输入",
            f"",
            f"## 基本信息",
            f"- 标题：{novel.title or '未命名'}",
            f"- 作者：{novel.author or '未知'}",
            f"- 章节数：{len(novel.chapters)}",
            f"- 总字数：{novel.total_word_count}",
            f"",
            "## 角色列表",
        ]

        for char in analysis["characters"][:10]:
            lines.append(f"- {char.name} ({char.importance.value}): {char.description[:50]}")

        lines.extend([
            "",
            "## 主要地点",
        ])

        for loc in analysis["locations"][:5]:
            lines.append(f"- {loc['name']} (出现 {loc['mentions']} 次)")

        lines.extend([
            "",
            "## 章节概要",
        ])

        for summary in analysis["chapter_summaries"]:
            lines.append(f"### 第 {summary['number']} 章：{summary['title']}")
            lines.append(f"- 字数：{summary['word_count']}")
            lines.append(f"- 对话比例：{summary['dialogue_ratio']:.1%}")
            lines.append(f"- 开头：{summary['beginning'][:80]}...")

        return "\n".join(lines)
