# 剧本 YAML Schema 设计文档

## 1. 概述

本文档定义了 AI 小说转剧本工具输出的 YAML Schema，说明每个字段的含义、数据类型以及设计原因。

Schema 版本：1.0.0

---

## 2. 设计目标与原则

### 2.1 设计目标

- **机器可读**：便于程序解析、校验和进一步处理
- **人类可编辑**：YAML 格式直观，作者可以直接修改
- **行业兼容**：参考 Final Draft、Celtx 等标准剧本格式的核心概念
- **可扩展**：支持未来添加新的剧本元素类型

### 2.2 设计原则

| 原则 | 说明 |
|------|------|
| 层次清晰 | act → scene → element 三级结构，与创作思维一致 |
| 类型明确 | 每个元素有明确的类型标签，便于渲染和统计 |
| 元数据完整 | 保留来源信息，便于版本管理和追溯 |
| 角色集中管理 | 角色信息统一维护，避免重复和冲突 |

---

## 3. Schema 结构

### 3.1 顶层结构

```yaml
screenplay:
  version: string      # Schema 版本号
  metadata: Metadata   # 剧本元数据
  characters: [Character]  # 角色列表
  acts: [Act]          # 幕列表
```

#### 设计原因：使用 `screenplay` 根节点

将根节点命名为 `screenplay` 而非直接展开内容，有以下考虑：

1. **语义明确**：明确标识文件内容为剧本，而非普通小说或文章
2. **便于扩展**：未来可添加 `novel`（原著）、`notes`（创作笔记）等兄弟节点
3. **多文件合并**：便于将多个剧本文件合并到一个 YAML 文档中

---

### 3.2 元数据 (Metadata)

```yaml
metadata:
  title: string           # 剧本标题
  source_title: string    # 原小说标题
  author: string          # 作者
  genre: string           # 类型/题材
  total_scenes: int       # 总场次数（自动生成）
  total_acts: int         # 总幕数（自动生成）
  total_characters: int   # 角色总数（自动生成）
  generated_at: string    # 生成时间（ISO 8601）
  version: string         # Schema 版本
```

#### 设计原因：为什么单独设置 `source_title` 和 `title`

小说改编为剧本时，两者常有差异：

- **原小说标题**：保留版权信息和溯源依据
- **剧本标题**：改编后可能有不同的命名（如加"电影版""剧版"后缀）

`total_scenes`、`total_acts`、`total_characters` 为自动生成字段，便于快速了解剧本规模。

---

### 3.3 角色 (Character)

```yaml
characters:
  - id: "char_001"                # 唯一标识符
    name: "张三"                   # 角色名称
    aliases: ["小张", "阿三"]      # 别名/绰号
    description: "年轻记者..."      # 角色描述
    traits: ["好奇", "勇敢"]       # 性格特征
    age: "28岁"                    # 年龄
    gender: "男"                   # 性别
    importance: "main"             # 重要性级别
    notes: ""                      # 备注
```

#### 设计原因：角色集中定义

将角色信息从场景中抽离，独立成表，有以下优势：

1. **一致性检查**：确保同一角色在不同场景中名称统一
2. **快速统计**：便于统计角色出场次数、戏份分布
3. **便于修改**：修改角色名称只需改一处
4. **选角参考**：演员/导演可快速了解角色基本信息

#### 设计原因：`importance` 枚举值

```yaml
importance: main | supporting | minor
```

- **main（主角）**：故事核心，出场率 > 15%
- **supporting（配角）**：推动情节，出场率 3%-15%
- **minor（龙套）**：功能性角色，出场率 < 3%

分级标准便于：
- 评估演员的戏份和片酬
- 规划拍摄日程（主角优先）
- 剧本朗读会的角色分配

---

### 3.4 幕 (Act)

```yaml
acts:
  - act_number: 1
    title: "初到雾隐"
    description: "李明来到雾隐镇，发现异常..."
    scenes: [Scene]
    scene_count: 5
```

#### 设计原因：保留 "幕" 结构

传统剧本常采用三幕式或五幕式结构。保留幕的概念：

1. **结构清晰**：幕是故事的大段落，便于把握整体节奏
2. **便于讨论**："第三幕的高潮戏" 比 "第 47 场" 更直观
3. **兼容标准**：与影视行业的分幕习惯一致

`scene_count` 为自动计算字段，便于快速了解每幕的规模。

---

### 3.5 场景 (Scene)

```yaml
scenes:
  - scene_number: 1          # 全局场次数
    act_scene_number: 1      # 幕内场次数
    heading: "内景. 客栈大厅 - 日"
    location: "客栈大厅"      # 地点
    time: "日"                # 时间
    int_ext: "内景"           # 内景/外景
    description: "李明初到客栈..."
    mood: "神秘"              # 氛围
    characters_present: ["李明", "老板"]
    estimated_duration: 120   # 预估时长（秒）
    elements: [SceneElement]
```

#### 设计原因：场景标题标准化

`heading` 字段采用标准剧本格式：

```
内景/外景. 地点 - 时间
```

例如：`内景. 客厅 - 日`

这种格式源于好莱坞标准剧本规范：
- **INT/EXT**（内景/外景）：直接影响拍摄场地选择和灯光方案
- **地点**：精确的场地信息，便于制片部门勘景
- **时间**：影响光线、氛围和排期

同时将这些信息拆分为独立字段（`location`、`time`、`int_ext`），便于：
- 统计同一地点的所有场次（拍摄计划优化）
- 按时间排序检查时间线连续性
- 筛选内景/外景分别安排拍摄

#### 设计原因：`scene_number` 与 `act_scene_number` 双编号

- `scene_number`（全局编号）：贯穿全剧的唯一标识，便于全局引用
- `act_scene_number`（幕内编号）：便于在单幕范围内讨论

