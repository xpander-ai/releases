import datetime as dt
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".github" / "scripts"))

import new_release as nr  # noqa: E402

TODAY = dt.date(2026, 10, 5)
SHA = "16bbdb30adbbf947981492c193916c3dd2ab84d8"


def manifest(release_id="onprem-36983327833", channel="production"):
    return {
        "schema_version": 1,
        "release_id": release_id,
        "channel": channel,
        "source": {"repository": "xpander-ai/xpander-mono", "branch": "main", "sha": SHA},
        "images": {"agent-controller": {"tag": "0.0.659", "digest": "sha256:" + "a" * 64}},
    }


@pytest.fixture
def remote(monkeypatch):
    """Serve the four remote reads from fixtures."""
    index = "apiVersion: v1\nentries:\n  xpander:\n  - name: xpander\n    version: 0.20.31\n  - name: xpander\n    version: 0.20.9\n  - name: xpander\n    version: 0.21.0-rc1\n"
    refs = [{"ref": f"refs/tags/airgap-chart-v{v}"} for v in ("0.14.9", "0.14.40", "0.14.39")]
    approved = {"onprem-36983327833": manifest()}

    def fetch(url, token=""):
        if url == nr.HYBRID_INDEX:
            return index
        if url == nr.AIRGAP_TAGS_API:
            return json.dumps(refs)
        if url.endswith("/latest/release-manifest.json"):
            return json.dumps(manifest())
        release_id = url.split("/download/")[1].split("/")[0]
        if release_id in approved:
            return json.dumps(approved[release_id])
        raise OSError("404")

    monkeypatch.setattr(nr, "fetch", fetch)
    return approved


def run(tmp_path, **env):
    env.setdefault("CHARTS_TOKEN", "token")
    outputs = nr.prepare(env, str(tmp_path), TODAY)
    read = lambda name: (tmp_path / name).read_text()  # noqa: E731
    return outputs, read


def test_newest_ignores_prereleases_and_sorts_numerically():
    assert nr.newest(["0.14.9", "0.14.40", "0.15.0-rc1", "junk"]) == "0.14.40"


def test_both_resolves_newest_everything(remote, tmp_path):
    outputs, read = run(tmp_path, RELEASE_TYPE="both")
    assert outputs["tag"] == "v2026.10.05"
    assert outputs["title"] == "xpander.ai Self-Hosted · October 5, 2026"
    assert (outputs["airgap"], outputs["hybrid"], outputs["image_set"]) == ("0.14.40", "0.20.31", "onprem-36983327833")
    notes = read("notes.md")
    assert "### Air-gapped installs" in notes and "### Hybrid installs" in notes
    assert "releases/download/v2026.10.05/release-manifest.json" in notes
    assert "--version 0.14.40" in notes and "--version 0.20.31" in notes
    assert json.loads(read("release-manifest.json"))["channel"] == "production"


def test_preview_lists_resolutions_and_publish_does_not(remote, tmp_path):
    _, read = run(tmp_path, RELEASE_TYPE="both")
    assert "Air-gapped chart `0.14.40` (newest)" in read("notes-preview.md")
    assert "Preview." not in read("notes.md")
    assert read("notes-preview.md").endswith(read("notes.md"))


def test_hybrid_only_needs_no_image_set(remote, tmp_path):
    outputs, read = run(tmp_path, RELEASE_TYPE="hybrid", HYBRID_CHART="0.20.30")
    assert outputs["image_set"] == "" and outputs["airgap"] == ""
    assert "Air-gapped" not in read("notes.md") and "### Hybrid" not in read("notes.md")
    assert not (tmp_path / "release-manifest.json").exists()


def test_unapproved_image_set_is_refused(remote, tmp_path):
    remote["onprem-1"] = manifest("onprem-1", channel="candidate")
    with pytest.raises(nr.ReleaseError, match="not approved"):
        run(tmp_path, RELEASE_TYPE="airgap", IMAGE_SET="onprem-1")


def test_image_set_without_approval_file_is_refused(remote, tmp_path):
    with pytest.raises(nr.ReleaseError, match="has not passed"):
        run(tmp_path, RELEASE_TYPE="airgap", IMAGE_SET="onprem-2")


def test_bad_image_set_name_is_refused(remote, tmp_path):
    with pytest.raises(nr.ReleaseError, match="latest-approved or onprem"):
        run(tmp_path, RELEASE_TYPE="airgap", IMAGE_SET="newest")


