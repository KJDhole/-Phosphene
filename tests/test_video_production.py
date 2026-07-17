"""Production-video storyboard behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.video_storyboard import build_storyboard
from core.video_assets import select_asset
from core.video_generator import write_video_manifest
from core.video_generator import allocate_audio_frames
from core.video_generator import update_video_review_status


def test_build_storyboard_creates_eight_traceable_vertical_scenes():
    parsed = {
        "title": "AI 芯片为什么更快",
        "category": "tech",
        "scenes": [
            {
                "id": index,
                "name": f"场景{index}",
                "visualType": visual_type,
                "gradient": "a1",
                "lines": [f"第{index}段文案"],
            }
            for index, visual_type in enumerate(
                ["explode", "number", "text", "pop", "text", "tag", "chain", "ending"]
            )
        ],
    }

    storyboard = build_storyboard(parsed, evidence_urls=["https://example.com/source"])

    assert storyboard["format"] == {"width": 1080, "height": 1920, "fps": 30}
    assert len(storyboard["scenes"]) == 8
    assert storyboard["scenes"][1]["asset_strategy"] == "evidence_or_infographic"
    assert storyboard["scenes"][1]["evidence_urls"] == ["https://example.com/source"]
    assert storyboard["scenes"][0]["asset_strategy"] == "stock_or_graphic"
    assert storyboard["scenes"][7]["layout"] == "ending"


def test_build_storyboard_rejects_scripts_that_are_not_eight_scenes():
    parsed = {"title": "x", "category": "tech", "scenes": []}

    try:
        build_storyboard(parsed, evidence_urls=[])
    except ValueError as exc:
        assert "8" in str(exc)
    else:
        raise AssertionError("expected an invalid storyboard to be rejected")


def test_evidence_scene_falls_back_to_infographic_without_a_source_capture():
    scene = {
        "asset_strategy": "evidence_or_infographic",
        "evidence_urls": [],
        "asset_query": "technology vertical video",
    }

    asset = select_asset(scene, pexels_key=None)

    assert asset["kind"] == "infographic"
    assert asset["source"] == "generated"


def test_stock_scene_records_pexels_attribution_when_a_result_is_available():
    scene = {
        "asset_strategy": "stock_or_graphic",
        "asset_query": "technology vertical video",
    }
    response = {
        "videos": [{
            "id": 42,
            "url": "https://www.pexels.com/video/42/",
            "user": {"name": "Ava", "url": "https://www.pexels.com/@ava"},
            "video_files": [{"width": 1080, "height": 1920, "link": "https://cdn.example/42.mp4"}],
        }]
    }

    asset = select_asset(scene, pexels_key="key", fetcher=lambda _query: response)

    assert asset["kind"] == "stock_video"
    assert asset["download_url"] == "https://cdn.example/42.mp4"
    assert asset["attribution"]["creator"] == "Ava"


def test_write_video_manifest_persists_review_gate_and_asset_provenance(tmp_path):
    destination = tmp_path / "video_manifest.json"
    storyboard = {"version": 1, "scenes": [{"id": 0}]}
    assets = [{"kind": "motion_graphic", "source": "generated"}]

    write_video_manifest(destination, storyboard, assets)

    import json
    saved = json.loads(destination.read_text(encoding="utf-8"))
    assert saved["review_status"] == "awaiting_review"
    assert saved["assets"] == assets


def test_allocate_audio_frames_preserves_total_duration_and_each_scene_is_visible():
    frames = allocate_audio_frames([2, 8, 20], total_frames=300)

    assert sum(frames) == 300
    assert all(frame >= 30 for frame in frames)
    assert frames[2] > frames[1] > frames[0]


def test_update_video_review_status_requires_an_existing_manifest(tmp_path):
    import json
    manifest = tmp_path / "video_manifest.json"
    manifest.write_text(json.dumps({"review_status": "awaiting_review"}), encoding="utf-8")

    update_video_review_status(manifest, "approved", "looks good")

    saved = json.loads(manifest.read_text(encoding="utf-8"))
    assert saved["review_status"] == "approved"
    assert saved["review_note"] == "looks good"
