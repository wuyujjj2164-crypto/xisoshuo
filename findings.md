# Findings & Decisions

## Requirements
- 将 3+ 章节的小说文本自动转换为结构化剧本（YAML 格式）
- 输出可编辑、可进一步打磨的剧本初稿
- 编写 YAML Schema 设计文档，说明设计原因
- 项目作业要求：代码健壮、架构清晰、可运行演示

## Research Findings
- 剧本标准格式包含：场次号、场景标题（内景/外景+地点+时间）、角色、对白、动作描述、转场提示
- YAML 适合作为中间格式：层次清晰、人类可读、支持注释
- 小说转剧本的核心挑战：叙述转对白、心理描写转动作、场景边界识别
- Anthropic Claude 3.7 Sonnet 适合长文本处理任务

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Python 3.10+ | 原生类型提示、match/case 语法、丰富的生态 |
| PyYAML + ruamel.yaml | PyYAML 用于基本读写，ruamel 用于保留注释和格式 |
| dataclasses + typing | 强类型模型层，自文档化 |
| 分层架构：Parser → Analyzer → Converter → Formatter | 单一职责，便于测试和扩展 |
| 章节分割：正则 + AI 确认 | 正则提取章节边界，AI 验证场景分割点 |
| 使用 Pydantic 做 Schema 验证 | 运行时类型检查，自动生成文档 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
|       |            |

## Resources
- 项目目录：Documents/novel-to-script/
- Anthropic SDK: https://github.com/anthropics/anthropic-sdk-python
- PyYAML: https://pyyaml.org/
- Pydantic: https://docs.pydantic.dev/

## Visual/Browser Findings
- 截图显示评审标准：作品完整度 40% + 开发过程 40% + 演示 20%
- PR 规范：每个 PR 只做一件事，标题清晰，包含功能描述/实现思路/测试方式
