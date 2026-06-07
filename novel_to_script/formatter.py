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


class ScreenplayFormatter:
    """
    标准剧本格式输出器

    将 Screenplay 对象格式化为标准的好莱坞剧本纯文本格式。
    适合直接打印或给导演/演员阅读。

    格式示例：
        1. 内景. 客厅 - 日

        阳光透过窗帘洒进客厅。

        李明
        （低声）
        这个项目必须在下周之前完成。

        王芳
        （端着咖啡）
        别太拼了，先喝杯咖啡吧。

        李明接过咖啡，点了点头。
    """

    def format(self, screenplay: Screenplay) -> str:
        """
        将剧本对象格式化为标准剧本文本

        Args:
            screenplay: Screenplay 对象

        Returns:
            纯文本剧本字符串
        """
        lines: list[str] = []

        # 标题页
        meta = screenplay.screenplay["metadata"]
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"{meta.get('title', '未命名剧本').center(60)}")
        lines.append("")
        if meta.get("author"):
            lines.append(f"作者: {meta['author']}".center(60))
        lines.append("")
        lines.append("=" * 60)
        lines.append("")

        # 角色表
        characters = screenplay.screenplay.get("characters", [])
        if characters:
            lines.append("【角色表】")
            lines.append("")
            for char in characters:
                imp = {"main": "主角", "supporting": "配角", "minor": "龙套"}.get(
                    char.get("importance", ""), ""
                )
                desc = self._clean_description(char.get("description", ""))
                info = f"  {char['name']}"
                if imp:
                    info += f" [{imp}]"
                if desc:
                    info += f" — {desc}"
                lines.append(info)
            lines.append("")
            lines.append("-" * 60)
            lines.append("")

        # 幕和场景
        scene_global = 1
        for act in screenplay.screenplay.get("acts", []):
            act_num = act.get("act_number", 0)
            act_title = act.get("title", f"第 {act_num} 幕")
            lines.append("")
            lines.append(f"{'=' * 20}  {act_title}  {'=' * 20}")
            lines.append("")

            for scene in act.get("scenes", []):
                # 场景标题行
                heading = scene.get("heading", "")
                if not heading:
                    loc = scene.get("location", "未知地点")
                    time = scene.get("time", "日")
                    int_ext = scene.get("int_ext", "内景")
                    heading = f"{int_ext}. {loc} - {time}"
                lines.append(f"{scene_global}. {heading}")
                lines.append("")

                # 场景描述
                desc = scene.get("description", "")
                if desc:
                    lines.append(desc)
                    lines.append("")

                # 场景元素
                for elem in scene.get("elements", []):
                    etype = elem.get("type", "action")
                    content = elem.get("content", "").strip()
                    if not content:
                        continue

                    if etype == "action":
                        lines.append(content)
                        lines.append("")

                    elif etype == "dialogue":
                        char = elem.get("character", "未知角色")
                        paren = elem.get("parenthetical", "")
                        # 角色名保持原样（中文无大小写，英文大写）
                        lines.append(char)
                        if paren:
                            lines.append(f"（{paren}）")
                        lines.append(content)
                        lines.append("")

                    elif etype == "transition":
                        lines.append(content)
                        lines.append("")

                    elif etype == "sound":
                        lines.append(f"【音效】{content}")
                        lines.append("")

                    elif etype == "note":
                        lines.append(f"【注】{content}")
                        lines.append("")

                scene_global += 1
                lines.append("")

        # 结尾
        lines.append("=" * 60)
        lines.append("")
        lines.append("【完】")
        lines.append("")

        return "\n".join(lines)

    def _clean_description(self, desc: str) -> str:
        """清理角色描述，过滤掉可能是错误提取的小说原文片段"""
        if not desc:
            return ""
        desc = desc.strip()
        # 如果描述包含引号或过长，可能是小说原文而非描述
        # 使用 Unicode 转义确保跨编码兼容
        # 使用 Unicode 码点检测，避免编码问题
        quote_ords = {0x22, 0x201c, 0x201d, 0x300c, 0x300d, 0x300e, 0x300f}
        has_quote = any(ord(c) in quote_ords for c in desc)
        if len(desc) > 30 and has_quote:
            return ""
        # 截断过长的描述
        if len(desc) > 50:
            desc = desc[:50] + "..."
        return desc
