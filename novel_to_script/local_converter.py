"""
本地剧本转换器（无需 API）

基于规则的小说到剧本转换，作为 AI 转换的备选方案。
适用于演示、测试或没有 API 密钥的场景。

转换规则：
1. 将直接引语（"..."）转换为对白
2. 将叙述段落转换为动作描述
3. 基于段落和地点关键词分割场景
"""

import re

from .models import (
    Act,
    Character,
    CharacterImportance,
    ElementType,
    Metadata,
    Scene,
    SceneElement,
    Screenplay,
)


class LocalConverter:
    """
    本地规则转换器

    使用基于规则的方法将小说转换为剧本，无需调用外部 API。
    适合快速原型和演示场景。
    """

    # 地点关键词（用于场景分割）
    LOCATION_KEYWORDS = [
        "房间", "屋子", "客厅", "卧室", "厨房", "书房", "办公室",
        "街道", "路上", "学校", "医院", "餐厅", "公园", "广场",
        "山上", "河边", "海边", "树下", "门口", "窗前", "阳台",
    ]

    # 时间关键词
    TIME_KEYWORDS = {
        "清晨": "晨", "早晨": "晨", "早上": "晨",
        "上午": "日", "中午": "正午", "下午": "下午",
        "傍晚": "黄昏", "黄昏": "黄昏",
        "晚上": "晚", "夜间": "夜", "夜里": "夜", "深夜": "深夜",
        "第二天": "日", "次日": "日",
    }

    # 转场提示词
    TRANSITION_WORDS = ["与此同时", "另一边", "几天后", "数日后", "第二天"]

    # 外景关键词（简单启发式规则）
    EXT_KEYWORDS = [
        "街道", "路上", "村口", "镇口", "山上", "河边", "海边", "树下",
        "门外", "院子", "庭院", "广场", "公园", "门外",
    ]

    def __init__(self):
        self.scene_counter = 1
        self.act_counter = 1

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
        # 重置计数器（支持同一实例多次调用）
        self.scene_counter = 1
        self.act_counter = 1

        acts = []
        current_scenes = []

        for chapter in chapters:
            chapter_scenes = self._convert_chapter(chapter, characters)
            current_scenes.extend(chapter_scenes)

            # 每 3-5 个场景分为一幕
            if len(current_scenes) >= 4:
                act = Act(
                    act_number=self.act_counter,
                    title=f"第 {self.act_counter} 幕",
                    description=f"包含场景 {current_scenes[0].scene_number}-{current_scenes[-1].scene_number}",
                    scenes=current_scenes,
                )
                acts.append(act)
                self.act_counter += 1
                current_scenes = []

        # 处理剩余场景
        if current_scenes:
            act = Act(
                act_number=self.act_counter,
                title=f"第 {self.act_counter} 幕",
                description=f"包含场景 {current_scenes[0].scene_number}-{current_scenes[-1].scene_number}",
                scenes=current_scenes,
            )
            acts.append(act)

        metadata = Metadata(
            title=title or "未命名剧本",
            source_title=title or "",
            author=author or "",
        )

        return Screenplay.create(
            metadata=metadata,
            characters=characters,
            acts=acts,
        )

    def _convert_chapter(self, chapter, characters: list[Character]) -> list[Scene]:
        """将单章转换为场景列表"""
        scenes = []

        # 将章节分割为段落
        paragraphs = [p.strip() for p in chapter.content.split("\n\n") if p.strip()]

        current_elements = []
        current_location = "未知地点"
        current_time = "日"
        current_int_ext = "内景"
        current_chars = set()
        act_scene_num = 1

        for para in paragraphs:
            # 检查是否是场景边界
            is_new_scene, location, time, int_ext = self._detect_scene_boundary(para)

            if is_new_scene and current_elements:
                # 保存当前场景
                scene = Scene(
                    scene_number=self.scene_counter,
                    act_scene_number=act_scene_num,
                    heading=f"{current_int_ext}. {current_location} - {current_time}",
                    location=current_location,
                    time=current_time,
                    int_ext=current_int_ext,
                    description="",
                    mood="",
                    elements=current_elements,
                    characters_present=list(current_chars),
                )
                scenes.append(scene)
                self.scene_counter += 1
                act_scene_num += 1

                # 重置
                current_elements = []
                current_location = location or current_location
                current_time = time or current_time
                current_int_ext = int_ext or current_int_ext
                current_chars = set()

            # 处理段落内容
            elements, chars = self._process_paragraph(para, characters)
            current_elements.extend(elements)
            current_chars.update(chars)

        # 保存最后一个场景
        if current_elements:
            scene = Scene(
                scene_number=self.scene_counter,
                act_scene_number=act_scene_num,
                heading=f"{current_int_ext}. {current_location} - {current_time}",
                location=current_location,
                time=current_time,
                int_ext=current_int_ext,
                description="",
                mood="",
                elements=current_elements,
                characters_present=list(current_chars),
            )
            scenes.append(scene)
            self.scene_counter += 1

        return scenes

    def _detect_scene_boundary(self, text: str) -> tuple[bool, str | None, str | None, str]:
        """
        检测场景边界

        通过地点和时间关键词判断是否需要分割新场景。

        Returns:
            (是否新场景, 地点, 时间, 内景/外景)
        """
        # 检查转场词
        for word in self.TRANSITION_WORDS:
            if text.startswith(word):
                # 尝试提取地点
                location = self._extract_location(text)
                time = self._extract_time(text)
                int_ext = self._guess_int_ext(text, location)
                return True, location, time, int_ext

        # 检查地点变化
        location = self._extract_location(text)
        if location:
            time = self._extract_time(text)
            int_ext = self._guess_int_ext(text, location)
            return True, location, time, int_ext

        return False, None, None, "内景"

    def _guess_int_ext(self, text: str, location: str | None) -> str:
        """
        猜测场景是内景还是外景

        通过地点关键词做简单启发式判断。
        """
        check_text = (text[:50] + " " + (location or "")).lower()
        for ext_kw in self.EXT_KEYWORDS:
            if ext_kw in check_text:
                return "外景"
        return "内景"

    def _extract_location(self, text: str) -> str | None:
        """从文本中提取地点"""
        # 匹配 "来到..."、"在..." 等模式
        patterns = [
            r"(?:来到|在|走进|走出|站在|坐在|回到|离开|前往)\s*([一-龥]{2,8}(?:房间|屋|厅|院|楼|阁|室|馆|店|街|路|山|河|园|场|里|外))",
            r"([一-龥]{2,6}(?:房间|屋|厅|院|楼|阁|室|馆|店|街|路|山|河|园|场))(?:里|中|内|外|上|下|前|后)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        # 直接匹配地点关键词
        for loc in self.LOCATION_KEYWORDS:
            if loc in text[:100]:
                return loc

        return None

    def _extract_time(self, text: str) -> str | None:
        """从文本中提取时间"""
        for keyword, time_val in self.TIME_KEYWORDS.items():
            if keyword in text[:100]:
                return time_val
        return None

    def _process_paragraph(
        self, text: str, characters: list[Character]
    ) -> tuple[list[SceneElement], set[str]]:
        """
        处理段落，提取场景元素

        Args:
            text: 段落文本
            characters: 角色列表

        Returns:
            (场景元素列表, 出场的角色名集合)
        """
        elements = []
        chars_present = set()

        # 构建角色名查找表
        char_names = {c.name for c in characters}
        for c in characters:
            if c.aliases:
                char_names.update(c.aliases)

        # 提取对话（支持中文弯引号 """ """ 和直引号 "")
        dialogue_pattern = re.compile(
            r'[""""""]([^""""""]{3,200})[""""""]'
        )

        last_end = 0
        for match in dialogue_pattern.finditer(text):
            # 匹配前的叙述文本 -> action
            before = text[last_end:match.start()].strip()
            if before and len(before) > 5:
                # 尝试提取动作描述（去除"说"等引导词）
                action_text = self._clean_action_text(before)
                if action_text:
                    elements.append(SceneElement(
                        type=ElementType.ACTION,
                        content=action_text,
                    ))

            # 查找说话人
            speaker = self._find_speaker(text, match.start(), char_names)
            dialogue_text = match.group(1).strip()

            if speaker:
                chars_present.add(speaker)

            # 提取括号内的表演指示
            parenthetical = None
            if "（" in dialogue_text and "）" in dialogue_text:
                p_match = re.search(r'（([^）]+)）', dialogue_text)
                if p_match:
                    parenthetical = p_match.group(1)
                    dialogue_text = dialogue_text.replace(p_match.group(0), "")

            elements.append(SceneElement(
                type=ElementType.DIALOGUE,
                content=dialogue_text,
                character=speaker or "未知角色",
                parenthetical=parenthetical,
            ))

            last_end = match.end()

        # 处理剩余的叙述文本
        after = text[last_end:].strip()
        if after and len(after) > 5:
            action_text = self._clean_action_text(after)
            if action_text:
                elements.append(SceneElement(
                    type=ElementType.ACTION,
                    content=action_text,
                ))

        # 如果没有对话，将整个段落作为动作
        if not elements:
            action_text = self._clean_action_text(text)
            if action_text:
                elements.append(SceneElement(
                    type=ElementType.ACTION,
                    content=action_text,
                ))

        return elements, chars_present

    def _find_speaker(self, text: str, dialogue_pos: int, char_names: set[str]) -> str | None:
        """查找说话人"""
        # 检查对话前的文本
        before = text[max(0, dialogue_pos - 50):dialogue_pos]

        # 匹配 "XX说道"、"XX说" 等模式
        speaker_pattern = re.compile(r"([一-龥]{2,4})(?:说道|说|问道|问|答道|回答|喊道|叫道)")
        match = speaker_pattern.search(before)
        if match:
            name = match.group(1)
            if name in char_names:
                return name

        # 尝试匹配已知角色名
        for name in sorted(char_names, key=len, reverse=True):
            if name in before[-20:]:
                return name

        return None

    def _clean_action_text(self, text: str) -> str:
        """清理动作描述文本"""
        # 去除说话引导词
        text = re.sub(r"[一-龥]{2,4}(?:说道|说|问道|问|答道|回答)[：:\s]*", "", text)
        # 去除多余空白
        text = re.sub(r"\s+", " ", text)
        return text.strip()
