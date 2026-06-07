"""
本地剧本转换器（无需 API）

基于规则的小说到剧本转换，核心能力是：
1. 叙述改写成可拍摄的动作（不是直接复制）
2. 对话提取并正确识别说话人
3. 场景按戏剧节奏分割（不是按段落）
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
    核心改进：叙述→动作的语义改写，不是简单复制。
    """

    # ===== 场景分割相关 =====
    TRANSITION_WORDS = ["与此同时", "另一边", "几天后", "数日后", "第二天", "次日"]
    LOCATION_KEYWORDS = [
        "房间", "屋子", "客厅", "卧室", "厨房", "书房", "办公室",
        "街道", "路上", "学校", "医院", "餐厅", "公园", "广场",
        "山上", "河边", "海边", "树下", "门口", "窗前", "阳台",
        "大楼", "实验室", "走廊", "大厅", "庭院", "院子",
    ]
    TIME_KEYWORDS = {
        "清晨": "晨", "早晨": "晨", "早上": "晨",
        "上午": "日", "中午": "正午", "下午": "下午",
        "傍晚": "黄昏", "黄昏": "黄昏",
        "晚上": "晚", "夜间": "夜", "夜里": "夜", "深夜": "深夜",
        "第二天": "日", "次日": "日",
    }
    EXT_KEYWORDS = ["街道", "路上", "村口", "镇口", "山上", "河边", "海边", "树下",
                    "门外", "院子", "庭院", "广场", "公园", "门外"]

    def __init__(self):
        self.scene_counter = 1
        self.act_counter = 1

    # ===== 主入口 =====
    def convert(
        self,
        chapters: list,
        characters: list[Character],
        title: str = "",
        author: str = "",
    ) -> Screenplay:
        self.scene_counter = 1
        self.act_counter = 1

        acts = []
        current_scenes = []

        for chapter in chapters:
            chapter_scenes = self._convert_chapter(chapter, characters)
            current_scenes.extend(chapter_scenes)

            if len(current_scenes) >= 4:
                acts.append(Act(
                    act_number=self.act_counter,
                    title=f"第 {self.act_counter} 幕",
                    scenes=current_scenes,
                ))
                self.act_counter += 1
                current_scenes = []

        if current_scenes:
            acts.append(Act(
                act_number=self.act_counter,
                title=f"第 {self.act_counter} 幕",
                scenes=current_scenes,
            ))

        return Screenplay.create(
            metadata=Metadata(
                title=title or "未命名剧本",
                source_title=title or "",
                author=author or "",
            ),
            characters=characters,
            acts=acts,
        )

    # ===== 章节转场景 =====
    def _convert_chapter(self, chapter, characters: list[Character]) -> list[Scene]:
        """将单章转换为场景列表"""
        char_names = {c.name for c in characters}
        for c in characters:
            if c.aliases:
                char_names.update(c.aliases)

        # 先把整章拆成"叙事块"：每个块要么是 action，要么是 dialogue
        segments = self._segment_chapter(chapter.content, char_names)

        # 按场景分组：地点变化或转场词出现时分割
        scenes = []
        current_elements = []
        current_location = "未知地点"
        current_time = "日"
        current_int_ext = "内景"
        current_chars = set()
        act_scene_num = 1

        for seg in segments:
            # 检测是否需要新场景
            is_new_scene, location, time, int_ext = self._detect_scene_boundary(seg)

            if is_new_scene and current_elements:
                # 合并当前场景中连续的太短 action
                merged_elements = self._merge_actions(current_elements)
                scenes.append(Scene(
                    scene_number=self.scene_counter,
                    act_scene_number=act_scene_num,
                    heading=f"{current_int_ext}. {current_location} - {current_time}",
                    location=current_location,
                    time=current_time,
                    int_ext=current_int_ext,
                    elements=merged_elements,
                    characters_present=list(current_chars),
                ))
                self.scene_counter += 1
                act_scene_num += 1
                current_elements = []
                current_chars = set()
                if location:
                    current_location = location
                if time:
                    current_time = time
                if int_ext:
                    current_int_ext = int_ext

            # 把 segment 转成元素
            if seg["type"] == "dialogue":
                speaker = seg.get("speaker", "未知角色")
                content = seg["content"]
                paren = seg.get("parenthetical")

                if speaker and speaker != "未知角色":
                    current_chars.add(speaker)

                current_elements.append(SceneElement(
                    type=ElementType.DIALOGUE,
                    content=content,
                    character=speaker,
                    parenthetical=paren,
                ))
            else:
                # action：做真正的叙述改写
                rewritten = self._rewrite_narrative(seg["content"])
                if rewritten:
                    current_elements.append(SceneElement(
                        type=ElementType.ACTION,
                        content=rewritten,
                    ))

        # 保存最后一个场景
        if current_elements:
            merged_elements = self._merge_actions(current_elements)
            scenes.append(Scene(
                scene_number=self.scene_counter,
                act_scene_number=act_scene_num,
                heading=f"{current_int_ext}. {current_location} - {current_time}",
                location=current_location,
                time=current_time,
                int_ext=current_int_ext,
                elements=merged_elements,
                characters_present=list(current_chars),
            ))
            self.scene_counter += 1

        return scenes

    # ===== 章节分段：先提取所有对话，其余是叙述 =====
    def _segment_chapter(self, text: str, char_names: set[str]) -> list[dict]:
        """
        将整章文本分割为叙事块。
        每个块是 {type: "action"|"dialogue", content: str, ...}
        """
        _quotes = '""""""'
        dialogue_pattern = re.compile(
            f'[{_quotes}]([^{_quotes}]{{2,300}})[{_quotes}]'
        )

        segments = []
        last_end = 0

        for match in dialogue_pattern.finditer(text):
            # 匹配前的叙述文本
            before = text[last_end:match.start()].strip()
            if before:
                # 按句子/分号分割，避免太长的 action
                for part in self._split_sentences(before):
                    if len(part) > 3:
                        segments.append({"type": "action", "content": part})

            # 对话内容
            dialogue_text = match.group(1).strip()
            speaker, paren = self._find_speaker_full(text, match.start(), match.end(), char_names)

            segments.append({
                "type": "dialogue",
                "content": dialogue_text,
                "speaker": speaker,
                "parenthetical": paren,
            })
            last_end = match.end()

        # 尾部叙述
        after = text[last_end:].strip()
        if after:
            for part in self._split_sentences(after):
                if len(part) > 3:
                    segments.append({"type": "action", "content": part})

        return segments

    # ===== 叙述→动作 核心改写 =====
    def _rewrite_narrative(self, text: str) -> str:
        """
        将小说叙述改写成可拍摄的动作描述。
        这是核心改编能力——不是复制，是改写。
        """
        if not text or len(text) < 5:
            return ""

        text = text.strip()

        # 1. 去掉说话引导句（整句）
        text = re.sub(
            r"[一-龥一-鿿]{2,5}(?:说道|说|问道|问|答道|回答|喊道|叫道|嘟哝|嘀咕)[：:,，。]\s*",
            "",
            text,
        )

        # 2. 去掉心理描写的提示词
        text = re.sub(
            r"(?:他|她|它|他们|她们|它们)(?:想|心想|暗道|暗自|觉得|感到|认为|琢磨|寻思)[：:,，]\s*",
            "",
            text,
        )

        # 3. 去掉旁白式解释
        text = re.sub(
            r"(?:原来|其实|事实上|殊不知|众所周知|众所周知的是|不得不说|不可否认的是)[：:,，]\s*",
            "",
            text,
        )

        # 4. 去掉过多的"了"（过去时痕迹）——但保留语义
        # 把"X了Y"变成"X Y"，但不影响所有"了"
        text = re.sub(r"([动走动跑跳看听想拿放推拉开关坐站躺趴跪爬飞跳])了", r"\1", text)

        # 5. 把"很XX"的心理描写改成动作暗示
        replacements = {
            "很生气": "脸色铁青，拳头紧握",
            "很紧张": "攥紧拳头，指节发白",
            "很高兴": "嘴角上扬，眼里带笑",
            "很难过": "低下头，眼眶泛红",
            "很害怕": "后退一步，浑身颤抖",
            "很惊讶": "瞪大眼睛，嘴巴微张",
            "很疲惫": "瘫坐在椅子上，揉着太阳穴",
            "很兴奋": "双眼发亮，手舞足蹈",
            "很失望": "垂下肩膀，叹了口气",
            "很愤怒": "咬紧牙关，额头青筋暴起",
            "很冷静": "面无表情，目光沉稳",
            "很着急": "来回踱步，不时看表",
            "很疑惑": "皱起眉头，歪着头",
            "很得意": "扬起下巴，嘴角带笑",
            "很沮丧": "耷拉着脑袋，无精打采",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # 6. 去掉冗余的主语重复
        # "李明放下杯子。李明站起身。" → "李明放下杯子，站起身。"
        text = re.sub(
            r"([一-龥]{2,4})[^一-龥]*?[。！？\n]\s*\1",
            r"\1",
            text,
        )

        # 7. 去掉无意义的过渡词
        text = re.sub(r"(?:于是|接着|然后|随后|紧接着|这时候|这时|此刻)[，,]\s*", "", text)

        # 8. 去掉"大概""也许""似乎"等不确定词
        text = re.sub(r"(?:大概|也许|似乎|好像|仿佛|隐约|仿佛|好像|像是|好像)[，,]\s*", "", text)

        # 9. 把"XX地看着"改成更直接的动作
        text = re.sub(r"([一-龥]{2,4})地看着", r"看着", text)

        # 10. 清理多余空白和重复标点
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[。！？]{2,}", "。", text)
        text = re.sub(r"[,，]{2,}", "，", text)

        # 11. 如果清理后只剩虚词或标点，返回空
        stripped = re.sub(r"[\s，。！？、；：\"'\(\)（）\n]", "", text)
        if len(stripped) < 5:
            return ""

        return text.strip()

    # ===== 合并连续 action =====
    def _merge_actions(self, elements: list[SceneElement]) -> list[SceneElement]:
        """合并连续的太短 action，避免碎片化"""
        if not elements:
            return elements

        result = []
        pending_action = ""

        for elem in elements:
            if elem.type == ElementType.ACTION:
                content = elem.content.strip()
                if not content:
                    continue
                if pending_action:
                    pending_action += "\n" + content
                else:
                    pending_action = content
            else:
                if pending_action:
                    result.append(SceneElement(
                        type=ElementType.ACTION,
                        content=pending_action,
                    ))
                    pending_action = ""
                result.append(elem)

        if pending_action:
            result.append(SceneElement(
                type=ElementType.ACTION,
                content=pending_action,
            ))

        return result

    # ===== 说话人识别（增强版） =====
    def _find_speaker_full(
        self, text: str, dialogue_start: int, dialogue_end: int, char_names: set[str]
    ) -> tuple[str | None, str | None]:
        """
        查找说话人和表演指示。
        检查引号前后 80 字范围。
        """
        before = text[max(0, dialogue_start - 80):dialogue_start]
        after = text[dialogue_end:min(len(text), dialogue_end + 80)]

        # 模式1: "XX说道/说/问：'...'"
        speaker_pattern = re.compile(r"([一-龥]{2,4})(?:说道|说|问道|问|答道|回答|喊道|叫道|嘟哝|嘀咕)")
        m = speaker_pattern.search(before)
        if m:
            name = m.group(1)
            if name in char_names:
                return name, None

        # 模式2: "..." XX说道/说
        m = speaker_pattern.search(after)
        if m:
            name = m.group(1)
            if name in char_names:
                return name, None

        # 模式3: 引号前/后直接用角色名（无"说"字）
        for name in sorted(char_names, key=len, reverse=True):
            if name in before[-30:]:
                return name, None
            if name in after[:30:]:
                return name, None

        # 模式4: 表演指示（如 "低声""愤怒地"）
        paren_pattern = re.compile(r"([一-龥]{2,6})(?:低声|大声|冷冷|愤怒|轻声|缓缓|突然|猛地|犹豫)")
        m = paren_pattern.search(before)
        if m:
            name = m.group(1)
            if name in char_names:
                return name, m.group(2) if m.lastindex and m.lastindex >= 2 else None

        return None, None

    # ===== 场景边界检测 =====
    def _detect_scene_boundary(self, text: str) -> tuple[bool, str | None, str | None, str]:
        # 先检查是否是 action 文本（如果不是，是 dialogue，不分割）
        if isinstance(text, dict):
            if text["type"] == "dialogue":
                return False, None, None, "内景"
            text = text["content"]

        # 转场词
        for word in self.TRANSITION_WORDS:
            if text.startswith(word):
                loc = self._extract_location(text)
                tm = self._extract_time(text)
                return True, loc, tm, self._guess_int_ext(text, loc)

        # 地点变化
        loc = self._extract_location(text)
        if loc:
            tm = self._extract_time(text)
            return True, loc, tm, self._guess_int_ext(text, loc)

        return False, None, None, "内景"

    def _guess_int_ext(self, text: str, location: str | None) -> str:
        check = (text[:50] + " " + (location or "")).lower()
        for kw in self.EXT_KEYWORDS:
            if kw in check:
                return "外景"
        return "内景"

    def _extract_location(self, text: str) -> str | None:
        patterns = [
            r"(?:来到|在|走进|走出|站在|坐在|回到|离开|前往)\s*([一-龥一-鿿]{2,8}(?:房间|屋|厅|院|楼|阁|室|馆|店|街|路|山|河|园|场|里|外))",
            r"([一-龥一-鿿]{2,6}(?:房间|屋|厅|院|楼|阁|室|馆|店|街|路|山|河|园|场))(?:里|中|内|外|上|下|前|后)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1)
        for loc in self.LOCATION_KEYWORDS:
            if loc in text[:100]:
                return loc
        return None

    def _extract_time(self, text: str) -> str | None:
        for k, v in self.TIME_KEYWORDS.items():
            if k in text[:100]:
                return v
        return None

    # ===== 句子分割 =====
    def _split_sentences(self, text: str) -> list[str]:
        """按句号/分号/换行分割，保留合理长度"""
        parts = re.split(r"[。；！？\n]", text)
        result = []
        for p in parts:
            p = p.strip()
            if len(p) > 3:
                result.append(p)
        return result
