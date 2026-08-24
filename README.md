# xpander.ai Releases

Release feed for the xpander.ai self-hosted (on-prem) platform: Docker images and the Helm chart.

Every release on this repository is published automatically by our CI when new artifacts ship. There is no source code here — this repository exists so you can subscribe to release notifications.

## Subscribe

- **GitHub notifications**: click **Watch → Custom → Releases** on this repository. You'll get an email and a GitHub notification for every new release.
- **RSS / Atom**: subscribe to [`https://github.com/xpander-ai/releases/releases.atom`](https://github.com/xpander-ai/releases/releases.atom) with any feed reader, Slack `/feed`, or automation of your choice.

## What gets published here

| Release prefix | What it covers |
|---|---|
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

## Contributing

This repository does not accept contributions — issues, discussions, and pull requests are not monitored here. For support, contact us through your usual xpander.ai support channel or [xpander.ai](https://xpander.ai).
