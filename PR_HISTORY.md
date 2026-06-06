# AI 小说转剧本工具 - 开发日志与 PR 记录

> 本项目严格遵循 "每个 PR 只做一件事" 的开发规范，保持持续、细粒度的提交记录。

---

## 开发周期总览

| 指标 | 数值 |
|------|------|
| 总 PR 数 | 10 个 |
| 总 Commit 数 | 21 个（含 10 个 feature commit + 10 个 merge commit + 1 个 init） |
| 开发文件数 | 17 个代码/文档文件 |
| 测试用例数 | 13 个单元测试 |
| 总代码行数 | ~6,900 行 |

---

## PR 详细记录

### PR-01: 核心数据模型与Schema

- **Branch**: `feature/pr-01-models-schema`
- **Commit**: `abc9638`
- **Merge Commit**: `12b823c`
- **Files Changed**: 3
- **Lines**: +675

**标题**  
feat: 定义剧本YAML Schema数据模型

**功能描述**  
使用 Pydantic v2 定义强类型的剧本数据模型，包含 Metadata、Character、Scene、Act、Screenplay 等核心结构。支持 6 种场景元素类型（action/dialogue/parenthetical/transition/sound/note），角色重要性分级（main/supporting/minor）。同时编写 Schema 设计文档，说明每个字段的设计原因。

**实现思路**  
- 使用 Python `Enum` 定义枚举类型（ElementType、CharacterImportance、IntExt、TimeOfDay）
- 使用 `pydantic.BaseModel` + `Field` 定义数据模型，包含类型约束和验证
- `Screenplay.create()` 工厂方法自动计算统计数据
- `model_dump(mode="json")` 确保枚举序列化为字符串而非 Python 对象

**测试方式**  
```bash
python -c "from novel_to_script.models import *; print('模型导入成功')"
```
验证 Pydantic 模型可以正常实例化和序列化。

---

### PR-02: 小说文本解析器

- **Branch**: `feature/pr-02-parser`
- **Commit**: `1bea8f4`
- **Merge Commit**: `502072a`
- **Files Changed**: 2
- **Lines**: +345

**标题**  
feat: 实现小说文本解析器（NovelParser）

**功能描述**  
将原始小说文本解析为结构化的 Novel 对象，自动分割章节并提取章节标题和内容。支持多种章节格式：第X章、Chapter X、第X回、纯数字标题等。

**实现思路**  
- 使用正则表达式匹配多种章节标题格式（中文数字/阿拉伯数字/英文）
- 尝试所有模式，选择匹配最多的作为最佳分割方案
- 回退策略：当无法识别章节时，按段落均匀分割
- 自动计算字数、过滤过短章节

**测试方式**  
```bash
python tests/test_parser.py
```
覆盖场景：简单章节、中文数字、英文格式、空文本、无章节标记、单章等。

---

### PR-03: 小说内容分析器

- **Branch**: `feature/pr-03-analyzer`
- **Commit**: `6e31fe4`
- **Merge Commit**: `f605240`
- **Files Changed**: 2
- **Lines**: +426

**标题**  
feat: 实现小说内容分析器（NovelAnalyzer）

**功能描述**  
分析小说文本，提取角色列表（名称、出场频率、重要性分级）、场景地点、时间线索、对话样本。为后续转换提供结构化输入。

**实现思路**  
- 基于对话动词模式（说道/说/问/答道等）识别人名
- 过滤常见误识别词（于是/因此/忽然等虚词）
- 按出场频率自动划分角色重要性（main>15%, supporting>3%, minor<3%）
- 通过地点关键词和动词模式提取场景位置

**测试方式**  
```bash
python tests/test_analyzer.py
```
覆盖：角色提取、地点提取、时间线提取、对话采样、章节摘要。

---

### PR-04: YAML格式化输出器

- **Branch**: `feature/pr-04-formatter`
- **Commit**: `56f351a`
- **Merge Commit**: `37cb01e`
- **Files Changed**: 1
- **Lines**: +144

**标题**  
feat: 实现YAML格式化输出器（YAMLFormatter）

**功能描述**  
将 Screenplay 对象序列化为标准 YAML 格式，支持自定义缩进和块风格输出。内置 Schema 验证，检查必需字段、对白必须有角色名等约束。

