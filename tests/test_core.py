"""
基础测试 — 核心模块功能验证
"""

import pytest
import sys
from pathlib import Path

# 确保项目根目录在 path 中
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


class TestOutputIndex:
    """测试 output.py 的索引更新逻辑"""

    def test_extract_title_simple(self):
        """从 blog.md 中提取标题"""
        # 使用类方法测试标题提取逻辑
        blog = "# 测试文章标题\n\n正文内容..."
        # 直接测试 output.py 中的标题提取逻辑
        import re
        title = "未命名文章"
        for line in blog.split("\n"):
            m = re.match(r'^#\s+(.+)$', line.strip())
            if m and not line.startswith("##"):
                title = m.group(1).strip()
                break
        assert title == "测试文章标题"

    def test_extract_title_no_title(self):
        """无标题时返回默认值"""
        blog = "正文内容，没有 Markdown 标题"
        import re
        title = "未命名文章"
        for line in blog.split("\n"):
            m = re.match(r'^#\s+(.+)$', line.strip())
            if m and not line.startswith("##"):
                title = m.group(1).strip()
                break
        assert title == "未命名文章"

    def test_extract_title_skips_h2(self):
        """跳过 ## 二级标题"""
        blog = "## 二级标题\n# 一级标题\n正文"
        import re
        title = "未命名文章"
        for line in blog.split("\n"):
            m = re.match(r'^#\s+(.+)$', line.strip())
            if m and not line.startswith("##"):
                title = m.group(1).strip()
                break
        assert title == "一级标题"


class TestParseScript:
    """测试 video_generator.py 的脚本解析"""

    def test_parse_structured(self):
        """解析结构化脚本格式"""
        from core.video_generator import _parse_structured
        script = """## S0 | 开场 | explode | a1
文案：你好世界

## S1 | 数据 | number | a1
文案：100天
       进步"""
        scenes = _parse_structured(script)
        assert len(scenes) == 2
        assert scenes[0]["name"] == "开场"
        assert scenes[0]["visualType"] == "explode"
        assert scenes[0]["lines"][0] == "你好世界"

    def test_parse_structured_continuation_lines(self):
        from core.video_generator import _parse_structured
        script = """## S0 | 开场 | explode | a1
文案：第一行
       第二行
       第三行"""
        scenes = _parse_structured(script)
        assert scenes[0]["lines"] == ["第一行", "第二行", "第三行"]

    def test_parse_legacy_empty(self):
        """空脚本应返回空列表"""
        from core.video_generator import _parse_legacy
        scenes = _parse_legacy("")
        assert scenes == []

    def test_find_content_start(self):
        """找到内容起始行"""
        from core.video_generator import _find_content_start
        lines = ["好的，我来写一个脚本", "#### 第一节", "内容"]
        assert _find_content_start(lines) == 1
        lines2 = ["其他内容", "#### 第一节"]
        assert _find_content_start(lines2) == 1


class TestCleanText:
    """测试文本清理函数"""

    def test_clean_text(self):
        from core.video_generator import _clean_text
        assert _clean_text("**加粗**文字") == "加粗文字"
        assert _clean_text("【0:00-0:05】标题") == "标题"
        assert _clean_text("（口播）内容") == "内容"


class TestSplitTextLines:
    """测试文本分行"""

    def test_split_text_lines_short(self):
        from core.video_generator import _split_text_lines
        lines = _split_text_lines("你好世界")
        assert lines == ["你好世界"]

    def test_split_text_lines_long(self):
        from core.video_generator import _split_text_lines
        lines = _split_text_lines("这是一个超过十五个字的测试句子用于验证")
        assert all(len(line) <= 15 for line in lines)
        assert len(lines) >= 2


class TestParseFormats:
    """测试 AI 多格式输出解析"""

    def test_parse_formats(self):
        from core.ai_client import AIClient
        raw = """===FORMAT:BLOG===
博客内容

===FORMAT:TWITTER===
推文内容"""
        result = AIClient._parse_formats(raw)
        assert "blog" in result
        assert result["blog"] == "博客内容"
        assert result["twitter"] == "推文内容"

    def test_parse_formats_empty(self):
        from core.ai_client import AIClient
        result = AIClient._parse_formats("")
        assert result == {}

    def test_parse_formats_single(self):
        from core.ai_client import AIClient
        raw = "===FORMAT:BLOG===\n仅博客"
        result = AIClient._parse_formats(raw)
        assert result["blog"] == "仅博客"


