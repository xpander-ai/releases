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
| Current image set (what `install.sh` and `image_sync.sh` download) | the `latest` release here: `https://github.com/xpander-ai/releases/releases/download/latest/release-manifest.json` |
| Hybrid Helm chart | [charts.xpander.ai](https://charts.xpander.ai) |
| Docker images | [hub.docker.com/u/xpanderaihub](https://hub.docker.com/u/xpanderaihub) |

## Publishing a release (xpander team)

A draft appears automatically after each approved image set; edit it and click **Publish**.

1. Open **Releases**. The bot keeps one draft up to date: the image set, the chart versions and a folded list of the pull requests merged since the last release.
2. Edit it in GitHub's editor. Write **What's new** and **Security** for customers, using the PR list as a source. Delete the upgrade block that doesn't apply.
   - No bot draft? Click **Draft a new release**, tag it `vYYYY.MM.DD` and paste [`notes/TEMPLATE.md`](notes/TEMPLATE.md).
   - **Image set**: keep the `Image set: onprem-<run>` line, or leave it out to ship the newest approved set.
   - **Hybrid only**: write `Hybrid only` anywhere in the notes; no image set is attached.
3. Save the draft and check the preview. Only the xpander team sees drafts.
4. Click **Publish**. The **On publish** workflow then:
   - checks the image set passed staging and production. If not, it turns the release back into a draft and says why in #xpander-releases.
   - attaches `release-manifest.json` to the release.
   - moves **Current image set** to it. It never moves it to an older set on its own.
   - removes the bot's markers and PR list, keeps the release marked Latest, and posts the announcement in #xpander-releases.

**Fix a typo:** edit the published release on GitHub. Nothing runs again.

**Roll back the image set:** Actions → **On publish** → Run workflow, with the older release's tag and **move_current** checked. Without **move_current**, a re-run only re-attaches the manifest and re-posts the announcement.

## Contributing

This repository doesn't accept issues or pull requests. For support, contact us through your usual xpander.ai support channel or [xpander.ai](https://xpander.ai).
