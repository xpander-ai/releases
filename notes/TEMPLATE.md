---
tag: vYYYY.MM.DD
title: xpander.ai Self-Hosted — <Month D, YYYY>
---
xpander.ai Self-Hosted was released on **<Month D, YYYY>**. <One or two sentences on the headline changes.>

| | |
|---|---|
| **Helm chart** | `<chart version>` |
| **Platform build** | [`<full sha>`](https://github.com/xpander-ai/releases/releases/tag/release-<short sha>) |
| **Breaking changes** | <None / Yes, see below> |
| **Upgrade effort** | <e.g. Chart upgrade + rolling restart> |

<!-- Only if there are breaking changes. Put it above everything else so no one misses it.
> [!CAUTION]
> **Breaking change.** <What breaks, who is affected, and what to do before upgrading.>
-->

## New features and improvements

### <Feature name>

<What changed and why it matters to the operator or user. Link to docs where they exist: [Learn more >](https://docs.xpander.ai/...)>

### Other improvements

- <Smaller item>

## Security

<!-- Permission changes, CVE fixes, hardening. Delete the section if there is nothing to report. -->

## Known issues

<!-- Delete the section if there is nothing to report. -->

## Upgrading

1. <Step>

If you use Helm (log in with the registry token provided with your license):

```bash
helm registry login docker.io
helm upgrade xpander oci://docker.io/xpanderaihub/xpander-airgap -n <namespace> --reuse-values --version <chart version>
kubectl -n <namespace> rollout restart deployment,statefulset
```

## Artifacts

- **Helm chart**: [`<chart version>` release](https://github.com/xpander-ai/releases/releases/tag/<chart tag>)
- **Platform images**: [Platform release <date>](https://github.com/xpander-ai/releases/releases/tag/release-<short sha>)
