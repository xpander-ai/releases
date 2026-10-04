# xpander.ai Releases

Release notes for the xpander.ai self-hosted platform: what's new, security changes and upgrade steps, for both air-gapped and hybrid installs. There is no source code here.

## Subscribe

- **GitHub notifications**: click **Watch → Custom → Releases**. You get one email per release.
- **RSS / Atom**: [`https://github.com/xpander-ai/releases/releases.atom`](https://github.com/xpander-ai/releases/releases.atom), in any feed reader or Slack `/feed`.

## Where things live

| What | Where |
|---|---|
| Release notes | [Releases](https://github.com/xpander-ai/releases/releases) on this repository, tagged `vYYYY.MM.DD` |
| Image set of a release | `release-manifest.json`, attached to that release |
| Newest approved image set | [`xpander-ai/release-manifests`](https://github.com/xpander-ai/release-manifests): `https://github.com/xpander-ai/release-manifests/releases/download/latest/release-manifest.json` |
| Hybrid Helm chart | [charts.xpander.ai](https://charts.xpander.ai) |
| Docker images | [hub.docker.com/u/xpanderaihub](https://hub.docker.com/u/xpanderaihub) |

## Publishing a release (xpander team)

Releases are published by hand, only through the **New release** workflow. Nothing else writes here.

1. Go to **Actions → New release → Run workflow**.
2. Fill in the form:
   - **Release type**: `both`, `airgap` or `hybrid`. This decides which upgrade steps the notes include.
   - **Release date**: blank means today. The tag becomes `vYYYY.MM.DD`.
   - **Air-gapped chart / Hybrid chart / Image set**: leave blank for the newest. The image set must have passed staging and production verification, or the run stops.
   - **Action required**, **What's new**, **Security**: separate list items with `;;`.
   - **Notes file override**: only for notes the form can't express. Start from [`notes/TEMPLATE.md`](notes/TEMPLATE.md).
3. Run it with **mode: preview**. It creates a draft only the xpander team can see, with a note at the top listing every version it picked. Check the draft under **Releases**.
4. Run it again with the same inputs and **mode: publish**. The release goes public and is marked Latest, the image set is attached, the notes are archived on the `notes-archive` branch, and #xpander-releases gets the announcement.

**Fix a typo:** run publish again with the same date. It edits the release in place and doesn't announce it again.

**Pull back a bad image set:** run publish again with the same date and the previous `onprem-<run>` in **Image set**, then tell customers to sync again.

## Contributing

This repository doesn't accept issues or pull requests. For support, contact us through your usual xpander.ai support channel or [xpander.ai](https://xpander.ai).
