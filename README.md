# AI 小说转剧本工具

将小说文本自动转换为结构化剧本（YAML 格式），帮助小说作者快速获得可编辑的剧本初稿。

> 🎬 **项目演示视频**：[百度网盘链接](https://pan.baidu.com/s/15fBwh2B8IXGR_tHdfIZgzA)（提取码：`kxde`）

## 功能特性

- **章节自动解析**：支持多种章节格式（第一章/Chapter 1/第1回等）
- **角色智能提取**：基于对话模式识别角色，分析出场频率和重要性
- **场景自动分割**：识别地点变化和时间跳跃，自动划分场景边界
- **双模式转换**：
  - **AI 模式**：调用 Claude API 进行高质量的智能转换
  - **本地模式**：基于规则的快速转换，无需 API 密钥
- **YAML 结构化输出**：符合剧本行业规范的层次化格式
- **Schema 验证**：内置 YAML 格式校验，确保输出质量
- **Web 可视化界面**：基于 Flask 的网页版操作界面，支持拖拽上传和实时预览

## 安装

### 环境要求

- Python 3.10+
- pip

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥（AI 模式需要）

```bash
# Linux/macOS
export ANTHROPIC_API_KEY="your-api-key"

# Windows PowerShell
$env:ANTHROPIC_API_KEY="your-api-key"
```

或在 `config.yaml` 中配置：

```yaml
anthropic:
  api_key: "your-api-key"
```

## 使用方法

### 基本用法

```bash
# 本地模式（无需 API 密钥）
python main.py novel.txt --local -o screenplay.yaml

# AI 模式（需要 API 密钥）
python main.py novel.txt -o screenplay.yaml

# 指定标题和作者
python main.py novel.txt --title "小说标题" --author "作者名" -o output.yaml
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input` | 输入小说文件路径 | 必填 |
| `-o, --output` | 输出剧本文件路径 | `screenplay.yaml` |
| `--title` | 小说标题 | 自动检测 |
| `--author` | 作者名称 | 自动检测 |
| `--local` | 使用本地规则转换 | `false` |
| `--analyze-only` | 仅分析小说结构 | `false` |
| `--ai-analyze` | 使用 AI 分析角色和场景（更准确，需 API） | `false` |
| `--config` | 配置文件路径 | `config.yaml` |
| `--api-key` | Anthropic API 密钥 | 环境变量 |
| `--model` | AI 模型名称 | `claude-sonnet-4-6` |
| `-v, --verbose` | 显示详细日志 | `false` |

### AI 智能分析模式

```bash
# 使用 AI 分析小说结构（比本地规则更准确）
python main.py novel.txt --ai-analyze --analyze-only

# AI 分析 + AI 转换（全流程 AI）
python main.py novel.txt --ai-analyze -o screenplay.yaml
```

AI 分析优势：
- **角色识别更准确**：不受 "XX说道" 格式限制，能识别各种对话模式
- **地点提取更智能**：能识别隐晦的地点描述，过滤噪声
- **支持多种小说风格**：现代文、古文、网文等不同写作风格

### 仅分析模式

```bash
python main.py novel.txt --analyze-only
```

输出小说结构分析，包括章节数、角色列表、地点识别等，不进行转换。

### Web 可视化界面

```bash
# 启动 Web 服务
python web_app.py

# 在浏览器中打开 http://127.0.0.1:5000
```

Web 界面功能：
- 拖拽上传小说文件
- 实时分析小说结构（章节、角色、地点）
- 一键转换为 YAML 剧本
- 在线预览转换结果
- 下载生成的剧本文件

## 项目结构

```
novel-to-script/
├── novel_to_script/        # 核心包
│   ├── __init__.py
│   ├── models.py          # 数据模型（YAML Schema）
│   ├── parser.py          # 小说文本解析器
│   ├── analyzer.py        # 场景和角色分析器
│   ├── converter.py       # AI 转换引擎（Claude API）
│   ├── local_converter.py # 本地规则转换器
│   ├── formatter.py       # YAML 格式化输出
│   └── cli.py             # 命令行接口
├── examples/              # 示例文件
│   ├── sample_novel.txt   # 示例小说（5章）
│   └── sample_output.yaml # 示例输出
├── tests/                 # 测试
│   ├── test_parser.py
│   └── test_analyzer.py
├── docs/                  # 文档
│   └── schema_design.md   # Schema 设计文档
├── templates/             # Web 界面模板
│   └── index.html
├── web_app.py             # Web 服务入口
├── requirements.txt       # 依赖
├── config.yaml           # 配置文件
├── main.py               # CLI 入口脚本
└── README.md             # 本文件
```

## 架构说明

```
输入小说文本
    |
    v
[Parser]  章节分割、文本预处理
    |
    v
[Analyzer] 角色提取、地点识别、对话分析
    |
    +---> --analyze-only (输出分析结果)
    |
    v
[Converter] 小说话转剧本
  - AI 模式：调用 Claude API
  - 本地模式：基于规则转换
    |
    v
[Formatter] YAML 序列化、格式校验
    |
    v
输出 screenplay.yaml
```

## 测试

```bash
# 运行所有测试
python -m unittest discover tests/ -v

# 运行单个测试文件
python tests/test_parser.py
python tests/test_analyzer.py
```

## YAML 输出格式

输出的 YAML 文件遵循定义的剧本 Schema，包含以下结构：

```yaml
screenplay:
  version: "1.0.0"
  metadata:
    title: 剧本标题
    author: 作者
    total_scenes: 总场景数
    total_acts: 总幕数
  characters:
    - id: char_001
      name: 角色名
      importance: main
  acts:
    - act_number: 1
      title: 第一幕
      scenes:
        - scene_number: 1
          heading: "内景. 客厅 - 日"
          elements:
            - type: action
              content: "动作描述"
            - type: dialogue
              character: "角色A"
              content: "对白内容"
```

详细的 Schema 定义和设计原因请参见 [docs/schema_design.md](docs/schema_design.md)。

## 配置说明

`config.yaml` 支持以下配置项：

```yaml
anthropic:
  api_key: ""              # API 密钥
  model: "claude-sonnet-4-6"  # AI 模型
  max_tokens: 4096         # 最大输出 token
  temperature: 0.3         # 创造性程度

openai:
  api_key: ""              # OpenAI 兼容 API 密钥
  base_url: ""             # API 基础地址（DeepSeek/通义千问等）
  model: "gpt-4o"          # 模型名称
  max_tokens: 4096
  temperature: 0.3

ai_analyzer:
  enabled: false           # 是否默认启用 AI 分析
  provider: "anthropic"    # 分析器使用的 API：anthropic / openai

conversion:
  chapters_per_batch: 3    # 每批处理的章节数
  scenes_per_act: 5        # 每幕建议场次数
  min_scene_length: 100    # 最小场景字数

output:
  format: "yaml"           # 输出格式
  indent: 2                # YAML 缩进
  default_width: 80        # 行宽限制
```

## 注意事项

1. **输入格式**：建议输入 `.txt` 格式的小说文本，编码为 UTF-8
2. **章节要求**：建议提供 3 个章节以上的内容，以获得更好的转换效果
3. **AI 模式**：需要有效的 Anthropic API 密钥和足够的 API 额度
4. **本地模式**：作为演示和快速原型使用，转换质量低于 AI 模式
5. **输出编辑**：YAML 文件可直接编辑，修改后格式校验仍会生效

## License

MIT License

---

## 开发日志与 PR 记录

本项目遵循 **"每个 PR 只做一件事"** 的开发规范，保持持续、细粒度的提交记录。

### 开发周期概览

| 指标 | 数值 |
|------|------|
| 总 PR 数 | 10 个 |
| 总 Commit 数 | 21 个 |
| 测试用例数 | 13 个单元测试 |
| 代码总行数 | ~6,900 行 |

### PR 列表

| PR | 标题 | 类型 | 文件数 | 测试方式 |
|---|------|------|--------|---------|
| #01 | [feat] 定义剧本YAML Schema数据模型 | 功能 | 3 | 模型导入验证 |
| #02 | [feat] 实现小说文本解析器（NovelParser） | 功能 | 2 | `python tests/test_parser.py` |
| #03 | [feat] 实现小说内容分析器（NovelAnalyzer） | 功能 | 2 | `python tests/test_analyzer.py` |
| #04 | [feat] 实现YAML格式化输出器（YAMLFormatter） | 功能 | 1 | 集成测试 |
| #05 | [feat] 实现本地规则剧本转换器（LocalConverter） | 功能 | 1 | `python main.py --local` |
| #06 | [feat] 实现AI剧本转换引擎（ScriptConverter） | 功能 | 1 | API调用测试 |
| #07 | [feat] 实现CLI命令行工具与项目配置 | 功能 | 4 | `python main.py --help` |
| #08 | [feat] 添加Web可视化操作界面 | 功能 | 2 | `python web_app.py` |
| #09 | [docs] 添加项目文档、示例小说与.gitignore | 文档 | 3 | 阅读验证 |
| #10 | [fix] 代码审查修复与项目优化 | 修复 | 1 | 安全+功能测试 |

### Commit 规范

```
<type>: <subject>

- 改动点1
- 改动点2

测试方式：xxx
```

| Type | 含义 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug修复 |
| `docs` | 文档 |
| `test` | 测试 |
| `refactor` | 重构 |

### 开发工作流

```
feature/pr-XX-功能名称
    → 开发测试 → commit → PR → Review → Merge main → 验证
```

### 质量保证

- ✅ 每个 PR 合并前通过单元测试
- ✅ 每个 PR 只做一件事，小粒度提交
- ✅ 主分支始终保持可运行状态
- ✅ Commit message 清晰描述改动和测试方式