def test_text_fields_render_in_order(remote, tmp_path):
    _, read = run(tmp_path, RELEASE_TYPE="airgap", ACTION_REQUIRED="true", WHATS_NEW="A ;; B;;", SECURITY="C",
                  EXTRA_UPGRADE_NOTES="Back up first.")
    notes = read("notes.md")
    assert notes.index("Action required.** Run every step below, in order.") < notes.index("## What's new")
    assert "- A\n- B\n\n## Security\n\n- C" in notes
    assert "**Before you start.** Back up first." in notes


def test_empty_sections_are_left_out(remote, tmp_path):
    _, read = run(tmp_path, RELEASE_TYPE="hybrid")
    assert "## What's new" not in read("notes.md") and "## Security" not in read("notes.md")


def test_explicit_date_and_title(remote, tmp_path):
    outputs, _ = run(tmp_path, RELEASE_TYPE="hybrid", RELEASE_DATE="2026-09-30", TITLE="Hotfix")
    assert (outputs["tag"], outputs["title"], outputs["date"]) == ("v2026.09.30", "Hotfix", "2026-09-30")


def test_bad_date_is_refused(remote, tmp_path):
    with pytest.raises(nr.ReleaseError, match="YYYY-MM-DD"):
        run(tmp_path, RELEASE_TYPE="hybrid", RELEASE_DATE="5/10/2026")


def test_notes_file_override_keeps_its_text_and_front_matter(remote, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("notes").mkdir()
    Path("notes/custom.md").write_text("---\ntag: v2026.09.30\ntitle: Custom title\n---\nHand written body.\n")
    outputs, read = run(tmp_path, RELEASE_TYPE="airgap", NOTES_FILE="notes/custom.md")
    assert (outputs["tag"], outputs["title"], outputs["date"]) == ("v2026.09.30", "Custom title", "2026-09-30")
    assert read("notes.md") == "Hand written body.\n"
    assert read("notes-file.md").startswith("---\ntag: v2026.09.30\ntitle: Custom title\n---\n")
    assert (tmp_path / "release-manifest.json").exists()


def test_missing_notes_file_is_refused(remote, tmp_path):
    with pytest.raises(nr.ReleaseError, match="does not exist"):
        run(tmp_path, RELEASE_TYPE="hybrid", NOTES_FILE="notes/nope.md")


def test_airgap_tags_unreachable_asks_for_a_version(monkeypatch, remote, tmp_path):
    original = nr.fetch

    def fetch(url, token=""):
        if url == nr.AIRGAP_TAGS_API:
            raise OSError("404")
        return original(url, token)

    monkeypatch.setattr(nr, "fetch", fetch)
    with pytest.raises(nr.ReleaseError, match="type the version"):
        run(tmp_path, RELEASE_TYPE="airgap")
    outputs, _ = run(tmp_path, RELEASE_TYPE="airgap", AIRGAP_CHART="0.14.40")
    assert outputs["airgap"] == "0.14.40"


def test_hybrid_versions_without_yaml(monkeypatch):
    monkeypatch.setitem(sys.modules, "yaml", None)
    assert nr.hybrid_versions("entries:\n  xpander:\n  - name: x\n    version: 0.20.31\n") == ["0.20.31"]


def test_notes_file_outside_notes_is_refused(remote, tmp_path):
    with pytest.raises(nr.ReleaseError, match="notes/<name>.md"):
        run(tmp_path, RELEASE_TYPE="hybrid", NOTES_FILE="../../etc/passwd")


def test_notes_file_with_a_malformed_tag_is_refused(remote, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("notes").mkdir()
    Path("notes/bad.md").write_text("---\ntag: v1 $(id)\n---\nBody.\n")
    with pytest.raises(nr.ReleaseError, match="vYYYY.MM.DD"):
        run(tmp_path, RELEASE_TYPE="hybrid", NOTES_FILE="notes/bad.md")


def test_newest_airgap_without_the_token_asks_for_a_version(remote, tmp_path):
    with pytest.raises(nr.ReleaseError, match="RELEASES_REPO_TOKEN"):
        run(tmp_path, RELEASE_TYPE="airgap", CHARTS_TOKEN="")
    outputs, _ = run(tmp_path, RELEASE_TYPE="hybrid", CHARTS_TOKEN="")
    assert outputs["hybrid"] == "0.20.31"
