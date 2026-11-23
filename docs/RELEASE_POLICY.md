# Framework-only publication policy

This repository distributes executable framework code, placeholder examples, rubric definitions, documentation and synthetic tests. The actual benchmark dataset and Arena state are a separate private runtime concern.

## Allowed source

The audited tree admits:

- Root README, package manifests, dependency requirements and Git ignore rules.
- JavaScript/HTML/CSS Arena source, without bundled snapshot/media files.
- Python and JavaScript server, command and test code.
- Markdown documentation and offline GitHub Actions workflows.
- The fixed-v4 evaluation rubric and explicitly named placeholder example files.
- A pre-push hook that checks the exact outgoing commit trees.

Only the synthetic fixture generator is included. It creates generic PNGs in an ignored local output directory when a developer runs a demo or test. No real candidate imagery is used by these tests.

## Excluded data

Do not add real task briefs, starter copies, Figma file URLs, candidate snapshots, screenshot catalogs, design files, images, audio/video, archives, trajectories, model responses, judge scores, reviewer identities, annotations, human ballots, credentials, database files, logs, production account lists or internal deployment settings.

Runtime manifests are ignored globally. The only JSON exceptions are package metadata, named example manifests and the rubric. Binary media, tabular exports, archives, storage, output, private, media, screenshot and backup directories are also ignored. Files already tracked by Git still require an audit; `.gitignore` alone does not remove them.

All local Arena rounds, including frozen snapshots and media, belong under `private/` or `outputs/`. The Arena may read those local files at runtime. That is independent of publishing the framework repository; neither the example workflow nor the demo command uploads them to GitHub or another storage service.

## Publication checks

```bash
# Check new and tracked, nonignored local source before staging:
python scripts/check-release.py --working-tree
# Stage only reviewed framework paths; check the exact index bytes:
python scripts/check-release.py
# Check a committed snapshot and all reachable local history:
python scripts/check-release.py --tree HEAD --history
```

The check rejects paths outside the source allowlist, binary and oversized files, symlinks/submodules, detected credentials, non-placeholder email addresses and Figma links, private deployment paths and private network addresses. It reports category, filename and line number without printing suspected secret values.

A failing check must be resolved before publishing. Do not weaken the allowlist to accommodate runtime data. Existing local history is also scanned so that deleting a sensitive file from HEAD does not silently leave it in the objects sent to GitHub. If a historical commit contains private material, stop and resolve that history before a push; do not force-push a rewrite without a reviewed plan.

To enable the repository's local preventive gate:

```bash
git config --local core.hooksPath .githooks
```

Preserve an existing custom hook setup rather than overriding it blindly. The supplied pre-push hook checks each outgoing local commit plus reachable history. The active GitHub Actions workflow checks the committed tree/history and runs offline tests. The workflow has read-only repository permission and no artifact-upload step.

## Limits and review

Pattern checks and file allowlists catch accidental publishing mistakes, but cannot prove that arbitrary prose or code contains no private information. Review source changes as well: do not encode real task data or credentials inside otherwise allowed code or Markdown. Keep examples on documented placeholder domains and generate fixtures rather than copying experiment outputs.

A passing check says the audited Git index or tree meets this publication policy. It does not grant an external service access, certify experiment provenance, or prove that a remote GitHub push succeeded.