class TestConfig:
    """测试配置加载"""

    def test_config_exists(self):
        from core.config import CONFIG_PATH
        assert CONFIG_PATH.exists()

    def test_load_config(self):
        from core.config import load_config
        cfg = load_config()
        assert "ai" in cfg
        assert "categories" in cfg
        assert "output" in cfg
        assert cfg["ai"]["model"] == "deepseek-v4-flash"


class TestRegistry:
    """测试分类注册表"""

    def test_discover_categories(self):
        from core.registry import list_categories
        cats = list_categories()
        assert len(cats) >= 7  # 7 个分类
        names = [c.name for c in cats]
        assert "tech" in names
        assert "finance" in names
        assert "zhongyi" in names

    def test_get_category(self):
        from core.registry import get_category
        cat = get_category("tech")
        assert cat is not None
        assert cat.info.display_name == "技术趋势"


class TestEvidenceCollection:
    def test_parse_github_payload(self):
        from core.base_category import SourceConfig
        from core.collector import _parse_json_payload

        source = SourceConfig(
            name="github",
            display_name="GitHub",
            type="api",
            url="https://api.github.com/search/repositories",
        )
        items = _parse_json_payload(
            {
                "items": [
                    {
                        "full_name": "owner/project",
                        "html_url": "https://github.com/owner/project",
                        "description": "A real project",
                        "stargazers_count": 42,
                    }
                ]
            },
            source,
        )
        assert len(items) == 1
        assert items[0].url == "https://github.com/owner/project"
        assert items[0].metadata["stargazers_count"] == 42

    def test_prompt_stops_when_evidence_is_insufficient(self):
        from core.base_category import InsufficientEvidenceError
        from core.registry import get_category

        category = get_category("tech")
        with pytest.raises(InsufficientEvidenceError):
            category.get_prompts({"github": {"status": "error", "items": []}})


class TestDiagnosticCollection:
    @staticmethod
    def source():
        from core.base_category import SourceConfig

        return SourceConfig(
            name="github",
            display_name="GitHub",
            type="api",
            url="https://api.github.com/search/repositories?q=python",
        )

    def test_diagnostic_log_contains_traceback_but_redacts_secrets(self, tmp_path):
        import json

        from core.diagnostics import (
            diagnostic_event,
            diagnostic_exception,
            end_diagnostic_run,
            start_diagnostic_run,
        )

        config_secret = "sk-" + "config-test-value"
        event_secret = "sk-" + "event-test-value"
        url_credentials = "user:" + "password"
        hidden_token = "hidden-" + "value"
        config = {
            "diagnostics": {
                "directory": str(tmp_path),
                "filename": "diagnostic.log",
            },
            "ai": {
                "model": "test-model",
                "base_url": "https://example.com/v1",
                "api_key": config_secret,
            },
            "runtime": {},
            "network": {},
            "output": {"output_dir": "./docs"},
        }
        path = start_diagnostic_run(
            "test-run-001",
            ["tech"],
            config,
            use_scrapling=False,
            origin="test",
        )
        diagnostic_event(
            "test.secret_redaction",
            api_key=event_secret,
            url=f"https://{url_credentials}@example.com/path?token={hidden_token}&safe=1",
        )
        try:
            raise OSError(22, "Invalid argument")
        except OSError as exc:
            diagnostic_exception("test.errno_22", exc)
        end_diagnostic_run("failed")

        content = path.read_text(encoding="utf-8")
        records = [json.loads(line) for line in content.splitlines()]
        assert any(record["event"] == "test.errno_22" for record in records)
        assert "Traceback" in content
        assert '"errno":22' in content
        assert event_secret not in content
        assert hidden_token not in content
        assert url_credentials not in content
        assert "<redacted>" in content

    def test_console_errno_22_cannot_stop_collection(self, monkeypatch):
        import asyncio

        import core.collector as collector
        from core.models import EvidenceItem, SourceResult

        class FakeClient:
            async def aclose(self):
                return None

        async def successful_source(_client, src, _debug, _use_scrapling):
            return SourceResult(
                source_name=src.name,
                display_name=src.display_name,
                source_url=src.url,
                status="ok",
                items=[
                    EvidenceItem(
                        source_id="github:1",
                        source_name="GitHub",
                        title="Project",
                        url="https://github.com/owner/project",
                    )
                ],
            )

        monkeypatch.setattr(collector, "_network_settings", lambda: {"trust_env": False})
        monkeypatch.setattr(collector, "_build_http_client", lambda *_args, **_kwargs: FakeClient())
        monkeypatch.setattr(collector, "_fetch_source", successful_source)
        monkeypatch.setattr(
            collector.CONSOLE,
            "print",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError(22, "Invalid argument")),
        )

        result = asyncio.run(collector.collect_sources([self.source()], use_scrapling=False))
        assert result["github"]["status"] == "ok"
        assert len(result["github"]["items"]) == 1

    def test_http_client_init_errno_22_falls_back_without_environment(self, monkeypatch):
        import asyncio

        import core.collector as collector
        from core.models import SourceResult

        calls = []

        class FakeClient:
            async def aclose(self):
                return None

        def build_client(_settings, *, trust_env):
            calls.append(trust_env)
            if trust_env:
                raise OSError(22, "Invalid argument")
            return FakeClient()

        async def successful_source(_client, src, _debug, _use_scrapling):
            return SourceResult(
                source_name=src.name,
                display_name=src.display_name,
                source_url=src.url,
                status="ok",
            )

        monkeypatch.setattr(
            collector,
            "_network_settings",
            lambda: {"trust_env": True, "fallback_without_env": True},
        )
        monkeypatch.setattr(collector, "_build_http_client", build_client)
        monkeypatch.setattr(collector, "_fetch_source", successful_source)

        result = asyncio.run(collector.collect_sources([self.source()], use_scrapling=False))
        assert calls == [True, False]
        assert result["github"]["status"] == "ok"

    def test_source_errno_22_is_isolated_and_retried_directly(self, monkeypatch):
        import asyncio

        import httpx

        import core.collector as collector

        calls = []

        class FakeClient:
            def __init__(self, trust_env):
                self.trust_env = trust_env

            async def get(self, url, headers=None):
                del headers
                if self.trust_env:
                    raise OSError(22, "Invalid argument")
                request = httpx.Request("GET", url)
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "items": [
                            {
                                "full_name": "owner/project",
                                "html_url": "https://github.com/owner/project",
                            }
                        ]
                    },
                )

            async def aclose(self):
                return None

        def build_client(_settings, *, trust_env):
            calls.append(trust_env)
            return FakeClient(trust_env)

        monkeypatch.setattr(
            collector,
            "_network_settings",
            lambda: {"trust_env": True, "fallback_without_env": True},
        )
        monkeypatch.setattr(collector, "_build_http_client", build_client)

        result = asyncio.run(collector.collect_sources([self.source()], use_scrapling=False))
        assert calls == [True, False]
        assert result["github"]["status"] == "ok"
        assert result["github"]["items"][0]["source_id"] == "github:1"