双编号系统兼顾了全局管理和局部讨论的需求。

---

### 3.6 场景元素 (SceneElement)

```yaml
elements:
  - type: "action"
    content: "李明推开门，环顾四周。"

  - type: "dialogue"
    character: "李明"
    content: "这里有人吗？"
    parenthetical: "低声"

  - type: "transition"
    content: "切至："

  - type: "sound"
    content: "远处传来钟声。"

  - type: "note"
    content: "此处可增加音效渲染紧张感。"
```

#### 设计原因：为什么将内容拆分为多种元素类型

小说文本是连续的叙述，而剧本需要区分不同类型的视觉/听觉信息。将内容拆分为元素类型：

| 类型 | 用途 | 设计原因 |
|------|------|---------|
| **action** | 动作描述、场景描写 | 对应小说的叙述部分，转化为可视化动作 |
| **dialogue** | 角色对白 | 剧本的核心，需要标注说话人 |
| **parenthetical** | 表演指示 | 附属于对白，说明语气、动作（括号内） |
| **transition** | 转场提示 | 切至/叠化/淡入淡出，控制叙事节奏 |
| **sound** | 音效/音乐 | 听觉元素，影响后期制作 |
| **note** | 备注/批注 | 编剧给导演/演员的提示，不用于拍摄 |

这种拆分使剧本：
1. **渲染友好**：便于生成 PDF/网页预览时应用不同的排版样式
2. **统计精确**：可统计对白量、动作量，评估剧本节奏
3. **后期支持**：音效元素可直接交给声音设计部门

#### 设计原因：dialogue 类型强制要求 `character` 字段

对白必须明确说话人，这是剧本与小说最核心的区别。强制约束避免遗漏说话人信息。

---

## 4. 类型定义

### 4.1 枚举类型

#### ElementType（元素类型）

```yaml
action | dialogue | parenthetical | transition | sound | note
```

#### CharacterImportance（角色重要性）

```yaml
main | supporting | minor
```

#### IntExt（内景/外景）

```yaml
内景 | 外景 | 内外景
```

#### TimeOfDay（时间段）

```yaml
黎明 | 晨 | 日 | 正午 | 下午 | 黄昏 | 晚 | 夜 | 深夜 |
连续 | 同时 | 稍后 | 片刻后
```

`连续` 和 `同时` 是特殊时间标记：
- **连续**：紧接上一场景，常用于同一地点的连续性动作
- **同时**：与另一场景并行发生，用于交叉剪辑

---

## 5. 完整示例

```yaml
screenplay:
  version: "1.0.0"
  metadata:
    title: "雾隐镇"
    source_title: "雾隐镇"
    author: "示例作者"
    genre: "悬疑"
    total_scenes: 3
    total_acts: 1
    total_characters: 2
    generated_at: "2026-06-05T12:00:00"
    version: "1.0.0"

  characters:
    - id: "char_001"
      name: "李明"
      aliases: []
      description: "年轻记者"
      traits: ["好奇", "执着"]
      age: "28岁"
      gender: "男"
      importance: "main"
      notes: ""

    - id: "char_002"
      name: "老板"
      aliases: []
      description: "客栈老板"
      traits: ["神秘", "冷漠"]
      age: "50岁"
      gender: "男"
      importance: "supporting"
      notes: ""

  acts:
    - act_number: 1
      title: "初到雾隐"
      description: "李明来到雾隐镇，发现异常"
      scenes:
        - scene_number: 1
          act_scene_number: 1
          heading: "外景. 雾隐镇口 - 晨"
          location: "雾隐镇口"
          time: "晨"
          int_ext: "外景"
          description: "李明初到雾隐镇"
          mood: "神秘"
          characters_present: ["李明"]
          elements:
            - type: "action"
              content: "清晨的雾气笼罩着小镇。李明拖着行李箱站在镇口。"
            - type: "action"
              content: "一位老者抽着旱烟，眼神锐利。"
            - type: "dialogue"
              character: "老者"
              content: "雾隐镇不欢迎外来人。"
            - type: "dialogue"
              character: "李明"
              content: "为什么？"
              parenthetical: "不解地"
            - type: "transition"
              content: "切至："

        - scene_number: 2
          act_scene_number: 2
          heading: "内景. 客栈大厅 - 日"
          location: "客栈大厅"
          time: "日"
          int_ext: "内景"
          description: "李明入住客栈"
          mood: "压抑"
          characters_present: ["李明", "老板"]
          elements:
            - type: "action"
              content: "李明推开门，陈旧的气息扑面而来。"
            - type: "dialogue"
              character: "老板"
              content: "住店？"
            - type: "dialogue"
              character: "李明"
              content: "一晚。"
            - type: "note"
              content: "老板态度冷淡，暗示镇上有秘密。"
```

---

## 6. 与标准剧本格式的映射

本 Schema 参考以下行业标准：

| Schema 字段 | 对应标准剧本元素 |
|------------|-----------------|
| `heading` | 场景标题（Slug Line） |
| `type: action` | 动作段落（Action Line） |
| `type: dialogue` + `character` | 对白（Dialogue） |
| `type: parenthetical` | 括号说明（Parenthetical） |
| `type: transition` | 转场（Transition） |
| `characters` 列表 | 角色表（Cast List） |

---

## 7. 扩展建议

未来版本可考虑扩展：

- **镜头类型**：添加 `type: shot`（特写/全景/跟拍等）
- **服装道具**：在角色或场景中标注 costume/prop 信息
- **情绪曲线**：为每幕添加情感强度数值
- **拍摄备注**：添加 `production_notes` 字段记录勘景信息

---

## 8. 变更日志

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| 1.0.0 | 2026-06-05 | 初始版本，包含基本剧本元素类型 |