**实现思路**  
- 使用 `PyYAML` 的 `yaml.dump()` 进行序列化
- `allow_unicode=True` 确保中文正确输出
- `sort_keys=False` 保持字段顺序
- `validate()` 方法检查顶层结构和必需字段

**测试方式**  
```bash
python main.py examples/sample_novel.txt --local -o test.yaml
```
验证生成的 YAML 文件可以通过 Schema 验证。

---

### PR-05: 本地规则剧本转换器

- **Branch**: `feature/pr-05-local-converter`
- **Commit**: `16015ea`
- **Merge Commit**: `366631b`
- **Files Changed**: 1
- **Lines**: +372

**标题**  
feat: 实现本地规则剧本转换器（LocalConverter）

**功能描述**  
无需 API 密钥，基于规则快速将小说转换为剧本。支持中文弯引号对话识别、基于地点关键词的场景分割、简单启发式内外景检测。

**实现思路**  
- 正则匹配弯引号 `"""..."""` 和直引号对话
- 提取说话人（对话前 50 字符内匹配 "XX说道" 模式）
- 场景边界检测：地点变化/时间跳跃/转场词触发新场景
- 内外景启发式：街道/村口/山上等关键词 → 外景

**测试方式**  
```bash
python main.py examples/sample_novel.txt --local -o output.yaml
```
验证 YAML 中 dialogue 类型元素数量 > 0，且包含内景和外景场景。

---

### PR-06: AI剧本转换引擎

- **Branch**: `feature/pr-06-ai-converter`
- **Commit**: `0a089f8`
- **Merge Commit**: `2401a9a`
- **Files Changed**: 1
- **Lines**: +363

**标题**  
feat: 实现AI剧本转换引擎（ScriptConverter）

**功能描述**  
调用 Anthropic Claude API 进行高质量的智能转换。将小说分批处理，避免超出 token 限制。自动解析 API 响应中的 YAML 代码块。

**实现思路**  
- 使用 `anthropic` SDK 调用 Claude API
- 每批处理 3 个章节，控制 prompt 长度
- 精心设计的 prompt 包含转换规则、角色参考、输出格式
- 自动提取 markdown 代码块并解析为 YAML
- `_fix_yaml()` 修复常见缩进问题

**测试方式**  
```bash
export ANTHROPIC_API_KEY="your-key"
python main.py novel.txt -o output.yaml
```

---

### PR-07: CLI命令行工具与配置

- **Branch**: `feature/pr-07-cli`
- **Commit**: `bc43503`
- **Merge Commit**: `d40d7c4`
- **Files Changed**: 4
- **Lines**: +333

**标题**  
feat: 实现CLI命令行工具与项目配置

**功能描述**  
提供完整的 argparse 命令行接口，支持双模式转换（本地/AI）、仅分析模式、配置文件管理。四步流程带进度提示。

**实现思路**  
- `argparse` 构建命令行参数解析
- `yaml.safe_load()` 读取配置文件
- 递归深度合并配置（避免浅合并丢失默认键）
- 支持环境变量、配置文件、命令行参数三种配置来源
- 统一转换器调用接口

**测试方式**  
```bash
python main.py --help
python main.py examples/sample_novel.txt --local --analyze-only
python main.py examples/sample_novel.txt --local -o output.yaml
```

---

### PR-08: Web可视化操作界面

- **Branch**: `feature/pr-08-web-ui`
- **Commit**: `4cd955a`
- **Merge Commit**: `e32ea18`
- **Files Changed**: 2
- **Lines**: +693

**标题**  
feat: 添加Web可视化操作界面

**功能描述**  
基于 Flask 的现代化暗色主题 Web 界面，支持拖拽上传、实时分析预览、一键转换、在线预览 YAML 结果、下载剧本文件。

**实现思路**  
- Flask 提供 `/api/convert`、`/api/analyze`、`/api/download` 三个 API
- 纯 HTML/CSS/JS 前端，无需额外前端依赖
- 拖拽上传 + 点击上传双模式
- UUID 临时文件名 + 路径遍历防护 + atexit 自动清理