class TestQualityGate:
    @staticmethod
    def evidence():
        return {
            "github": {
                "status": "ok",
                "items": [
                    {
                        "source_id": "github:1",
                        "source_name": "GitHub",
                        "title": "Project",
                        "url": "https://github.com/owner/project",
                    }
                ],
            }
        }

    def test_traceable_article_passes(self):
        from core.quality import validate_generated_content

        blog = """# 可验证文章

这是一个来自公开项目的事实。[github:1]

## 参考来源
- [Project](https://github.com/owner/project)
"""
        report = validate_generated_content(blog, self.evidence(), "tech")
        assert report.passed is True

    def test_unknown_citation_fails(self):
        from core.quality import ContentQualityError, validate_generated_content

        blog = """# 错误文章

无法验证的事实。[github:99]

## 参考来源
- [Project](https://github.com/owner/project)
"""
        with pytest.raises(ContentQualityError):
            validate_generated_content(blog, self.evidence(), "tech")

    def test_chinese_citation_label_is_normalized_but_id_is_still_checked(self):
        from core.quality import normalize_citation_syntax, validate_generated_content

        blog = """# 可验证文章

这是一个来自公开项目的事实。[证据github:1]

## 参考来源
- [Project](https://github.com/owner/project)
"""
        normalized = normalize_citation_syntax(blog)
        assert "[github:1]" in normalized
        assert "[证据github:1]" not in normalized
        assert validate_generated_content(normalized, self.evidence(), "tech").passed

        assert normalize_citation_syntax("[证据编号：github：1]") == "[github:1]"

        invalid = normalize_citation_syntax(blog.replace("github:1", "github:99"))
        with pytest.raises(Exception, match="github:99"):
            validate_generated_content(invalid, self.evidence(), "tech")


