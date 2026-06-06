# Task Plan: AI 小说转剧本工具

## Goal
开发一款 AI 辅助剧本创作工具，将 3+ 章节的小说文本自动转换为结构化剧本（YAML 格式），并编写 YAML Schema 设计文档。

## Current Phase
Phase 2

## Phases

### Phase 1: Requirements & Discovery
- [x] 分析项目需求（小说转剧本、YAML 输出、3+ 章节支持）
- [x] 分析评审标准（完整度 40%、开发质量 40%、演示 20%）
- [x] 了解 PR 提交规范（小 PR、单一功能、可运行代码）
- [x] 确定技术栈（Python + Anthropic SDK + YAML）
- **Status:** complete

### Phase 2: Planning & Structure
- [ ] 设计剧本 YAML Schema（场次、场景、对白、动作、镜头等）
- [ ] 设计项目架构（parser → analyzer → converter → exporter）
- [ ] 创建项目目录结构
- [ ] 编写 Schema 设计文档大纲
- **Status:** in_progress

### Phase 3: Implementation - Core Engine
- [ ] 开发小说文本解析器（章节分割、场景识别）
- [ ] 开发角色提取模块
- [ ] 开发剧本转换引擎（调用 Claude API）
- [ ] 开发 YAML 输出格式化器
- **Status:** pending

### Phase 4: Implementation - CLI Tool
- [ ] 开发命令行接口（argparse）
- [ ] 支持文件输入/输出
- [ ] 添加配置管理（API key、模型选择）
- [ ] 添加错误处理和日志
- **Status:** pending

### Phase 5: Testing & Examples
- [ ] 创建示例小说文本（3+ 章节）
- [ ] 运行端到端测试
- [ ] 验证 YAML Schema 完整性
- [ ] 修复发现的问题
- **Status:** pending

### Phase 6: Documentation
- [ ] 编写 YAML Schema 设计文档
- [ ] 编写项目 README（使用方法、安装）
- [ ] 编写 API 文档和配置说明
- **Status:** pending

## Key Questions
1. YAML Schema 应包含哪些剧本元素？（场次、场景、角色、对白、动作、镜头、音效等）
2. 如何分割小说章节并识别场景边界？
3. 如何保持对话的戏剧性和角色特征？
4. 如何设计可扩展的架构支持不同剧本格式？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 使用 Python 3.10+ | 丰富的 NLP 库、YAML 支持、Anthropic SDK |
| 使用 Anthropic SDK (Claude API) | 强大的中文理解能力和长文本处理能力 |
| 使用 PyYAML 输出 | 标准格式、人类可读、易编辑 |
| 使用 dataclasses 定义模型 | 类型安全、序列化方便、自文档化 |
| 章节检测采用正则+AI混合策略 | 正则快速粗分，AI 精确调整 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
|       | 1       |            |

## Notes
- 评审重点：功能完整度、架构清晰度、代码规范、可运行性
- PR 规范：每个 PR 只做一件事，小粒度提交
- 需要确保主分支始终可运行
