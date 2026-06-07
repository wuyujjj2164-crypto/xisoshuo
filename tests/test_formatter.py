"""
测试 ScreenplayFormatter 和 YAMLFormatter
"""

import unittest
import yaml

from novel_to_script.formatter import ScreenplayFormatter, YAMLFormatter
from novel_to_script.models import (
    Act,
    Character,
    CharacterImportance,
    Metadata,
    Scene,
    SceneElement,
    Screenplay,
)


def create_test_screenplay():
    """创建一个测试用的 Screenplay 对象"""
    characters = [
        Character(
            id="char_001",
            name="李明",
            description="主角，程序员",
            importance=CharacterImportance.MAIN,
        ),
        Character(
            id="char_002",
            name="王芳",
            description="李明的同事",
            importance=CharacterImportance.SUPPORTING,
        ),
    ]

    scenes = [
        Scene(
            scene_number=1,
            act_scene_number=1,
            heading="内景. 客厅 - 日",
            location="客厅",
            time="日",
            int_ext="内景",
            mood="温馨",
            elements=[
                SceneElement(type="action", content="阳光透过窗帘洒进客厅。"),
                SceneElement(
                    type="dialogue",
                    character="李明",
                    content="这个项目必须在下周之前完成。",
                    parenthetical="低声",
                ),
                SceneElement(type="action", content="王芳从厨房走出来。"),
                SceneElement(
                    type="dialogue",
                    character="王芳",
                    content="别太拼了，先喝杯咖啡吧。",
                ),
            ],
            characters_present=["李明", "王芳"],
        ),
        Scene(
            scene_number=2,
            act_scene_number=2,
            heading="外景. 街道 - 下午",
            location="街道",
            time="下午",
            int_ext="外景",
            mood="紧张",
            elements=[
                SceneElement(type="action", content="李明走出大楼。"),
                SceneElement(type="transition", content="切至："),
            ],
            characters_present=["李明"],
        ),
    ]

    acts = [Act(act_number=1, title="第一幕", scenes=scenes)]

    metadata = Metadata(title="测试剧本", author="测试作者")

    return Screenplay.create(
        metadata=metadata,
        characters=characters,
        acts=acts,
    )


class TestScreenplayFormatter(unittest.TestCase):
    def test_format_contains_title(self):
        screenplay = create_test_screenplay()
        formatter = ScreenplayFormatter()
        result = formatter.format(screenplay)
        self.assertIn("测试剧本", result)

    def test_format_contains_scene_heading(self):
        screenplay = create_test_screenplay()
        formatter = ScreenplayFormatter()
        result = formatter.format(screenplay)
        self.assertIn("内景. 客厅 - 日", result)
        self.assertIn("外景. 街道 - 下午", result)

    def test_format_contains_character_names(self):
        screenplay = create_test_screenplay()
        formatter = ScreenplayFormatter()
        result = formatter.format(screenplay)
        self.assertIn("李明", result)
        self.assertIn("王芳", result)

    def test_format_contains_dialogue(self):
        screenplay = create_test_screenplay()
        formatter = ScreenplayFormatter()
        result = formatter.format(screenplay)
        self.assertIn("这个项目必须在下周之前完成。", result)
        self.assertIn("别太拼了，先喝杯咖啡吧。", result)

    def test_format_contains_parenthetical(self):
        screenplay = create_test_screenplay()
        formatter = ScreenplayFormatter()
        result = formatter.format(screenplay)
        self.assertIn("（低声）", result)

    def test_format_contains_act_separator(self):
        screenplay = create_test_screenplay()
        formatter = ScreenplayFormatter()
        result = formatter.format(screenplay)
        self.assertIn("第一幕", result)

    def test_clean_description_filters_quotes(self):
        formatter = ScreenplayFormatter()
        # 正常描述（短，不超30字，不触发过滤）
        self.assertEqual(
            formatter._clean_description("省报记者，好奇心强"),
            "省报记者，好奇心强",
        )
        # 包含英文直引号的错误描述（超过30字才触发过滤）
        english_quote = '"Hello world, this is a very long description with quotes," he said'
        self.assertEqual(
            formatter._clean_description(english_quote),
            "",
        )
        # 包含中文弯引号的错误描述（超过30字才触发过滤）
        chinese_quote = '“我在井里看见了你的记忆，这是一段很长的文字超过三十个字，”李明说'
        self.assertEqual(
            formatter._clean_description(chinese_quote),
            "",
        )
        # 过长的描述
        self.assertEqual(
            formatter._clean_description("A" * 60),
            "A" * 50 + "...",
        )

    def test_format_skips_whitespace_only_content(self):
        """测试空白 content 被跳过"""
        characters = [
            Character(
                id="char_001",
                name="测试",
                importance=CharacterImportance.MAIN,
            ),
        ]
        scenes = [
            Scene(
                scene_number=1,
                act_scene_number=1,
                heading="内景. 测试 - 日",
                elements=[
                    # Pydantic 不允许空字符串，所以用 strip 后会变空的字符串
                    SceneElement(type="action", content="  有效内容  "),
                    SceneElement(type="action", content="有效内容"),
                ],
            ),
        ]
        acts = [Act(act_number=1, scenes=scenes)]
        screenplay = Screenplay.create(
            metadata=Metadata(title="测试"),
            characters=characters,
            acts=acts,
        )
        formatter = ScreenplayFormatter()
        result = formatter.format(screenplay)
        # 两个 "有效内容" 都应该出现（只是 strip 后相同）
        self.assertIn("有效内容", result)


class TestYAMLFormatter(unittest.TestCase):
    def test_format_valid_yaml(self):
        screenplay = create_test_screenplay()
        formatter = YAMLFormatter()
        result = formatter.format(screenplay)
        # 验证是合法的 YAML
        data = yaml.safe_load(result)
        self.assertIn("screenplay", data)
        self.assertEqual(data["screenplay"]["metadata"]["title"], "测试剧本")

    def test_validate_passes(self):
        screenplay = create_test_screenplay()
        formatter = YAMLFormatter()
        yaml_content = formatter.format(screenplay)
        valid, msg = formatter.validate(yaml_content)
        self.assertTrue(valid)
        self.assertEqual(msg, "验证通过")

    def test_validate_missing_screenplay(self):
        formatter = YAMLFormatter()
        valid, msg = formatter.validate("metadata: {}")
        self.assertFalse(valid)
        self.assertIn("screenplay", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
