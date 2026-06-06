"""
小说分析器测试
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from novel_to_script.analyzer import NovelAnalyzer
from novel_to_script.models import Chapter, Novel


class TestNovelAnalyzer(unittest.TestCase):
    """测试 NovelAnalyzer 类"""

    def setUp(self):
        self.analyzer = NovelAnalyzer()

    def test_extract_characters(self):
        """测试角色提取"""
        novel = Novel(
            chapters=[
                Chapter(
                    number=1,
                    title="第一章",
                    content=(
                        "张三走进房间，看见李四正在喝茶。"
                        "李四说道：你来了。"
                        "张三说道：路上有点事耽搁了。"
                        "王五问道：两位在聊什么？"
                        "张三回答：没什么，就是叙叙旧。"
                    ),
                )
            ]
        )

        analysis = self.analyzer.analyze(novel)
        characters = analysis["characters"]

        names = {c.name for c in characters}
        self.assertIn("张三", names)
        self.assertIn("李四", names)
        self.assertIn("王五", names)

    def test_extract_locations(self):
        """测试地点提取"""
        novel = Novel(
            chapters=[
                Chapter(
                    number=1,
                    title="第一章",
                    content=(
                        "张三走进客厅，看见李四正坐在沙发上。"
                        "随后他们来到院子里，发现王五正在树下。"
                        "三人一起走向村口。"
                    ),
                )
            ]
        )

        analysis = self.analyzer.analyze(novel)
        locations = analysis["locations"]

        self.assertTrue(len(locations) > 0)
        location_names = {loc["name"] for loc in locations}
        self.assertIn("客厅", location_names)

    def test_extract_timeline(self):
        """测试时间线索提取"""
        novel = Novel(
            chapters=[
                Chapter(
                    number=1,
                    title="第一章",
                    content=(
                        "清晨，张三起床。"
                        "到了中午，他吃过饭。"
                        "傍晚时分，他来到镇上。"
                        "深夜，他才回到家。"
                    ),
                )
            ]
        )

        analysis = self.analyzer.analyze(novel)
        timeline = analysis["timeline"]

        self.assertIn("清晨", timeline)
        self.assertIn("中午", timeline)
        self.assertIn("傍晚", timeline)
        self.assertIn("深夜", timeline)

    def test_extract_dialogue_samples(self):
        """测试对话样本提取"""
        novel = Novel(
            chapters=[
                Chapter(
                    number=1,
                    title="第一章",
                    content=(
                        '张三说道："今天天气不错。"'
                        '李四回答："是啊，很适合出门。"'
                        '张三又说："我们去公园吧。"'
                    ),
                )
            ]
        )

        analysis = self.analyzer.analyze(novel)
        samples = analysis["dialogue_samples"]

        self.assertIn("张三", samples)
        self.assertTrue(len(samples["张三"]) > 0)

    def test_summarize_chapters(self):
        """测试章节摘要"""
        novel = Novel(
            chapters=[
                Chapter(
                    number=1,
                    title="第一章",
                    content=(
                        "这是第一章的开头。\n\n"
                        "中间有一些内容。\n\n"
                        '张三说道："这是对话。"\n\n'
                        "这是结尾。"
                    ),
                )
            ]
        )

        analysis = self.analyzer.analyze(novel)
        summaries = analysis["chapter_summaries"]

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["number"], 1)
        self.assertEqual(summaries[0]["title"], "第一章")
        self.assertTrue(summaries[0]["paragraphs"] > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