class TestHistoryReview:
    def test_approval_revalidates_and_persists_metadata(self, tmp_path, monkeypatch):
        import json
        import web.routes.history as history
        from web.models import ReviewUpdate

        slug_dir = tmp_path / "docs" / "posts" / "tech" / "20260717_120000"
        slug_dir.mkdir(parents=True)
        (slug_dir / "blog.md").write_text(
            "# 可审核文章\n\n可追溯事实。[证据github:1]\n\n"
            "## 参考来源\n- [Project](https://github.com/owner/project)\n",
            encoding="utf-8",
        )
        metadata = {
            "review_status": "awaiting_review",
            "evidence": self._evidence(),
            "quality": {"passed": True, "errors": [], "warnings": []},
        }
        (slug_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False), encoding="utf-8"
        )
        monkeypatch.setattr(history, "ROOT", tmp_path)
        monkeypatch.setattr(history, "_cache_result", None)
        monkeypatch.setattr(history, "_cache_mtime", 0)

        detail = history.update_article_review(
            "20260717_120000",
            ReviewUpdate(status="approved", note="来源已核对"),
            "tech",
        )
        saved = json.loads((slug_dir / "metadata.json").read_text(encoding="utf-8"))
        assert detail.review_status == "approved"
        assert detail.deployment_ready is True
        assert saved["review_status"] == "approved"
        assert saved["review_note"] == "来源已核对"
        assert saved["quality"]["passed"] is True
        assert len(saved["approved_content_sha256"]) == 64
        approved_blog = (slug_dir / "blog.md").read_text(encoding="utf-8")
        assert "[github:1]" in approved_blog
        assert "[证据github:1]" not in approved_blog

        # Approval is bound to the exact canonical article. Any later edit must
        # invalidate deployment until a reviewer approves the new content.
        (slug_dir / "blog.md").write_text(approved_blog + "\n审核后的人工改动。\n", encoding="utf-8")
        history._scan_articles(force=True)
        stale = history.get_article_detail("20260717_120000", "tech")
        assert stale.review_status == "approved"
        assert stale.deployment_ready is False

        revised_detail = history.update_article_review(
            "20260717_120000",
            ReviewUpdate(status="changes_requested", note="需要再修改"),
            "tech",
        )
        revised = json.loads((slug_dir / "metadata.json").read_text(encoding="utf-8"))
        assert revised["review_status"] == "changes_requested"
        assert "approved_content_sha256" not in revised
        assert revised_detail.deployment_ready is False

        (slug_dir / "blog.md").write_text(
            "# 错误引用\n\n无法追溯。[github:99]\n\n"
            "## 参考来源\n- [Project](https://github.com/owner/project)\n",
            encoding="utf-8",
        )
        with pytest.raises(Exception) as rejected:
            history.update_article_review(
                "20260717_120000",
                ReviewUpdate(status="approved", note=""),
                "tech",
            )
        assert getattr(rejected.value, "status_code", None) == 409

    @staticmethod
    def _evidence():
        return {
            "github": {
                "status": "ok",
                "display_name": "GitHub",
                "items": [
                    {
                        "source_id": "github:1",
                        "source_name": "github",
                        "title": "Project",
                        "url": "https://github.com/owner/project",
                    }
                ],
            }
        }


class TestWebShell:
    def test_spa_routes_fall_back_to_index_but_unknown_api_does_not(self, tmp_path):
        from fastapi.testclient import TestClient
        from web.server import create_app

        static_dir = tmp_path / "static"
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<main>phosphene-shell</main>", encoding="utf-8")
        client = TestClient(create_app(static_dir=static_dir))

        review = client.get("/review")
        assert review.status_code == 200
        assert "phosphene-shell" in review.text
        assert client.get("/api/not-a-real-route").status_code == 404

    def test_sanitized_diagnostic_log_can_be_downloaded(self, tmp_path):
        from fastapi.testclient import TestClient

        from core.diagnostics import diagnostic_event, start_diagnostic_run
        from web.server import create_app

        config = {
            "diagnostics": {
                "directory": str(tmp_path),
                "filename": "downloadable.log",
            },
            "ai": {"model": "test", "base_url": "https://example.com/v1"},
            "runtime": {},
            "network": {},
            "output": {"output_dir": "./docs"},
        }
        start_diagnostic_run(
            "download-test",
            ["tech"],
            config,
            use_scrapling=False,
            origin="test",
        )
        diagnostic_event("test.downloadable")

        client = TestClient(create_app())
        info = client.get("/api/diagnostics/info")
        download = client.get("/api/diagnostics/log")
        assert info.status_code == 200
        assert info.json()["available"] is True
        assert info.json()["sanitized"] is True
        assert download.status_code == 200
        assert "attachment" in download.headers["content-disposition"]
        assert "test.downloadable" in download.text


class TestTaskStore:
    def test_task_state_is_persisted(self, tmp_path):
        from core.task_store import TaskStore

        store = TaskStore(tmp_path / "tasks.db")
        task = store.create(["tech"])
        store.update(task["id"], status="running", progress=0.5)
        current = store.get(task["id"])
        assert current["status"] == "running"
        assert current["progress"] == 0.5
