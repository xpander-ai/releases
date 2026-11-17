# CLAUDE.md

All rules for this repo live in [`AGENTS.md`](./AGENTS.md). Read it before changing anything here.

## Security and CI rules

Before touching auth, outbound requests, secrets, API responses, webhooks, database grants, Dockerfiles or anything under `.github/`, read `AGENTS.md` → "Security and CI rules" and follow its checklist. These rules are binding; a PR that breaks one is not ready for review.
