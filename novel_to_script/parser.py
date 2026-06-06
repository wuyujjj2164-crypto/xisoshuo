"""
小说文本解析器

将原始小说文本分割为章节，提取章节标题和内容。
支持多种章节格式检测（第X章、Chapter X、数字标题等）。
"""

import re

from .models import Chapter, Novel


class NovelParser:
    """
    小说文本解析器

    负责将原始小说文本解析为结构化的 Novel 对象。
    核心功能是章节分割和元数据提取。
    """

    # 章节标题匹配模式
    CHAPTER_PATTERNS = [
        # 中文格式：第一章、第1章、第 一 章
        r"^(?:第\s*[一二三四五六七八九十百千万零\d]+\s*章)[：:\s]*(.+?)$",
        # 中文格式：第一回、第1回
        r"^(?:第\s*[一二三四五六七八九十百千万零\d]+\s*回)[：:\s]*(.+?)$",
        # 中文格式：第1章 标题（无分隔符）
        r"^(?:第\s*\d+\s*章)\s*(.+?)$",
        # 英文格式：Chapter 1 / Chapter One
        r"^(?:Chapter\s+[\dIVXLCivxlc]+)[\s:.-]*(.+?)$",
        # 分隔线格式：=== 第一章 ===
        r"^[\=\-\*\#\s]+(?:第\s*\d+\s*章)[\s\=\-\*\#]*(.+?)$",
    ]

    def __init__(self, min_chapter_length: int = 200):
        """
        初始化解析器

        Args:
            min_chapter_length: 最小章节长度（字符数），低于此值的段落将被忽略
        """
        self.min_chapter_length = min_chapter_length
        self._compiled_patterns = [
            re.compile(p, re.MULTILINE | re.IGNORECASE) for p in self.CHAPTER_PATTERNS
        ]

    def parse(self, text: str, title: str = "", author: str = "") -> Novel:
        """
        解析小说文本

        Args:
            text: 原始小说文本
            title: 小说标题（如已知）
            author: 作者（如已知）

        Returns:
            Novel 对象

        Raises:
            ValueError: 文本为空或无法解析出章节
        """
        if not text or not text.strip():
            raise ValueError("小说文本不能为空")

        text = self._preprocess(text)
        chapters = self._split_chapters(text)

        if len(chapters) < 1:
            # 如果无法识别章节，将整个文本作为一个章节
            chapters = [
                Chapter(number=1, title="全文", content=text.strip())
            ]

        return Novel(title=title, author=author, chapters=chapters)

    def _preprocess(self, text: str) -> str:
        """
        预处理文本

        统一换行符、去除多余空白、修复常见编码问题。
        """
        # 统一换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # 去除 BOM
        text = text.lstrip("﻿")
        # 去除多余空行（保留段落分隔）
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 统一中文标点
        text = text.replace("．", ".")
        return text.strip()

    def _split_chapters(self, text: str) -> list[Chapter]:
        """
        分割章节

        使用多种模式检测章节标题，将文本分割为章节列表。

        Args:
            text: 预处理后的文本

        Returns:
            Chapter 列表
        """
        chapters = []

        # 尝试所有模式，使用匹配最多的
        best_result = None
        best_count = 0

        for pattern in self._compiled_patterns:
            result = self._split_with_pattern(text, pattern)
            if len(result) > best_count and len(result) >= 1:
                best_count = len(result)
                best_result = result

        # 如果找到有效分割，使用最佳结果
        if best_result is not None:
            chapters = best_result
        else:
            # 回退策略：尝试按大段空白分割
            chapters = self._split_by_paragraphs(text)

        # 过滤过短的章节
        filtered = [c for c in chapters if c.word_count >= self.min_chapter_length]

        # 如果过滤后为空，回退到段落分割
        if not filtered and chapters:
            filtered = chapters[:3]  # 至少保留前3章

        chapters = filtered

        # 重新编号
        for i, ch in enumerate(chapters, 1):
            ch.number = i

        return chapters

    def _split_with_pattern(self, text: str, pattern: re.Pattern) -> list[Chapter]:
        """使用特定模式分割章节"""
        chapters = []
        matches = list(pattern.finditer(text))

        if len(matches) < 1:
            return []

        if len(matches) == 1:
            # 只有一个章节标记，将整个文本作为一章
            match = matches[0]
            title = match.group(1).strip() if match.group(1) else "全文"
            content = text[match.end():].strip()
            return [Chapter(number=1, title=title, content=content)]

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            chapter_text = text[start:end].strip()
            title = match.group(1).strip() if match.group(1) else f"第 {i + 1} 章"
            content = chapter_text[len(match.group(0)):].strip()

            # 清理标题中的换行
            title = title.split("\n")[0].strip()

            chapters.append(
                Chapter(number=i + 1, title=title, content=content)
            )

        return chapters

    def _split_by_paragraphs(self, text: str) -> list[Chapter]:
        """
        按段落回退分割

        当无法识别章节标题时，将文本均匀分割为多个部分。
        每部分至少包含一定数量的段落。
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if len(paragraphs) < 6:
            # 段落太少，作为一个整体
            return [Chapter(number=1, title="全文", content=text)]

        # 目标：分成 3-10 个"章节"
        target_chapters = min(max(len(paragraphs) // 5, 3), 10)
        paras_per_chapter = len(paragraphs) // target_chapters

        chapters = []
        for i in range(target_chapters):
            start = i * paras_per_chapter
            end = start + paras_per_chapter if i < target_chapters - 1 else len(paragraphs)

            content = "\n\n".join(paragraphs[start:end])
            chapters.append(
                Chapter(number=i + 1, title=f"第 {i + 1} 部分", content=content)
            )

        return chapters

    def get_chapter_summary(self, novel: Novel) -> str:
        """
        获取章节摘要

        Args:
            novel: Novel 对象

        Returns:
            格式化的章节摘要字符串
        """
        lines = [
            f"小说：{novel.title or '未命名'}",
            f"作者：{novel.author or '未知'}",
            f"章节数：{len(novel.chapters)}",
            f"总字数：{novel.total_word_count}",
            "-" * 40,
        ]

        for ch in novel.chapters:
            lines.append(f"第 {ch.number} 章：{ch.title} ({ch.word_count} 字)")

        return "\n".join(lines)
