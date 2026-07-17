"""Asset selection and provenance records for the video renderer."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def select_asset(
    scene: dict[str, Any],
    pexels_key: str | None,
    fetcher: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Select one truthful visual asset, returning an auditable record.

    Evidence scenes deliberately do not call a stock provider: an infographic is
    safer than unrelated footage until a browser screenshot capture is available.
    """
    if scene.get("asset_strategy") == "evidence_or_infographic":
        return _infographic_asset(scene)

    if not pexels_key:
        return _graphic_asset(scene)

    payload = fetcher(scene["asset_query"]) if fetcher else _search_pexels(
        scene["asset_query"], pexels_key
    )
    video = _first_portrait_video(payload)
    if video is None:
        return _graphic_asset(scene)

    file = next(
        item for item in video.get("video_files", [])
        if item.get("width", 0) <= item.get("height", 0) and item.get("link")
    )
    user = video.get("user", {})
    return {
        "kind": "stock_video",
        "source": "pexels",
        "download_url": file["link"],
        "attribution": {
            "creator": user.get("name", "Pexels creator"),
            "creator_url": user.get("url", ""),
            "source_url": video.get("url", ""),
            "license": "Pexels License",
        },
    }


def _first_portrait_video(payload: dict[str, Any]) -> dict[str, Any] | None:
    for video in payload.get("videos", []):
        if any(
            file.get("width", 0) <= file.get("height", 0) and file.get("link")
            for file in video.get("video_files", [])
        ):
            return video
    return None


def _search_pexels(query: str, api_key: str) -> dict[str, Any]:
    params = urlencode({"query": query, "per_page": 5, "orientation": "portrait"})
    request = Request(
        f"https://api.pexels.com/v1/videos/search?{params}",
        headers={"Authorization": api_key},
    )
    with urlopen(request, timeout=15) as response:  # nosec B310: fixed HTTPS host
        return json.loads(response.read().decode("utf-8"))


def _infographic_asset(scene: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "infographic",
        "source": "generated",
        "label": "Source-backed information card",
        "attribution": {},
        "query": scene.get("asset_query", ""),
    }


def _graphic_asset(scene: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "motion_graphic",
        "source": "generated",
        "label": "Procedural motion graphic",
        "attribution": {},
        "query": scene.get("asset_query", ""),
    }
