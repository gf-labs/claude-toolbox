# Git Management Policy (generic default)

> Bundled default the `git-policy-auditor` uses when no policy is configured via
> `CLAUDE_TOOLBOX_GIT_POLICY`. It names no repositories — a repo's tier is set by
> the question **"does anyone install or depend on this?"**, never by its folder.
> Point the env var at your own policy to override this.

## Tiers

- **Distributed** — anyone installs or depends on it. Full Git Flow + SemVer + PRs + CI/CD.
- **Rolling registry** — distributed, but a catalog with no version of its own; consumers always want latest. No Git Flow/SemVer/CD; CI = validation only; work merges to the default branch directly.
- **Personal** — working/config repos nobody installs as a versioned product. Default branch + short `feature/*`; tag only to mark a milestone; optional lint CI.
- **Throwaway** — scratch/experiments. No policy.

## Distributed tier

### Branches (Git Flow)
- `main` — stable releases only; the default branch; each release is an annotated tag `vX.Y.Z`.
- `develop` — daily integration; carries `X.Y.Z-dev` (non-authoritative).
- `feature/*` → squash-merge into `develop`.
- `release/*` → betas/RCs tagged here (`-beta.N`/`-rc.N`); merges into `main`.
- `hotfix/*` → branches from `main`; merges into `main` and back into `develop` (or the open `release/*`).
- Drift guardrails: delete + back-merge `release/*`/`hotfix/*` immediately. Every `main` commit stays reachable from `develop` or an open `release/*` (`git log develop..main` is empty once back-merged).

### Versioning
- Semantic Versioning. Pre-1.0 (`0.y.z`): a breaking change bumps MINOR, a feature or fix bumps PATCH. `0.x → 1.0.0` is the stability commitment.
- **Manifest ↔ tag must match on `main`** (CI-gated): the manifest version equals the tag pointing at `main`'s HEAD. No tagless bumps left on `main`. Tag the release-branch tip before merge so tag and manifest arrive together.

### Channels
- Consumers install from the default branch's HEAD. Branch discipline — not the tag — delivers stability; the tag is the release marker of record. Pre-releases ship out-of-band (e.g. a local checkout), not through the default branch.

### PRs & branch protection
- PRs required for merges into `main` (release/hotfix). Approvals optional for a solo maintainer.
- Protect `main`: require the CI check + a PR + no force-push. Not linear-history (release merge commits are wanted).

### CI/CD
- CI: actions pinned to commit SHAs, least-privilege `permissions` (`contents: read` by default), Dependabot for the actions ecosystem. Lint + test on PRs into `main` and pushes to `develop`.
- CD: a workflow on a `v*` tag cuts a GitHub Release from the matching `CHANGELOG.md` section. No publish step when distribution is "clone the default branch."
