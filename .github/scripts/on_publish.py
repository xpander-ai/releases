"""Finish a release a person just published: attach its approved image set, move Current image set, announce it."""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO = "xpander-ai/releases"
MANIFESTS_REPO = "xpander-ai/release-manifests"
MANIFESTS_DOWNLOAD = f"https://github.com/{MANIFESTS_REPO}/releases/download"
POINTER = "latest"
HYBRID_ONLY = "Hybrid only"
IMAGE_SET = re.compile(r"Image set:?\**:?\s*\[?`?(onprem-[1-9][0-9]*)")
AIRGAP_CHART = re.compile(r"`xpander-airgap`\s*`(\d+\.\d+\.\d+)`")
HYBRID_CHART = re.compile(r"`xpander`\s*`(\d+\.\d+\.\d+)`")
BOT_LINES = ("<!-- auto-draft -->", "<!-- auto:begin -->", "<!-- auto:end -->")
BOT_NOTE = re.compile(r"^> \[!NOTE\]\n> Drafted automatically[^\n]*\n\n?", re.M)
PR_DETAILS = re.compile(r"<details><summary>PRs since last release</summary>.*?</details>\n?", re.S)
SLACK = Path(__file__).with_name("release_slack.py")


class NotApproved(Exception):
    pass


def image_set(body):
    match = IMAGE_SET.search(body or "")
    return match.group(1) if match else None


def chart_versions(body):
    airgap, hybrid = AIRGAP_CHART.search(body or ""), HYBRID_CHART.search(body or "")
    return (airgap.group(1) if airgap else ""), (hybrid.group(1) if hybrid else "")


def strip_bot_text(body):
    """Drop the draft's bot scaffolding; the Image set and versions lines stay."""
    body = PR_DETAILS.sub("", body)
    body = BOT_NOTE.sub("", body)
    lines = [line for line in body.split("\n") if line.strip() not in BOT_LINES]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def newest_approved():
    raw = fetch(f"{MANIFESTS_DOWNLOAD}/latest/release-manifest.json")
    if raw is None:
        raise NotApproved("no approved image set exists yet")
    return json.loads(raw)["release_id"]


def approved_manifest(release_id):
    """The approved manifest bytes for release_id; raises NotApproved when it never passed verification."""
    raw = fetch(f"{MANIFESTS_DOWNLOAD}/{release_id}/approved-release-manifest.json")
    if raw is None:
        raise NotApproved(f"image set {release_id} is not approved")
    data = json.loads(raw)
    if data.get("channel") != "production" or data.get("release_id") != release_id or not data.get("images"):
        raise NotApproved(f"image set {release_id} is not approved")
    return raw


def release_number(release_id):
    return int(release_id.split("-")[1])


def current_pointer():
    """The image set Current image set serves now, or None."""
    raw = fetch(f"https://github.com/{REPO}/releases/download/{POINTER}/release-manifest.json")
    return json.loads(raw).get("release_id") if raw else None


def should_move(release_id, current, move_current, dispatched):
    """Published releases only move the pointer forward; a dispatch moves it only when asked, even backwards."""
    if dispatched:
        return move_current
    return current is None or release_number(release_id) >= release_number(current)


def gh(*args, token=None):
    env = dict(os.environ)
    if token:
        env["GH_TOKEN"] = token
    return subprocess.check_output(["gh", *args], text=True, env=env)


def slack(*args):
    subprocess.run([sys.executable, str(SLACK), *args], check=False)


def mark_released(release_id, tag):
    """Best effort: flip the candidate's Slack card to Released."""
    token = os.environ.get("MANIFESTS_TOKEN", "")
    raw = fetch(f"{MANIFESTS_DOWNLOAD}/{release_id}/slack.json")
    if raw is None or not token:
        return
    with tempfile.TemporaryDirectory() as directory:
        state = Path(directory) / "slack.json"
        state.write_bytes(raw)
        slack("released", "--state", str(state), "--tag", tag)
        try:
            gh("release", "upload", release_id, str(state), "--repo", MANIFESTS_REPO, "--clobber", token=token)
        except subprocess.CalledProcessError as exc:
            print(f"::warning::Slack card state not saved: {exc}")


def finish(release, actor, dispatched=False, move_current=False):
    tag, body = release["tag_name"], release.get("body") or ""
    if tag == POINTER:
        print("Current image set is maintained by this workflow; nothing to do.")
        return 0
    hybrid_only = HYBRID_ONLY in body
    release_id = None
    if not hybrid_only:
        try:
            release_id = image_set(body) or newest_approved()
            manifest = approved_manifest(release_id)
        except NotApproved as exc:
            if dispatched:
                print(f"::error::{tag}: {exc}")
                return 1
            gh("release", "edit", tag, "--repo", REPO, "--draft=true")
            slack("notice", "--text", f"⚠️ *{tag}* moved back to draft · {exc}")
            print(f"::error::{tag} moved back to draft: {exc}")
            return 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release-manifest.json"
            path.write_bytes(manifest)
            gh("release", "upload", tag, str(path), "--repo", REPO, "--clobber")
            current = current_pointer()
            if should_move(release_id, current, move_current, dispatched):
                gh("release", "upload", POINTER, str(path), "--repo", REPO, "--clobber")
                print(f"Current image set: {current} -> {release_id}")
            else:
                print(f"::warning::Current image set stays on {current}; {release_id} is older or move_current is off")
    cleaned = strip_bot_text(body)
    if release_id and not image_set(cleaned):
        cleaned = f"Image set: [`{release_id}`](https://github.com/{MANIFESTS_REPO}/releases/tag/{release_id})\n\n{cleaned}"
    with tempfile.TemporaryDirectory() as directory:
        notes = Path(directory) / "notes.md"
        notes.write_text(cleaned)
        badge = [] if dispatched else ["--latest"]
        gh("release", "edit", tag, "--repo", REPO, *badge, "--notes-file", str(notes))
    airgap, hybrid = chart_versions(cleaned)
    slack("release-message", "--tag", tag, "--title", release.get("name") or tag, "--url", release["html_url"],
          "--actor", actor, "--airgap", airgap, "--hybrid", hybrid, "--images", release_id or "")
    if release_id:
        mark_released(release_id, tag)
    print(f"{tag} finished" + (f" with image set {release_id}" if release_id else " (hybrid only)"))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", help="path to the release event payload")
    parser.add_argument("--tag", help="re-process an already published release")
    parser.add_argument("--move-current", default="false", choices=("true", "false"))
    args = parser.parse_args(argv)
    if args.event:
        event = json.loads(Path(args.event).read_text())
        return finish(event["release"], event.get("sender", {}).get("login", ""))
    view = json.loads(gh("release", "view", args.tag, "--repo", REPO, "--json", "tagName,body,name,url,isDraft"))
    if view["isDraft"]:
        print(f"::error::{args.tag} is still a draft; publish it on GitHub first")
        return 1
    release = {"tag_name": view["tagName"], "body": view["body"], "name": view["name"], "html_url": view["url"]}
    return finish(release, os.environ.get("ACTOR", ""), dispatched=True, move_current=args.move_current == "true")


if __name__ == "__main__":
    sys.exit(main())
