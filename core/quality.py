"""Deterministic quality gates for generated content."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class ContentQualityError(RuntimeError):
    pass


@dataclass
class QualityReport:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cited_sources: list[str] = field(default_factory=list)
    evidence_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "cited_sources": self.cited_sources,
            "evidence_count": self.evidence_count,
        }


def normalize_citation_syntax(blog: str) -> str:
    """Normalize common model variants without weakening evidence checks.

    Only the optional Chinese label around an otherwise canonical source id is
    removed. The normalized id is still checked against the collected evidence.
    """
    return re.sub(
        r"\[(?:证据(?:编号)?\s*[:：]?\s*)?([\w-]+)\s*[:：]\s*(\d+)\]",
        r"[\1:\2]",
        blog,
        flags=re.I,
    )


def validate_generated_content(
    blog: str,
    evidence_results: dict[str, dict[str, Any]],
    category: str,
) -> QualityReport:
    """Reject drafts that are not traceable to collected evidence."""
    blog = normalize_citation_syntax(blog)
    errors: list[str] = []
    warnings: list[str] = []
    evidence_items = [
        item
        for result in evidence_results.values()
        if result.get("status") == "ok"
        for item in result.get("items", [])
    ]
    known_ids = {str(item.get("source_id")) for item in evidence_items}
    citations = sorted(set(re.findall(r"\[([\w-]+:\d+)\]", blog)))

    if not re.search(r"(?m)^#\s+\S+", blog):
        errors.append("缺少一级标题")
    if "## 参考来源" not in blog:
        errors.append("缺少“参考来源”章节")
    if not re.search(r"https?://", blog):
        errors.append("文章中没有可点击的原始来源链接")
    if not citations:
        errors.append("正文没有证据编号引用")

    unknown = sorted(set(citations) - known_ids)
    if unknown:
        errors.append(f"引用了不存在的证据编号: {', '.join(unknown)}")

    banned_patterns = {
        r"基于\s*AI\s*知识补充": "包含‘基于AI知识补充’",
        r"^(好的|当然|没问题)[，,]": "包含模型寒暄前言",
        r"根据.*?ID.*?(推断|判断|显示)": "根据不透明ID推断事实",
    }
    for pattern, message in banned_patterns.items():
        if re.search(pattern, blog, flags=re.I | re.M):
            errors.append(message)

    if len(blog.strip()) < 500:
        warnings.append("文章较短，请人工确认是否信息不足")

    if category == "finance" and not re.search(r"不构成.{0,8}(投资|财务)建议", blog):
        errors.append("财经内容缺少‘不构成投资建议’声明")
    if category == "zhongyi" and not re.search(r"不构成.{0,8}(医疗|诊疗|个体)建议", blog):
        errors.append("健康内容缺少医疗建议免责声明")

    report = QualityReport(
        passed=not errors,
        errors=errors,
        warnings=warnings,
        cited_sources=citations,
        evidence_count=len(evidence_items),
    )
    if errors:
        raise ContentQualityError("；".join(errors))
    return report
