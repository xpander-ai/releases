# AGENTS.md

Instructions for coding agents working in this repository.

This repository holds the release notes for the xpander.ai self-hosted platform (air-gapped and hybrid installs). There is no product source code here. Each release is a GitHub release tagged `vYYYY.MM.DD` with its `release-manifest.json` attached; the `latest` release points at the current image set. `.github/workflows/on-publish.yml` runs `.github/scripts/on_publish.py` to finish a release after a person publishes it. See `README.md` for the publishing steps.

This repository is public. Never commit or write internal hostnames, internal channel names, secret names, people's names or customer details into files, release notes or workflow logs.

## Security and CI rules

### Release rules

- Releases are immutable once published; never replace a published release's assets. The only moving asset is the `latest` release's manifest, and only `on_publish.py` moves it. The approved `release-manifest.json` is attached to the draft before publish. `on_publish.py` only checks it (it uploads one only to a release that has none); if the attached manifest differs from the approved image set, it fails and does not move `latest`.
- This repo is public: workflows trigger only on `release: published` / `workflow_dispatch`, never on pull requests. Blacksmith runners.
- Release notes name fixed CVEs and every new image or chart repo (customers mirror and scan them, and their pull tokens must cover them).
- Install commands in notes use placeholders for tokens and pin chart versions and manifest URLs to this release.

### Release and deploy

- A merge is not a customer release. Publishing to customers (images `:latest`, charts, packages, release feeds) is an explicit dispatch behind its own approval.
- Build once and promote the same digest from staging to production.
- Published versions and release tags are immutable; never overwrite. Check the registry before pushing.
- After every deploy or publish, a live check proves the target serves exactly this version (and that refusal paths still refuse).