**测试方式**  
```bash
python web_app.py
# 浏览器访问 http://127.0.0.1:5000
```

---

### PR-09: 项目文档与示例

- **Branch**: `feature/pr-09-docs-examples`
- **Commit**: `15b9a7b`
- **Merge Commit**: `aef826a`
- **Files Changed**: 3
- **Lines**: +533

**标题**  
docs: 添加项目文档、示例小说与.gitignore

**功能描述**  
编写完整的 README.md（项目介绍、安装指南、使用方法、架构说明），提供示例小说《雾隐镇》（5章悬疑小说），配置 .gitignore 排除不需要的文件。

**实现思路**  
- README 包含：功能特性、安装步骤、使用示例、项目结构、架构说明
- 示例小说经过精心设计，包含对话、场景转换、多角色，适合演示
- .gitignore 覆盖 Python 缓存、虚拟环境、IDE 配置、敏感文件

**测试方式**  
阅读 README.md 确认信息完整，运行示例验证可执行。

---

### PR-10: Bug修复与安全加固

- **Branch**: `feature/pr-10-bugfixes`
- **Commit**: `126d22a`
- **Merge Commit**: `3a84436`
- **Files Changed**: 1 (.gitignore 更新，修复逻辑在之前的 commit 中)
- **Lines**: +10

**标题**  
fix: 代码审查修复与项目优化

**功能描述**  
基于全面代码审查，修复安全漏洞、核心功能缺陷和体验问题。包括路径遍历修复、弯引号支持、对话比例计算修复等。

**实现思路**  
- 路径遍历：验证下载路径前缀，非法路径返回 403
- 弯引号：正则 `r'[\"\"\"\"\"\"](...)[\"\"\"\"\"\"]'` 同时匹配三种引号
- 对话比例：`sum(len(m) for m in matches)` 替代 `len(matches)`
- 配置合并：递归 `_deep_merge()` 替代 `dict.update()`

**测试方式**  
```bash
# 单元测试
python tests/test_parser.py && python tests/test_analyzer.py

# 端到端验证
python main.py examples/sample_novel.txt --local -o test.yaml

# 安全验证
curl "http://127.0.0.1:5000/api/download?file=..\Windows\..."
# 应返回 403
```

---

## Commit 规范

### Commit Message 格式

```
<type>: <subject>

<body>
```

### Type 说明

| Type | 含义 | 使用场景 |
|------|------|---------|
| `feat` | 新功能 | 新增模块、新增接口 |
| `fix` | 修复 | Bug修复、安全问题 |
| `docs` | 文档 | README、设计文档 |
| `test` | 测试 | 新增测试用例 |
| `refactor` | 重构 | 代码结构调整 |
| `init` | 初始化 | 项目创建 |

### Commit 示例

```
feat: 实现小说文本解析器（NovelParser）

- 支持多种章节格式：第X章/Chapter X/第X回
- 自动检测最佳章节分割模式
- 包含8个单元测试用例

测试：python tests/test_parser.py
```

---

## 开发工作流

```
1. 创建功能分支
   git checkout -b feature/pr-XX-功能名称

2. 开发并测试
   （编写代码 → 运行测试 → 修复问题）

3. 提交代码
   git add .
   git commit -m "feat: 功能说明

   - 改动点1
   - 改动点2

   测试方式：xxx"

4. 发起 Pull Request
   （GitHub 上创建 PR，填写标题和描述）

5. Code Review
   （自测通过 → 合并到 main）

6. 合并后验证
   git checkout main
   python tests/...  # 确认主分支可运行
```

---

## 分支策略

| 分支 | 用途 | 保护规则 |
|------|------|---------|
| `main` | 主分支，始终保持可运行 | 需 PR 合并，不能直接 push |
| `feature/pr-XX-*` | 功能开发分支 | 开发完成后删除 |
| `backup-main` | 备份分支 | 保留历史版本 |

---

## 质量保证

- ✅ 每个 PR 合并前必须通过单元测试
- ✅ 每个 PR 只做一件事，小粒度提交
- ✅ 主分支始终保持可运行状态
- ✅ Commit message 清晰描述改动和测试方式
- ✅ 代码审查关注：安全性、可读性、可测试性
