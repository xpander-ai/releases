# xpander.ai Releases

Release feed for the xpander.ai self-hosted (on-prem) platform: Docker images and the Helm chart.

Artifact releases (images and charts) are published automatically by our CI when new artifacts ship. Release notes are written, reviewed, and published by the xpander.ai team. There is no source code here — this repository exists so you can subscribe to release notifications.

## Subscribe

- **GitHub notifications**: click **Watch → Custom → Releases** on this repository. You'll get an email and a GitHub notification for every new release.
- **RSS / Atom**: subscribe to [`https://github.com/xpander-ai/releases/releases.atom`](https://github.com/xpander-ai/releases/releases.atom) with any feed reader, Slack `/feed`, or automation of your choice.

## What gets published here

| Release prefix | What it covers |
|---|---|
| `vYYYY.MM.DD` | **Release notes**: new features, security changes, upgrade steps. Start here. |
| `images-*` | On-prem platform service images (`xpanderaihub/*` on Docker Hub) |
| `agent-images-*` | Agent container images (sandbox and scaffolds) |
| `chart-v*` | The `xpander` Helm chart, served from [charts.xpander.ai](https://charts.xpander.ai) |

Each release lists the exact image versions published, with links to Docker Hub.

## Artifact locations

- **Docker images**: [hub.docker.com/u/xpanderaihub](https://hub.docker.com/u/xpanderaihub)
- **Helm chart**:

  ```bash
  helm repo add xpander https://charts.xpander.ai
  helm repo update
  ```

## Writing release notes (xpander.ai team)

Release notes are written by hand and published by hand. Nothing goes out automatically.

1. Copy [`notes/TEMPLATE.md`](notes/TEMPLATE.md) to `notes/<YYYY-MM-DD>.md` and fill it in with the approved notes and upgrade instructions.
2. Open a PR. A reviewer checks the wording, versions, and commands.
3. When the PR merges, the [Draft release notes](.github/workflows/publish-notes.yml) workflow creates a **draft** release.
4. Open the draft under **Releases**, check how it renders, tick **Set as the latest release**, and click **Publish**.

## Contributing

This repository does not accept contributions — issues, discussions, and pull requests are not monitored here. For support, contact us through your usual xpander.ai support channel or [xpander.ai](https://xpander.ai).
