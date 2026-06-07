"""
AI 小说转剧本工具 - Web 界面

基于 Flask 的可视化操作界面，支持文件上传、转换配置和结果预览。
"""

import atexit
import os
import shutil
import uuid

from flask import Flask, jsonify, render_template, request, send_file

from novel_to_script.ai_analyzer import AINovelAnalyzer
from novel_to_script.analyzer import NovelAnalyzer
from novel_to_script.formatter import YAMLFormatter
from novel_to_script.local_converter import LocalConverter
from novel_to_script.parser import NovelParser

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

# 项目临时目录（用于保存生成的剧本文件）
TMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)


def _cleanup_tmp():
    """进程退出时清理临时目录"""
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR, ignore_errors=True)


atexit.register(_cleanup_tmp)


def _is_safe_path(path: str) -> bool:
    """验证路径是否在允许的临时目录内，防止路径遍历"""
    if not path:
        return False
    abs_path = os.path.abspath(path)
    abs_tmp = os.path.abspath(TMP_DIR)
    # 确保路径以 TMP_DIR 开头
    return abs_path.startswith(abs_tmp + os.sep) or abs_path == abs_tmp


def _get_analyzer(ai_mode: bool = False, api_key: str = "", provider: str = ""):
    """
    获取分析器实例
    ai_mode=True 时尝试使用 AI 分析器
    返回 (analyzer, error_message)
    """
    if not ai_mode:
        return NovelAnalyzer(), None

    # 优先使用前端传入的密钥，其次环境变量
    key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("MOONSHOT_API_KEY")
    if not key:
        return NovelAnalyzer(), "未提供 API 密钥，已回退到本地规则分析"

    # 确定 provider
    provider = (provider or "").lower()
    if not provider:
        # 根据密钥前缀判断 provider
        if key.startswith("sk-ant-"):
            provider = "anthropic"
        else:
            # 默认使用 openai 兼容格式（支持 OpenAI / DeepSeek / 通义千问 / Kimi）
            provider = "openai"

    # 模型和 base_url 配置
    model = "claude-sonnet-4-6"
    base_url = None

    if provider == "anthropic":
        model = "claude-sonnet-4-6"
    elif provider == "kimi":
        model = "moonshot-v1-32k"
        base_url = "https://api.kimi.com/coding/v1"
    else:
        # openai 兼容格式，尝试从环境变量读取 base_url
        model = "gpt-4o"
        base_url = os.environ.get("OPENAI_BASE_URL")

    try:
        analyzer = AINovelAnalyzer(
            api_key=key,
            model=model,
            provider=provider,
            base_url=base_url,
        )
        return analyzer, None
    except ImportError as e:
        return NovelAnalyzer(), f"AI 分析依赖未安装: {e}"
    except Exception as e:
        return NovelAnalyzer(), f"AI 分析器初始化失败: {e}"


@app.route("/")
def index():
    """首页"""
    return render_template("index.html")


