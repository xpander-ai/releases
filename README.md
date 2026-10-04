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
   - No bot draft? [**Draft a new release from the template**](https://github.com/xpander-ai/releases/releases/new?tag=vYYYY.MM.DD&title=xpander.ai%20Self-Hosted%20%C2%B7%20Month%20D%2C%20YYYY&body=%3E%20%5B%21IMPORTANT%5D%0A%3E%20%2A%2AAction%20required.%2A%2A%20%3CWhat%20the%20operator%20must%20do%20before%20or%20during%20the%20upgrade.%3E%0A%0AImage%20set%3A%20%5B%60onprem-%3Crun%3E%60%5D%28https%3A%2F%2Fgithub.com%2Fxpander-ai%2Frelease-manifests%2Freleases%2Ftag%2Fonprem-%3Crun%3E%29%0A%0A%2A%2AAir-gapped%20Helm%20chart%3A%2A%2A%20%60xpander-airgap%60%20%60%3Cversion%3E%60%20%C2%B7%20%2A%2AHybrid%20Helm%20chart%3A%2A%2A%20%60xpander%60%20%60%3Cversion%3E%60%0A%0A%23%23%20What%27s%20new%0A%0A-%20%3CChange%2C%20written%20for%20the%20customer.%3E%0A%0A%23%23%20Security%0A%0A-%20%3CHardening%20or%20fix.%3E%0A%0A%23%23%20Upgrade%0A%0A%23%23%23%20Air-gapped%20installs%0A%0AReplace%20%60%3Cnamespace%3E%60%2C%20%60%3Cyour-registry%3E%60%20and%20%60%3Cxpander-token%3E%60%20%28from%20your%20license%20email%29.%20Every%20command%20works%20from%20a%20terminal%20or%20a%20CI%2FCD%20pipeline.%0A%0A%2A%2A1.%20Download%20the%20release.%2A%2A%0A%0A%60%60%60bash%0Acurl%20-fsSL%20https%3A%2F%2Fcharts.xpander.ai%2Fimage_sync.sh%20-o%20image_sync.sh%0Acurl%20-fsSL%20https%3A%2F%2Fgithub.com%2Fxpander-ai%2Freleases%2Freleases%2Fdownload%2FvYYYY.MM.DD%2Frelease-manifest.json%20-o%20release-manifest.json%0A%60%60%60%0A%0A%2A%2A2.%20Mirror%20the%20images.%2A%2A%20This%20writes%20%60pins.yaml%60%2C%20which%20pins%20every%20image%20to%20this%20release.%0A%0A%60%60%60bash%0Abash%20image_sync.sh%20--source-user%20xpanderaihub%20--source-token%20%3Cxpander-token%3E%20%5C%0A%20%20--dest%20%3Cyour-registry%3E%20--release-manifest%20release-manifest.json%20--manifest-out%20pins.yaml%0A%60%60%60%0A%0A%2A%2A3.%20Upgrade.%2A%2A%0A%0A%60%60%60bash%0Ahelm%20registry%20login%20registry-1.docker.io%20-u%20xpanderaihub%20-p%20%3Cxpander-token%3E%0Ahelm%20upgrade%20xpander%20oci%3A%2F%2Fregistry-1.docker.io%2Fxpanderaihub%2Fxpander-airgap%20--version%20%3Cversion%3E%20%5C%0A%20%20-n%20%3Cnamespace%3E%20--reuse-values%20-f%20pins.yaml%20--wait%20--timeout%2030m%0A%60%60%60%0A%0AThen%20run%20the%20%5Bverification%20guide%5D%28https%3A%2F%2Fpages.xpander.ai%2Fairgap-verification-guide%29.%0A%0A%23%23%23%20Hybrid%20installs%0A%0A%60%60%60bash%0Ahelm%20repo%20add%20xpander%20https%3A%2F%2Fcharts.xpander.ai%20%26%26%20helm%20repo%20update%20xpander%0Ahelm%20upgrade%20xpander%20xpander%2Fxpander%20--version%20%3Cversion%3E%20-n%20%3Cnamespace%3E%20--reuse-values%20--wait%20--timeout%2030m%0A%60%60%60%0A): opens the editor prefilled with [`notes/TEMPLATE.md`](notes/TEMPLATE.md); set the tag and replace the placeholders.
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
