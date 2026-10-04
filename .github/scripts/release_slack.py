# Vendored from xpander-mono platform/onprem-bundle/release_slack.py - keep identical.
"""Post and update the #xpander-releases Slack card for an on-prem release candidate."""

import argparse
import json
import os
import sys
import urllib.request

CHANNEL = "C0C6MMPCF89"
STAGES = ("candidate", "staging", "production", "approved", "released")
LABELS = {"candidate": "Candidate", "staging": "Staging", "production": "Production", "approved": "Approved", "released": "Released"}
MARKS = {"pending": "◻️", "running": "⏳", "done": "✅", "failed": "❌", "skipped": "⏭️"}
NEW_RELEASE_URL = "https://github.com/xpander-ai/releases/actions/workflows/new-release.yml"
MAX_CHANGES = 6


def warn(message):
    print(f"::warning::{message}")


def slack(method, payload):
    """Call a Slack Web API method; returns the response or None, never raises."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        warn("SLACK_BOT_TOKEN not set - Slack update skipped")
        return None
    request = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read())
    except Exception as exc:  # noqa: BLE001 - Slack must never fail a release job
        warn(f"Slack {method} failed: {exc}")
        return None
    if not body.get("ok"):
        warn(f"Slack {method} returned {body.get('error')}")
        return None
    return body


def image_changes(manifest, previous):
    """List [name, old, new] for every image whose tag differs from the previous approved set."""
    old = (previous or {}).get("images", {})
    changes = []
    for name, entry in sorted(manifest.get("images", {}).items()):
        before = old.get(name, {}).get("tag")
        if before != entry.get("tag"):
            changes.append([name, before, entry.get("tag")])
    return changes


def headline(state):
    stages = state["stages"]
    rid = f"`{state['release_id']}`"
    if state.get("superseded_by"):
        return f"⏭️ *Superseded* {rid} by `{state['superseded_by']}`"
    if stages["released"] == "done":
        return f"📣 *Released `{state.get('release_tag')}`* {rid} · step 5/5"
    if stages["approved"] == "done":
        return f"🚀 *Approved* {rid} · step 4/5"
    for step, stage in ((3, "production"), (2, "staging")):
        if stages[stage] == "failed":
            return f"❌ *Failed on {LABELS[stage].lower()}* {rid} · step {step}/5"
        if stages[stage] == "running":
            return f"⏳ *Testing on {LABELS[stage].lower()}* {rid} · step {step}/5"
    if stages["staging"] == "done":
        return f"⏳ *Waiting for production* {rid} · step 3/5"
    return f"🧪 *New candidate* {rid} · step 1/5"


def render(state):
    """Render the card text from its state; at most four lines."""
    changes = state.get("changes", [])
    if changes:
        shown = [f"{name} `{old or '-'}→{new}`" for name, old, new in changes[:MAX_CHANGES]]
        more = f" +{len(changes) - MAX_CHANGES} more" if len(changes) > MAX_CHANGES else ""
        facts = f"{len(changes)}/{state.get('total', len(changes))} images changed: " + " · ".join(shown) + more
    else:
        facts = "no image changes since the last approved set"
    progress = " · ".join(f"{MARKS[state['stages'][s]]} {LABELS[s]}" for s in STAGES)
    links = state.get("links", {})
    names = (("manifest", "Manifest"), ("diff", "Diff"), ("build", "Build"), ("staging", "Staging run"), ("production", "Production run"))
    link_line = " · ".join(f"<{links[key]}|{label}>" for key, label in names if links.get(key))
    lines = [headline(state), f"`main@{state['sha'][:7]}` · {facts}", progress]
    if link_line:
        lines.append(link_line)
    return "\n".join(lines)


def load(path):
    with open(path) as handle:
        return json.load(handle)


def save(path, state):
    with open(path, "w") as handle:
        json.dump(state, handle, indent=2)
        handle.write("\n")


def update_card(state):
    if state.get("ts"):
        slack("chat.update", {"channel": state["channel"], "ts": state["ts"], "text": render(state)})


def reply(state, text, broadcast=False):
    if state.get("ts"):
        slack("chat.postMessage", {"channel": state["channel"], "thread_ts": state["ts"], "text": text, "reply_broadcast": broadcast})


def cmd_candidate(args):
    manifest = load(args.manifest)
    previous = load(args.previous) if args.previous else None
    rid = args.release_id
    state = {
        "channel": CHANNEL,
        "ts": None,
        "release_id": rid,
        "sha": args.sha,
        "changes": image_changes(manifest, previous),
        "total": len(manifest.get("images", {})),
        "stages": {"candidate": "done", "staging": "pending", "production": "pending", "approved": "pending", "released": "pending"},
        "links": {
            "manifest": f"https://github.com/xpander-ai/release-manifests/releases/tag/{rid}",
            "build": args.build_url,
            "diff": args.diff_url,
        },
        "release_tag": None,
    }
    posted = slack("chat.postMessage", {"channel": CHANNEL, "text": render(state)})
    if posted:
        state["ts"] = posted["ts"]
    save(args.out, state)
    print(state["ts"] or "")


def cmd_stage(args):
    state = load(args.state)
    state["stages"][args.stage] = args.status
    if args.run_url:
        state["links"][args.stage] = args.run_url
    save(args.state, state)
    update_card(state)
    if args.status == "failed":
        env = "acme-staging" if args.stage == "staging" else "acme"
        run = f" · <{args.run_url}|Failed run>" if args.run_url else ""
        reply(state, f"❌ *{LABELS[args.stage]} failed* ({env}) · current `latest` unchanged{run}")


def cmd_approved(args):
    state = load(args.state)
    for stage in ("staging", "production", "approved"):
        state["stages"][stage] = "done"
    save(args.state, state)
    update_card(state)
    reply(state, f"🚀 *Approved for production* · now `latest` for new syncs · not announced yet · <{NEW_RELEASE_URL}|New release>", broadcast=True)


def cmd_superseded(args):
    state = load(args.state)
    state["superseded_by"] = args.by
    for stage in ("staging", "production", "approved", "released"):
        if state["stages"][stage] in ("pending", "running"):
            state["stages"][stage] = "skipped"
    save(args.state, state)
    update_card(state)


def cmd_released(args):
    state = load(args.state)
    state["stages"]["released"] = "done"
    state["release_tag"] = args.tag
    save(args.state, state)
    update_card(state)


def release_message(tag, title, airgap, hybrid, images, action_required, whats_new, url, actor):
    """Render the channel announcement for a published release."""
    versions = []
    if airgap:
        versions.append(f"Airgap `{airgap}`")
    if hybrid:
        versions.append(f"Hybrid `{hybrid}`")
    if images:
        versions.append(f"Images `{images}`")
    if action_required:
        versions.append("⚠️ action required")
    lines = [f"📣 *Released* `{tag}` · {title} · step 5/5", " · ".join(versions)]
    items = [item.strip() for item in (whats_new or "").split(";;") if item.strip()]
    if items:
        lines.append(" · ".join(items))
    lines.append(f"<{url}|Release notes> · by {actor}")
    return "\n".join(lines)


def cmd_release_message(args):
    text = release_message(args.tag, args.title, args.airgap, args.hybrid, args.images,
                           args.action_required == "true", args.whats_new, args.url, args.actor)
    slack("chat.postMessage", {"channel": CHANNEL, "text": text})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("candidate")
    p.add_argument("--manifest", required=True)
    p.add_argument("--previous", default="")
    p.add_argument("--release-id", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--build-url", default="")
    p.add_argument("--diff-url", default="")
    p.add_argument("--out", default="slack.json")
    p.set_defaults(func=cmd_candidate)
    p = sub.add_parser("stage")
    p.add_argument("--state", required=True)
    p.add_argument("--stage", required=True, choices=("staging", "production"))
    p.add_argument("--status", required=True, choices=("running", "done", "failed"))
    p.add_argument("--run-url", default="")
    p.set_defaults(func=cmd_stage)
    p = sub.add_parser("approved")
    p.add_argument("--state", required=True)
    p.set_defaults(func=cmd_approved)
    p = sub.add_parser("superseded")
    p.add_argument("--state", required=True)
    p.add_argument("--by", required=True)
    p.set_defaults(func=cmd_superseded)
    p = sub.add_parser("released")
    p.add_argument("--state", required=True)
    p.add_argument("--tag", required=True)
    p.set_defaults(func=cmd_released)
    p = sub.add_parser("release-message")
    for name in ("--tag", "--title", "--url", "--actor"):
        p.add_argument(name, required=True)
    for name in ("--airgap", "--hybrid", "--images", "--whats-new"):
        p.add_argument(name, default="")
    p.add_argument("--action-required", default="false", choices=("true", "false"))
    p.set_defaults(func=cmd_release_message)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:  # noqa: BLE001 - Slack bookkeeping must never fail a release job
        warn(f"release_slack {args.command} failed: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
