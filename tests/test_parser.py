"""
小说解析器测试
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from novel_to_script.parser import NovelParser


def long_chapter_content(num: int) -> str:
    """生成长章节内容"""
    paragraphs = []
    for i in range(10):
        paragraphs.append(
            f"这是段落{i+1}的内容。"
            "阳光明媚的早晨，主人公走在熙熙攘攘的街道上，"
            "周围的人群来来往往，每个人都有自己的故事。"
            "远处的山峦在晨雾中若隐若现，像一幅水墨画。"
            "街道两旁的店铺陆续开门，早点摊飘出阵阵香气。"
            "一只小狗跟在主人身后，摇着尾巴欢快地跑着。"
        )
    return "\n\n".join(paragraphs)


class TestNovelParser(unittest.TestCase):
    """测试 NovelParser 类"""

    def setUp(self):
        self.parser = NovelParser()

    def test_parse_empty_text(self):
        """测试空文本处理"""
        with self.assertRaises(ValueError):
            self.parser.parse("")

    def test_parse_simple_chapters(self):
        """测试简单章节解析"""
        text = (
            "第一章 初识\n\n" + long_chapter_content(1) + "\n\n"
            "第二章 相识\n\n" + long_chapter_content(2) + "\n\n"
            "第三章 离别\n\n" + long_chapter_content(3)
        )

        novel = self.parser.parse(text, title="测试小说", author="测试作者")

        self.assertEqual(len(novel.chapters), 3)
        self.assertEqual(novel.chapters[0].title, "初识")
        self.assertEqual(novel.chapters[1].title, "相识")
        self.assertEqual(novel.chapters[2].title, "离别")
        self.assertEqual(novel.title, "测试小说")
        self.assertEqual(novel.author, "测试作者")

    def test_parse_chinese_numerals(self):
        """测试中文数字章节"""
        text = (
            "第一回：风雨欲来\n\n" + long_chapter_content(1) + "\n\n"
            "第二回：暗流涌动\n\n" + long_chapter_content(2) + "\n\n"
            "第三回：真相大白\n\n" + long_chapter_content(3)
        )

        novel = self.parser.parse(text)
        self.assertEqual(len(novel.chapters), 3)

    def test_parse_english_chapters(self):
        """测试英文章节格式"""
        text = (
            "Chapter 1: The Beginning\n\n" + long_chapter_content(1) + "\n\n"
            "Chapter 2: The Middle\n\n" + long_chapter_content(2) + "\n\n"
            "Chapter 3: The End\n\n" + long_chapter_content(3)
        )

        novel = self.parser.parse(text)
        self.assertEqual(len(novel.chapters), 3)
        self.assertEqual(novel.chapters[0].title, "The Beginning")

    def test_preprocess(self):
        """测试文本预处理"""
        text = "第一行\r\n第二行\r\n\n\n\n\n第三行"
        result = self.parser._preprocess(text)
        self.assertIn("\n\n", result)
        self.assertNotIn("\r", result)

    def test_get_chapter_summary(self):
        """测试章节摘要生成"""
        text = (
            "第一章 测试\n\n" + long_chapter_content(1) + "\n\n"
            "第二章 测试2\n\n" + long_chapter_content(2)
        )

        novel = self.parser.parse(text, title="摘要测试")
        summary = self.parser.get_chapter_summary(novel)

        self.assertIn("摘要测试", summary)
        self.assertIn("章节数：2", summary)
        self.assertIn("第 1 章", summary)


class TestNovelParserEdgeCases(unittest.TestCase):
    """测试边界情况"""

    def setUp(self):
        self.parser = NovelParser()

    def test_no_chapter_markers(self):
        """测试无章节标记的文本"""
        text = "这是一个没有章节标记的长文本。" + "这是内容。" * 100
        novel = self.parser.parse(text)
        # 应该分割为多个部分或作为一个整体
        self.assertGreaterEqual(len(novel.chapters), 1)

    def test_single_chapter(self):
        """测试单章文本"""
        # 使用长内容确保超过 min_chapter_length
        content = long_chapter_content(1) + "\n\n" + long_chapter_content(1)
        text = "第一章 唯一\n\n" + content
        novel = self.parser.parse(text)
        self.assertEqual(len(novel.chapters), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
