"""Publishing finishes a release: approved image set attached, Current image set only moves forward, Slack told once."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".github" / "scripts"))
import on_publish as op

APPROVED = {"channel": "production", "release_id": "onprem-200", "images": {"api": {"tag": "0.0.1", "digest": "sha256:" + "a" * 64}}}
BODY = (
    "<!-- auto-draft -->\n> [!NOTE]\n> Drafted automatically after this image set passed staging and production. Edit it.\n\n"
    "<!-- auto:begin -->\nImage set: [`onprem-200`](https://github.com/xpander-ai/release-manifests/releases/tag/onprem-200)\n\n"
    "**Air-gapped Helm chart:** `xpander-airgap` `0.14.40` · **Hybrid Helm chart:** `xpander` `0.20.31`\n\n"
    "<details><summary>PRs since last release</summary>\n\n- One (#1)\n\n</details>\n<!-- auto:end -->\n\n## What's new\n\n- Real line\n"
)


def test_image_set_accepts_plain_bold_and_link_forms():
    assert op.image_set("Image set: onprem-5") == "onprem-5"
    assert op.image_set("**Image set:** [`onprem-6`](https://x)") == "onprem-6"
    assert op.image_set("Image set: [`onprem-7`](https://x)") == "onprem-7"
    assert op.image_set("no set here") is None


def test_chart_versions_are_read_from_the_versions_line():
    assert op.chart_versions(BODY) == ("0.14.40", "0.20.31")
    assert op.chart_versions("nothing") == ("", "")


def test_strip_bot_text_keeps_image_set_versions_and_human_text():
    cleaned = op.strip_bot_text(BODY)
    for gone in ("auto-draft", "auto:begin", "auto:end", "Drafted automatically", "PRs since last release", "- One (#1)"):
        assert gone not in cleaned
    assert "Image set: [`onprem-200`]" in cleaned and "`xpander-airgap` `0.14.40`" in cleaned and "- Real line" in cleaned


@pytest.mark.parametrize("release_id,current,move,dispatched,expected", [
    ("onprem-200", None, False, False, True),
    ("onprem-200", "onprem-100", False, False, True),
    ("onprem-200", "onprem-200", False, False, True),
    ("onprem-100", "onprem-200", False, False, False),
    ("onprem-100", "onprem-200", False, True, False),
    ("onprem-100", "onprem-200", True, True, True),
    ("onprem-300", "onprem-200", False, True, False),
])
def test_should_move(release_id, current, move, dispatched, expected):
    assert op.should_move(release_id, current, move, dispatched) is expected


def _world(monkeypatch, approved=APPROVED, pointer="onprem-100", slack_state=None):
    calls, posts = [], []
    files = {
        f"{op.MANIFESTS_DOWNLOAD}/latest/release-manifest.json": json.dumps({"release_id": "onprem-200"}).encode(),
        f"https://github.com/{op.REPO}/releases/download/latest/release-manifest.json": json.dumps({"release_id": pointer}).encode() if pointer else None,
    }
    if approved is not None:
        files[f"{op.MANIFESTS_DOWNLOAD}/{approved['release_id']}/approved-release-manifest.json"] = json.dumps(approved).encode()
    if slack_state is not None:
        files[f"{op.MANIFESTS_DOWNLOAD}/onprem-200/slack.json"] = json.dumps(slack_state).encode()
    monkeypatch.setattr(op, "fetch", lambda url: files.get(url))

    def fake_gh(*args, token=None):
        record = list(args)
        if "--notes-file" in args:
            record.append(Path(args[args.index("--notes-file") + 1]).read_text())
        calls.append(record)
        return ""
    monkeypatch.setattr(op, "gh", fake_gh)
    monkeypatch.setattr(op, "slack", lambda *args: posts.append(args))
    return calls, posts


RELEASE = {"tag_name": "v2026.10.05", "name": "xpander.ai Self-Hosted · October 5, 2026", "html_url": "https://r", "body": BODY}


def test_publish_attaches_moves_forward_cleans_and_announces(monkeypatch):
    calls, posts = _world(monkeypatch)
    assert op.finish(RELEASE, "moriel") == 0
    uploads = [c[2] for c in calls if c[:2] == ["release", "upload"]]
    assert uploads == ["v2026.10.05", "latest"]
    edit = next(c for c in calls if c[:2] == ["release", "edit"])
    assert "--latest" in edit and "auto-draft" not in edit[-1]
    message = next(p for p in posts if p[0] == "release-message")
    assert message[message.index("--images") + 1] == "onprem-200" and message[message.index("--airgap") + 1] == "0.14.40"


def test_publish_never_moves_current_backwards(monkeypatch):
    calls, _ = _world(monkeypatch, pointer="onprem-300")
    assert op.finish(RELEASE, "moriel") == 0
    assert [c[2] for c in calls if c[:2] == ["release", "upload"]] == ["v2026.10.05"]


def test_unapproved_image_set_goes_back_to_draft(monkeypatch):
    calls, posts = _world(monkeypatch, approved=None)
    assert op.finish(RELEASE, "moriel") == 1
    assert ["release", "edit", "v2026.10.05", "--repo", op.REPO, "--draft=true"] in calls
    assert posts[0][0] == "notice" and "moved back to draft" in posts[0][2]
    assert not any(c[:2] == ["release", "upload"] for c in calls)


def test_a_candidate_manifest_is_not_approved(monkeypatch):
    _world(monkeypatch, approved={**APPROVED, "channel": "candidate"})
    with pytest.raises(op.NotApproved):
        op.approved_manifest("onprem-200")


def test_blank_image_set_uses_newest_approved(monkeypatch):
    calls, _ = _world(monkeypatch)
    release = {**RELEASE, "body": "## What's new\n\n- x\n"}
    assert op.finish(release, "moriel") == 0
    edit = next(c for c in calls if c[:2] == ["release", "edit"])
    assert edit[-1].startswith("Image set: [`onprem-200`]")


def test_hybrid_only_skips_the_manifest(monkeypatch):
    calls, posts = _world(monkeypatch)
    assert op.finish({**RELEASE, "body": "Hybrid only\n\n**Hybrid Helm chart:** `xpander` `0.20.31`\n"}, "moriel") == 0
    assert not any(c[:2] == ["release", "upload"] for c in calls)
    assert any(p[0] == "release-message" for p in posts)


def test_dispatch_keeps_current_unless_asked_and_never_takes_the_badge(monkeypatch):
    calls, _ = _world(monkeypatch, pointer="onprem-300")
    assert op.finish(RELEASE, "moriel", dispatched=True) == 0
    assert [c[2] for c in calls if c[:2] == ["release", "upload"]] == ["v2026.10.05"]
    assert "--latest" not in next(c for c in calls if c[:2] == ["release", "edit"])
    calls, _ = _world(monkeypatch, pointer="onprem-300")
    assert op.finish(RELEASE, "moriel", dispatched=True, move_current=True) == 0
    assert [c[2] for c in calls if c[:2] == ["release", "upload"]] == ["v2026.10.05", "latest"]


def test_dispatch_on_an_unapproved_set_fails_without_unpublishing(monkeypatch):
    calls, _ = _world(monkeypatch, approved=None)
    assert op.finish(RELEASE, "moriel", dispatched=True) == 1
    assert not any("--draft=true" in c for c in calls)


def test_the_pointer_release_itself_is_ignored(monkeypatch):
    calls, posts = _world(monkeypatch)
    assert op.finish({**RELEASE, "tag_name": "latest"}, "x") == 0
    assert not calls and not posts


def test_released_card_flip_needs_state_and_token(monkeypatch):
    monkeypatch.setenv("MANIFESTS_TOKEN", "t")
    calls, posts = _world(monkeypatch, slack_state={"ts": "1"})
    op.finish(RELEASE, "moriel")
    assert any(p[0] == "released" for p in posts)
    assert any(c[:3] == ["release", "upload", "onprem-200"] for c in calls)
