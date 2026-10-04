"""Resolve versions and render the notes for the New release workflow."""

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request

MANIFESTS = "xpander-ai/release-manifests"
FEED = "xpander-ai/releases"
HYBRID_INDEX = "https://charts.xpander.ai/index.yaml"
AIRGAP_TAGS_API = "https://api.github.com/repos/xpander-ai/helm-charts/git/matching-refs/tags/airgap-chart-v"
VERIFY_GUIDE = "https://pages.xpander.ai/airgap-verification-guide"
RELEASE_ID = re.compile(r"onprem-[1-9][0-9]*")
SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")
PREVIEW_START = "<!-- preview -->"
PREVIEW_END = "<!-- /preview -->"


class ReleaseError(Exception):
    """A problem the person running the workflow can fix from the form."""


def fetch(url, token=""):
    headers = {"User-Agent": "xpander-new-release"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return response.read().decode()


def semver_key(version):
    match = SEMVER.fullmatch(version)
    return tuple(int(part) for part in match.groups()) if match else None


def newest(versions):
    """Highest plain x.y.z version; prereleases and junk are ignored."""
    ranked = [(semver_key(v), v) for v in versions if semver_key(v)]
    if not ranked:
        raise ReleaseError("no published versions found")
    return max(ranked)[1]


def hybrid_versions(index_text):
    """Versions of the `xpander` chart listed in a Helm repository index."""
    try:
        import yaml
    except ImportError:
        yaml = None
    if yaml:
        entries = (yaml.safe_load(index_text) or {}).get("entries", {}).get("xpander", [])
        return [str(entry.get("version", "")) for entry in entries]
    return re.findall(r"^    version: (\S+)$", index_text, flags=re.M)


def airgap_versions(refs):
    """Versions from helm-charts `airgap-chart-v*` tag refs."""
    prefix = "refs/tags/airgap-chart-v"
    return [ref["ref"][len(prefix):] for ref in refs if ref.get("ref", "").startswith(prefix)]


def release_tag(date):
    return f"v{date:%Y.%m.%d}"


def default_title(date):
    return f"xpander.ai Self-Hosted · {date:%B} {date.day}, {date:%Y}"


def parse_date(value, today):
    if not value.strip():
        return today
    try:
        return dt.date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ReleaseError(f"Release date '{value}' is not YYYY-MM-DD") from exc


def items(value):
    return [item.strip() for item in (value or "").split(";;") if item.strip()]


def check_manifest(manifest, release_id):
    """Only an image set that passed staging and production verification may ship."""
    if manifest.get("channel") != "production":
        raise ReleaseError(f"{release_id} is not approved for production yet (channel {manifest.get('channel')!r})")
    if manifest.get("release_id") != release_id:
        raise ReleaseError(f"{release_id}: manifest names {manifest.get('release_id')!r}")
    if not manifest.get("images"):
        raise ReleaseError(f"{release_id}: manifest lists no images")
    return manifest


def split_front_matter(text):
    """Return (front matter dict, body) for a notes file; front matter is optional."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return meta, text[end + 5:].lstrip("\n")


def airgap_upgrade(tag, chart):
    manifest_url = f"https://github.com/{FEED}/releases/download/{tag}/release-manifest.json"
    latest_url = f"https://github.com/{MANIFESTS}/releases/download/latest/release-manifest.json"
    return f"""Replace `<namespace>`, `<your-registry>` and `<xpander-token>` (from your license email). Every command works from a terminal or a CI/CD pipeline.

**1. Check the nodes.** Every node must show kubelet `v1.33` or later, kernel `6.3` or later, and containerd `2.0` or later. Upgrade any node that doesn't before you continue.

```bash
kubectl get nodes -o custom-columns=NODE:.metadata.name,KUBELET:.status.nodeInfo.kubeletVersion,KERNEL:.status.nodeInfo.kernelVersion,RUNTIME:.status.nodeInfo.containerRuntimeVersion
```

**2. Download the release.** The image set of this release is attached to it as `release-manifest.json`. The newest approved image set is always at `{latest_url}`.

```bash
curl -fsSL https://charts.xpander.ai/image_sync.sh -o image_sync.sh
curl -fsSL {manifest_url} -o release-manifest.json
```

**3. Mirror the images.** This writes `pins.yaml`, which pins every image to this release.

```bash
bash image_sync.sh --source-user xpanderaihub --source-token <xpander-token> \\
  --dest <your-registry> --release-manifest release-manifest.json --manifest-out pins.yaml
```

**4. Upgrade.**

```bash
helm registry login registry-1.docker.io -u xpanderaihub -p <xpander-token>
helm upgrade xpander oci://registry-1.docker.io/xpanderaihub/xpander-airgap --version {chart} \\
  -n <namespace> --reuse-values -f pins.yaml --wait --timeout 30m
```

**5. Verify.** Run the [verification guide]({VERIFY_GUIDE})."""


def hybrid_upgrade(chart):
    return f"""Replace `<namespace>` with the namespace xpander runs in.

**1. Update the chart repository.**

```bash
helm repo add xpander https://charts.xpander.ai 2>/dev/null || true
helm repo update xpander
```

**2. Upgrade.**

```bash
helm upgrade xpander xpander/xpander --version {chart} -n <namespace> --reuse-values --wait --timeout 30m
```

**3. Verify.** Every pod must be `Running` or `Completed`.

```bash
kubectl -n <namespace> get pods
```"""


def preview_block(resolved):
    """The preview-only note listing what the workflow resolved; publish strips it."""
    lines = "\n".join(f"> - {line}" for line in resolved)
    return f"{PREVIEW_START}\n> [!NOTE]\n> **Preview.** This block is removed when you publish. Resolved:\n{lines}\n{PREVIEW_END}\n\n"


def render(ctx):
    """Render the release notes body in the fixed release structure."""
    parts = []
    if ctx.get("action_required"):
        note = ctx.get("action_note") or "Run every step below, in order."
        parts.append(f"> [!IMPORTANT]\n> **Action required.** {note}")
    facts = []
    if ctx.get("airgap"):
        facts.append(f"**Air-gapped Helm chart:** `xpander-airgap` `{ctx['airgap']}`")
    if ctx.get("hybrid"):
        facts.append(f"**Hybrid Helm chart:** `xpander` `{ctx['hybrid']}`")
    if ctx.get("image_set"):
        facts.append(f"**Image set:** [`{ctx['image_set']}`](https://github.com/{MANIFESTS}/releases/tag/{ctx['image_set']})")
    if ctx.get("sha"):
        facts.append(f"**Platform build:** `{ctx['sha'][:12]}`")
    parts.append(" · ".join(facts))
    if ctx.get("whats_new"):
        parts.append("## What's new\n\n" + "\n".join(f"- {item}" for item in ctx["whats_new"]))
    if ctx.get("security"):
        parts.append("## Security\n\n" + "\n".join(f"- {item}" for item in ctx["security"]))
    upgrade = ["## Upgrade"]
    if ctx.get("extra_upgrade_notes"):
        upgrade.append(f"**Before you start.** {ctx['extra_upgrade_notes']}")
    both = ctx.get("airgap") and ctx.get("hybrid")
    if ctx.get("airgap"):
        upgrade.append(("### Air-gapped installs\n\n" if both else "") + airgap_upgrade(ctx["tag"], ctx["airgap"]))
    if ctx.get("hybrid"):
        upgrade.append(("### Hybrid installs\n\n" if both else "") + hybrid_upgrade(ctx["hybrid"]))
    parts.append("\n\n".join(upgrade))
    return "\n\n".join(parts) + "\n"


def notes_file_text(tag, title, body):
    """The archived notes file: front matter plus the published body."""
    return f"---\ntag: {tag}\ntitle: {title}\n---\n{body}"


def resolve_image_set(choice):
    """Download the approved manifest for `latest-approved` or an explicit onprem-<run> id."""
    choice = (choice or "").strip() or "latest-approved"
    if choice == "latest-approved":
        pointer = json.loads(fetch(f"https://github.com/{MANIFESTS}/releases/download/latest/release-manifest.json"))
        release_id = pointer.get("release_id", "")
        label = f"`{release_id}` (newest approved)"
    else:
        release_id, label = choice, f"`{choice}` (chosen)"
    if not RELEASE_ID.fullmatch(release_id):
        raise ReleaseError(f"Image set '{choice}' must be latest-approved or onprem-<run>")
    url = f"https://github.com/{MANIFESTS}/releases/download/{release_id}/approved-release-manifest.json"
    try:
        raw = fetch(url)
    except Exception as exc:  # noqa: BLE001
        raise ReleaseError(f"{release_id} has no approved manifest yet; it has not passed staging and production") from exc
    return release_id, label, check_manifest(json.loads(raw), release_id), raw


def prepare(env, out_dir, today):
    """Resolve every input, then write notes and the manifest into out_dir; returns the outputs."""
    kind = env.get("RELEASE_TYPE", "both")
    if kind not in ("airgap", "hybrid", "both"):
        raise ReleaseError(f"Release type '{kind}' must be airgap, hybrid or both")
    front, override = {}, None
    if env.get("NOTES_FILE", "").strip():
        path = env["NOTES_FILE"].strip()
        if not os.path.isfile(path):
            raise ReleaseError(f"Notes file '{path}' does not exist on main")
        with open(path) as handle:
            front, override = split_front_matter(handle.read())
    date = parse_date(env.get("RELEASE_DATE", ""), today)
    tag = front.get("tag") if front.get("tag") and not env.get("RELEASE_DATE", "").strip() else release_tag(date)
    title = env.get("TITLE", "").strip() or front.get("title") or default_title(date)
    resolved = [f"Tag `{tag}`"]
    ctx = {"tag": tag}
    if kind in ("airgap", "both"):
        airgap = env.get("AIRGAP_CHART", "").strip()
        if airgap:
            resolved.append(f"Air-gapped chart `{airgap}` (chosen)")
        else:
            try:
                refs = json.loads(fetch(AIRGAP_TAGS_API, env.get("CHARTS_TOKEN", "")))
            except Exception as exc:  # noqa: BLE001
                raise ReleaseError("Could not list air-gapped chart versions; type the version in 'Airgap chart version'") from exc
            airgap = newest(airgap_versions(refs))
            resolved.append(f"Air-gapped chart `{airgap}` (newest)")
        if not semver_key(airgap):
            raise ReleaseError(f"Air-gapped chart version '{airgap}' is not x.y.z")
        release_id, label, manifest, raw = resolve_image_set(env.get("IMAGE_SET", ""))
        resolved.append(f"Image set {label}, built from `main@{manifest['source']['sha'][:7]}`")
        with open(os.path.join(out_dir, "release-manifest.json"), "w") as handle:
            handle.write(raw)
        ctx.update(airgap=airgap, image_set=release_id, sha=manifest["source"]["sha"])
    if kind in ("hybrid", "both"):
        hybrid = env.get("HYBRID_CHART", "").strip()
        if hybrid:
            resolved.append(f"Hybrid chart `{hybrid}` (chosen)")
        else:
            hybrid = newest(hybrid_versions(fetch(HYBRID_INDEX)))
            resolved.append(f"Hybrid chart `{hybrid}` (newest)")
        if not semver_key(hybrid):
            raise ReleaseError(f"Hybrid chart version '{hybrid}' is not x.y.z")
        ctx["hybrid"] = hybrid
    ctx.update(
        action_required=env.get("ACTION_REQUIRED", "false") == "true",
        action_note=env.get("ACTION_NOTE", "").strip(),
        whats_new=items(env.get("WHATS_NEW", "")),
        security=items(env.get("SECURITY", "")),
        extra_upgrade_notes=env.get("EXTRA_UPGRADE_NOTES", "").strip(),
    )
    public = override if override is not None else render(ctx)
    preview = preview_block(resolved) + public
    for name, text in (("notes-preview.md", preview), ("notes.md", public), ("notes-file.md", notes_file_text(tag, title, public))):
        with open(os.path.join(out_dir, name), "w") as handle:
            handle.write(text)
    return {
        "tag": tag,
        "title": title,
        "date": date.isoformat(),
        "kind": kind,
        "airgap": ctx.get("airgap", ""),
        "hybrid": ctx.get("hybrid", ""),
        "image_set": ctx.get("image_set", ""),
        "whats_new": ";;".join(ctx["whats_new"]),
        "action_required": "true" if ctx["action_required"] else "false",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    try:
        outputs = prepare(os.environ, args.out, dt.datetime.now(dt.timezone.utc).date())
    except ReleaseError as exc:
        print(f"::error::{exc}")
        return 1
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as handle:
        for key, value in outputs.items():
            handle.write(f"{key}={value}\n")
    print(json.dumps(outputs, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
