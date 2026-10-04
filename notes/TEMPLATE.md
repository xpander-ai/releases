<!-- Copy everything below this comment into Releases → Draft a new release. Tag: vYYYY.MM.DD.
     Image set: leave the line out to ship the newest approved set. For a hybrid-only release,
     write "Hybrid only" anywhere in the notes and drop the air-gapped block. Delete what doesn't apply. -->
> [!IMPORTANT]
> **Action required.** <What the operator must do before or during the upgrade.>

Image set: [`onprem-<run>`](https://github.com/xpander-ai/release-manifests/releases/tag/onprem-<run>)

**Air-gapped Helm chart:** `xpander-airgap` `<version>` · **Hybrid Helm chart:** `xpander` `<version>`

## What's new

- <Change, written for the customer.>

## Security

- <Hardening or fix.>

## Upgrade

### Air-gapped installs

Replace `<namespace>`, `<your-registry>` and `<xpander-token>` (from your license email). Every command works from a terminal or a CI/CD pipeline.

**1. Download the release.**

```bash
curl -fsSL https://charts.xpander.ai/image_sync.sh -o image_sync.sh
curl -fsSL https://github.com/xpander-ai/releases/releases/download/vYYYY.MM.DD/release-manifest.json -o release-manifest.json
```

**2. Mirror the images.** This writes `pins.yaml`, which pins every image to this release.

```bash
bash image_sync.sh --source-user xpanderaihub --source-token <xpander-token> \
  --dest <your-registry> --release-manifest release-manifest.json --manifest-out pins.yaml
```

**3. Upgrade.**

```bash
helm registry login registry-1.docker.io -u xpanderaihub -p <xpander-token>
helm upgrade xpander oci://registry-1.docker.io/xpanderaihub/xpander-airgap --version <version> \
  -n <namespace> --reuse-values -f pins.yaml --wait --timeout 30m
```

Then run the [verification guide](https://pages.xpander.ai/airgap-verification-guide).

### Hybrid installs

```bash
helm repo add xpander https://charts.xpander.ai && helm repo update xpander
helm upgrade xpander xpander/xpander --version <version> -n <namespace> --reuse-values --wait --timeout 30m
```
