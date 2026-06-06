#!/usr/bin/env python3
"""
AI 小说转剧本工具 - 入口脚本

使用方法:
    python main.py <小说文件> [选项]

示例:
    python main.py examples/sample_novel.txt --local -o output.yaml
    python main.py novel.txt --title "我的小说" --author "张三"
"""

from novel_to_script.cli import run

if __name__ == "__main__":
    run()
