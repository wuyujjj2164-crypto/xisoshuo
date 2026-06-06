"""
YAML 格式化输出器

将剧本对象序列化为 YAML 文件，支持自定义格式和样式。
"""

from typing import Any

import yaml

from .models import Screenplay


class YAMLFormatter:
    """
    YAML 格式化器

    负责将 Screenplay 对象序列化为符合剧本规范的 YAML 文件。
    支持自定义缩进、排序、注释等格式选项。
    """

    def __init__(self, indent: int = 2, default_flow_style: bool = False):
        """
        初始化格式化器

        Args:
            indent: YAML 缩进空格数
            default_flow_style: 是否使用流式风格（默认否，使用块风格）
        """
        self.indent = indent
        self.default_flow_style = default_flow_style

    def format(self, screenplay: Screenplay) -> str:
        """
        将剧本对象格式化为 YAML 字符串

        Args:
            screenplay: Screenplay 对象

        Returns:
            YAML 格式字符串
        """
        data = {"screenplay": screenplay.to_yaml_dict()}
        return self._to_yaml(data)

    def save(self, screenplay: Screenplay, filepath: str) -> None:
        """
        将剧本保存为 YAML 文件

        Args:
            screenplay: Screenplay 对象
            filepath: 输出文件路径
        """
        yaml_content = self.format(screenplay)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(yaml_content)

    def _to_yaml(self, data: dict[str, Any]) -> str:
        """
        将字典序列化为 YAML 字符串

        使用自定义格式确保输出符合剧本规范。
        """
        # 使用 allow_unicode 确保中文正确输出
        yaml_content = yaml.dump(
            data,
            allow_unicode=True,
            sort_keys=False,  # 保持键的顺序
            default_flow_style=self.default_flow_style,
            indent=self.indent,
            width=9999,  # 禁用自动换行，保持长字符串完整
        )

        # 添加文件头部注释
        header = self._generate_header()

        return header + yaml_content

    def _generate_header(self) -> str:
        """生成 YAML 文件头部注释"""
        return """# 剧本文件
# 本文件由 AI 小说转剧本工具自动生成
# 可直接编辑修改，支持 YAML 格式规范
#
# 结构说明：
#   - metadata: 剧本元数据（标题、作者等）
#   - characters: 角色列表
#   - acts: 幕列表
#     - scenes: 场景列表
#       - elements: 场景元素（action/dialogue/transition 等）
#

"""

    def validate(self, yaml_content: str) -> tuple[bool, str]:
        """
        验证 YAML 内容是否符合剧本 Schema

        Args:
            yaml_content: YAML 字符串

        Returns:
            (是否有效, 错误信息)
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return False, f"YAML 格式错误: {e}"

        # 检查必需字段
        if "screenplay" not in data:
            return False, "缺少根节点 'screenplay'"

        sp = data["screenplay"]

        if "metadata" not in sp:
            return False, "缺少 'metadata' 节点"

        if "acts" not in sp:
            return False, "缺少 'acts' 节点"

        if not isinstance(sp["acts"], list) or len(sp["acts"]) == 0:
            return False, "'acts' 必须是非空列表"

        # 检查每个 act
        for i, act in enumerate(sp["acts"]):
            if "scenes" not in act:
                return False, f"第 {i + 1} 幕缺少 'scenes'"

            for j, scene in enumerate(act.get("scenes", [])):
                if "heading" not in scene:
                    return False, f"第 {i + 1} 幕第 {j + 1} 场缺少 'heading'"

                for k, elem in enumerate(scene.get("elements", [])):
                    if "type" not in elem:
                        return False, f"元素缺少 'type': 幕{i+1}场{j+1}元素{k+1}"
                    if "content" not in elem:
                        return False, f"元素缺少 'content': 幕{i+1}场{j+1}元素{k+1}"

                    if elem.get("type") == "dialogue" and "character" not in elem:
                        return False, f"对白缺少 'character': 幕{i+1}场{j+1}"

        return True, "验证通过"
