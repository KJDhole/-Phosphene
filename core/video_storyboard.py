"""Validated, renderer-facing storyboard data for production short videos."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


VIDEO_FORMAT = {"width": 1080, "height": 1920, "fps": 30}

# These are layout names, not merely text animation names.  Remotion uses them
# to select a composition with an actual visual hierarchy.
LAYOUT_BY_VISUAL_TYPE = {
    "explode": "hook",
    "number": "fact_card",
    "text": "explain",
    "pop": "analogy",
    "tag": "quote",
    "chain": "process",
    "ending": "ending",
}

# Numerical claims and source-backed explanation must never be illustrated by
# unrelated stock footage.  They use an article source screenshot when one is
# available and fall back to a truthful infographic when it is not.
EVIDENCE_LAYOUTS = {"fact_card", "explain", "process"}


def build_storyboard(parsed: dict[str, Any], evidence_urls: list[str]) -> dict[str, Any]:
    """Return a stable, JSON-serialisable 9:16 storyboard.

    ``parsed`` remains intentionally compatible with the current markdown
    parser.  This lets existing scripts be regenerated through the new render
    path without making the renderer depend on prompt formatting.
    """
    scenes = parsed.get("scenes", [])
    if len(scenes) != 8:
        raise ValueError(f"Production video requires exactly 8 scenes, got {len(scenes)}")

    result_scenes = []
    for position, source_scene in enumerate(scenes):
        scene = deepcopy(source_scene)
        visual_type = scene.get("visualType", "text")
        layout = LAYOUT_BY_VISUAL_TYPE.get(visual_type, "explain")
        uses_evidence = layout in EVIDENCE_LAYOUTS
        scene.update(
            {
                "order": position,
                "layout": layout,
                "asset_strategy": (
                    "evidence_or_infographic" if uses_evidence else "stock_or_graphic"
                ),
                "evidence_urls": list(evidence_urls) if uses_evidence else [],
                "asset_query": _asset_query(scene, parsed.get("category", "tech")),
            }
        )
        result_scenes.append(scene)

    return {
        "version": 1,
        "title": parsed.get("title", ""),
        "category": parsed.get("category", "tech"),
        "format": VIDEO_FORMAT.copy(),
        "scenes": result_scenes,
    }


def _asset_query(scene: dict[str, Any], category: str) -> str:
    """Produce a conservative stock-search query when stock is permitted."""
    text = " ".join(str(line) for line in scene.get("lines", []))
    name = str(scene.get("name", ""))
    # Pexels responds more consistently to concise English category anchors;
    # Chinese scene text is preserved for auditability in the manifest.
    category_anchor = {
        "tech": "technology", "finance": "finance", "business": "business",
        "world": "world", "literature": "books", "entertainment": "creative",
    }.get(category, "abstract")
    return f"{category_anchor} vertical video | {name} | {text}".strip()