@app.route("/api/convert", methods=["POST"])
def convert():
    """转换API"""
    if "file" not in request.files:
        return jsonify({"error": "请上传文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    # 读取配置
    title = request.form.get("title", "")
    author = request.form.get("author", "")
    mode = request.form.get("mode", "local")

    try:
        # 读取文件内容
        content = file.read().decode("utf-8")
    except UnicodeDecodeError:
        return jsonify({"error": "文件编码错误，请使用 UTF-8 编码的文本文件"}), 400

    # 步骤1: 解析
    parser = NovelParser()
    try:
        novel = parser.parse(content, title=title, author=author)
    except ValueError as e:
        return jsonify({"error": f"解析失败: {e}"}), 400

    # 步骤2: 分析
    ai_analyze = request.form.get("ai_analyze", "false").lower() == "true"
    api_key = request.form.get("api_key", "")
    provider = request.form.get("provider", "")
    analyzer, ai_error = _get_analyzer(ai_mode=ai_analyze, api_key=api_key, provider=provider)
    analysis = analyzer.analyze(novel)

    # 如果用户要求 AI 分析但失败了，显示警告
    if ai_analyze and ai_error and not isinstance(analyzer, AINovelAnalyzer):
        pass  # 继续用本地规则，但结果中会包含 ai_error

    # 步骤3: 转换
    if mode == "local":
        converter = LocalConverter()
        screenplay = converter.convert(
            chapters=novel.chapters,
            characters=analysis["characters"],
            title=title or novel.title,
            author=author or novel.author,
        )
    else:
        return jsonify({"error": "AI模式需要配置API密钥，当前仅支持本地模式"}), 400

    # 步骤4: 格式化
    formatter = YAMLFormatter()
    yaml_content = formatter.format(screenplay)

    # 保存到项目临时目录（使用 UUID 避免并发冲突）
    temp_filename = f"screenplay_{uuid.uuid4().hex}.yaml"
    temp_path = os.path.join(TMP_DIR, temp_filename)
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    # 统计信息
    stats = {
        "chapters": len(novel.chapters),
        "acts": len(screenplay.screenplay["acts"]),
        "scenes": sum(len(a["scenes"]) for a in screenplay.screenplay["acts"]),
        "characters": len(screenplay.screenplay["characters"]),
        "word_count": novel.total_word_count,
    }

    result = {
        "success": True,
        "yaml": yaml_content,
        "stats": stats,
        "download_url": f"/api/download?file={temp_filename}",
    }

    # 标记 AI 分析状态
    if ai_analyze and isinstance(analyzer, AINovelAnalyzer):
        result["ai_analyzed"] = True
    elif ai_analyze and ai_error:
        result["ai_error"] = ai_error

    return jsonify(result)


@app.route("/api/download")
def download():
    """下载生成的YAML文件"""
    filename = request.args.get("file", "")
    if not filename:
        return jsonify({"error": "缺少文件名参数"}), 400

    # 防止路径遍历：只接受纯文件名，不接受路径分隔符
    if os.sep in filename or "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"error": "非法文件名"}), 403

    path = os.path.join(TMP_DIR, filename)
    if not _is_safe_path(path) or not os.path.exists(path):
        return jsonify({"error": "文件不存在或无权访问"}), 403

    return send_file(path, as_attachment=True, download_name="screenplay.yaml")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """仅分析API"""
    if "file" not in request.files:
        return jsonify({"error": "请上传文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    try:
        content = file.read().decode("utf-8")
    except UnicodeDecodeError:
        return jsonify({"error": "文件编码错误"}), 400

    parser = NovelParser()
    try:
        novel = parser.parse(content)
    except ValueError as e:
        return jsonify({"error": f"解析失败: {e}"}), 400

    ai_mode = request.form.get("ai_analyze", "false").lower() == "true"
    api_key = request.form.get("api_key", "")
    provider = request.form.get("provider", "")
    analyzer, ai_error = _get_analyzer(ai_mode=ai_mode, api_key=api_key, provider=provider)
    analysis = analyzer.analyze(novel)

    result = {
        "success": True,
        "chapters": len(novel.chapters),
        "word_count": novel.total_word_count,
        "characters": [
            {"name": c.name, "importance": c.importance.value}
            for c in analysis["characters"][:10]
        ],
        "locations": [loc["name"] for loc in analysis["locations"][:10]],
        "timeline": analysis["timeline"][:10],
    }

    # 标记是否使用了 AI 分析
    if ai_mode and isinstance(analyzer, AINovelAnalyzer):
        result["ai_analyzed"] = True
    elif ai_mode and ai_error:
        result["ai_error"] = ai_error

    return jsonify(result)


if __name__ == "__main__":
    print("=" * 50)
    print("AI 小说转剧本工具 - Web 界面")
    print("=" * 50)
    print("请在浏览器中打开: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=False)
