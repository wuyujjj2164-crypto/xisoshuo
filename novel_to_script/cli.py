"""
命令行接口

提供用户友好的命令行工具，支持小说转剧本的完整流程。
"""

import argparse
import os
import sys
from pathlib import Path

import yaml

from .analyzer import NovelAnalyzer
from .converter import ScriptConverter
from .formatter import YAMLFormatter
from .local_converter import LocalConverter
from .parser import NovelParser


def setup_parser() -> argparse.ArgumentParser:
    """配置命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="novel-to-script",
        description="AI 小说转剧本工具 - 将小说文本转换为结构化剧本（YAML 格式）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s input.txt -o output.yaml
  %(prog)s novel.txt --title "我的小说" --author "张三" -o script.yaml
  %(prog)s novel.txt --config config.yaml -o script.yaml
  %(prog)s novel.txt --analyze-only
        """,
    )

    parser.add_argument(
        "input",
        help="输入小说文件路径（.txt 格式）",
    )

    parser.add_argument(
        "-o", "--output",
        default="screenplay.yaml",
        help="输出剧本文件路径（默认: screenplay.yaml）",
    )

    parser.add_argument(
        "--title",
        default="",
        help="小说标题",
    )

    parser.add_argument(
        "--author",
        default="",
        help="作者名称",
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径（默认: config.yaml）",
    )

    parser.add_argument(
        "--api-key",
        default="",
        help="Anthropic API 密钥（默认从环境变量 ANTHROPIC_API_KEY 读取）",
    )

    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="使用的 AI 模型（默认: claude-sonnet-4-6）",
    )

    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="仅分析小说结构，不调用 AI 转换",
    )

    parser.add_argument(
        "--local",
        action="store_true",
        help="使用本地规则转换（无需 API 密钥）",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    return parser


def _deep_merge(base: dict, override: dict) -> dict:
    """递归深度合并两个字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    default_config = {
        "anthropic": {
            "api_key": "",
            "model": "claude-sonnet-4-6",
            "max_tokens": 4096,
            "temperature": 0.3,
        },
        "conversion": {
            "chapters_per_batch": 3,
            "scenes_per_act": 5,
            "min_scene_length": 100,
        },
        "output": {
            "format": "yaml",
            "indent": 2,
            "default_width": 80,
        },
    }

    if not os.path.exists(config_path):
        return default_config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f)

        # 递归深度合并配置
        if isinstance(user_config, dict):
            return _deep_merge(default_config, user_config)

        return default_config
    except Exception as e:
        print(f"警告：无法加载配置文件 '{config_path}': {e}")
        return default_config


def main() -> int:
    """主入口函数"""
    parser = setup_parser()
    args = parser.parse_args()

    # 检查输入文件
    if not os.path.exists(args.input):
        print(f"错误：找不到输入文件 '{args.input}'")
        return 1

    # 加载配置
    config = load_config(args.config)
    verbose = args.verbose

    # 读取小说文本
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            novel_text = f.read()
    except Exception as e:
        print(f"错误：无法读取文件 '{args.input}': {e}")
        return 1

    print(f"[BOOK] 正在处理: {args.input}")
    print(f"   文件大小: {len(novel_text)} 字符")

    # 步骤 1: 解析小说
    print("\n[1/4] 解析小说结构...")
    novel_parser = NovelParser()
    try:
        novel = novel_parser.parse(novel_text, title=args.title, author=args.author)
    except ValueError as e:
        print(f"错误：{e}")
        return 1

    print(novel_parser.get_chapter_summary(novel))

    if len(novel.chapters) < 3:
        print(f"\n[WARNING] 仅检测到 {len(novel.chapters)} 个章节，建议提供 3 章以上的小说")

    # 步骤 2: 分析小说
    print("\n[2/4] 分析角色和场景...")
    analyzer = NovelAnalyzer()
    analysis = analyzer.analyze(novel)

    print(f"   识别角色: {len(analysis['characters'])} 个")
    for char in analysis["characters"][:5]:
        print(f"   - {char.name} ({char.importance.value})")

    print(f"   识别地点: {len(analysis['locations'])} 个")
    print(f"   时间线索: {', '.join(analysis['timeline'][:5])}")

    # 仅分析模式
    if args.analyze_only:
        print("\n[OK] 分析完成（--analyze-only 模式，未进行转换）")
        return 0

    # 步骤 3: 转换
    if args.local:
        print("\n[3/4] 本地规则转换...")
        print("   (使用基于规则的本地转换，无需 API)")
        try:
            converter = LocalConverter()
            screenplay = converter.convert(
                chapters=novel.chapters,
                characters=analysis["characters"],
                title=args.title or novel.title,
                author=args.author or novel.author,
            )
        except Exception as e:
            print(f"\n[ERROR] 转换失败: {e}")
            return 1
    else:
        print("\n[3/4] AI 转换剧本...")

        api_key = args.api_key or config["anthropic"]["api_key"] or os.environ.get("ANTHROPIC_API_KEY")

        if not api_key:
            print("\n[ERROR] 未设置 API 密钥")
            print("   请通过以下方式之一设置：")
            print("   1. 环境变量: export ANTHROPIC_API_KEY='your-key'")
            print("   2. 命令行参数: --api-key 'your-key'")
            print("   3. 配置文件: config.yaml")
            print("   或使用 --local 参数进行本地规则转换")
            return 1

        try:
            converter = ScriptConverter(
                api_key=api_key,
                model=args.model or config["anthropic"]["model"],
                max_tokens=config["anthropic"]["max_tokens"],
                temperature=config["anthropic"]["temperature"],
                chapters_per_batch=config["conversion"]["chapters_per_batch"],
            )

            screenplay = converter.convert(
                chapters=novel.chapters,
                characters=analysis["characters"],
                title=args.title or novel.title,
                author=args.author or novel.author,
            )

        except Exception as e:
            print(f"\n[ERROR] 转换失败: {e}")
            return 1

    # 步骤 4: 输出 YAML
    print("\n[4/4] 生成 YAML 文件...")
    formatter = YAMLFormatter(indent=config["output"]["indent"])

    try:
        formatter.save(screenplay, args.output)
    except Exception as e:
        print(f"\n[ERROR] 保存失败: {e}")
        return 1

    # 验证输出
    with open(args.output, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    valid, message = formatter.validate(yaml_content)

    print(f"\n{'='*50}")
    print(f"[DONE] 转换完成！")
    print(f"   输出文件: {args.output}")
    print(f"   总幕数: {len(screenplay.screenplay['acts'])}")
    print(f"   总场景数: {sum(len(a['scenes']) for a in screenplay.screenplay['acts'])}")
    print(f"   角色数: {len(screenplay.screenplay['characters'])}")
    print(f"   YAML 验证: {'通过' if valid else '失败'} ({message})")
    print(f"{'='*50}")

    return 0


def run() -> None:
    """入口点"""
    sys.exit(main())


if __name__ == "__main__":
    run()
