# Paper-to-code alignment audit

Audit date: 2026-11-23. Manuscript: **FigmaEval: A Benchmark for Evaluating AI Agents in Professional UI Design**, supplied final PDF, 10 pages. PDF SHA-256: `e64b56576a0b2fb4864759e92280fec6c1a90a52a42eb6226a7563ae8aafb27c`.

The audited GitHub `main` was `70e9dfbc54405f622cb469876036c6e185f5d6c7`, tree `9a98fcd54f1a80bec977efc4bfd011bfcc5d15c5`. Its complete source tree matched the local audited framework release. This document updates the explanation; it does not introduce new model outputs, task files or human votes.

## Conclusion

The core generation and rubric-scoring path implements the paper's stated model set, shared Claude Code harness, Figma tool restrictions, whole-artifact visual/structural evaluation, 22-criterion allocation and three-judge/three-pass aggregation. The Arena includes a Bradley–Terry implementation corresponding to the paper's human-evaluation method, but also includes alternative modes: selecting an arbitrary Arena/demo mode is not sufficient to establish alignment.

The code can be checked against the main paper. Historical experiment equivalence additionally requires the actual model routes, task resources, versioned supplement, seed enforcement and run/vote manifests. Those private materials are deliberately excluded from this repository. This audit does not assert numerical reproduction of the paper's tables or agreement statistics.

## Requirements and implementation evidence

| Manuscript requirement | Code evidence | Conclusion |
|---|---|---|
| §3.1: standardized screens/content/resources; original layouts withheld; open visual solutions | `server/benchmark_design.mjs`, `benchmarkDesignSystemPrompt(..., {paperProtocol: true})` | The prompt preserves design freedom and uses native Figma output. Content-level removal of reference-layout clues remains a dataset-curation responsibility. |
| §3.2: four Starter reference pages | `validate_starter` in `scripts/claude_code_harness.py` | Requires 00 Start Here, 01 Foundations, 02 Components, 03 Media. The additional 03 Workspace is an implementation delivery-page convention, distinct from the Media page. |
| §3.3: 84 tasks and 783 required screens | `validate` in the harness; full-scope regression | Full mode validates 84 unique tasks, 783 screens by task, and 84×11 task/model cells. A valid schema does not certify the absent dataset's domain/screen-type annotations. |
| §4.1: eleven evaluated generation models | `PAPER_MODELS`, example inference manifest | Names match the main paper. The DeepSeek generation identity is V4 Flash, separate from the V4.1 Flash judge. Configured and observed provider labels are recorded. |
| §4.1: all models use the same Claude Code agent harness | `run_cli`, `infer_one`, isolated configuration/work directories | All configured generation routes execute the same CLI loop. The release entry point does not call a separate direct model agent loop. |
| §4.1: whoami, get_metadata, get_screenshot, use_figma | CLI permission list, `prepare_mcp`, assigned-file MCP proxy | Exactly these Figma MCP tools are available; shell/web/subagent workflows are disabled. |
| Fig.1 / Agent Setup: inspection, editing and visual feedback | `benchmarkDesignSystemPrompt` | Multiple screenshots, fixes and checks are allowed during inference. The historical no-inference-screenshots profile is not applied by the release entry point. |
| §3.4: one entire artifact, screenshots plus Figma structures | `artifact_fingerprint`, `judge_one`, frozen inventory/layer summary | Every product frame needs a matching PNG/node ID; G1/G2 receive structural summary evidence. Compact summaries do not prove complete semantic editability. |
| Table 1: six dimensions, 22 criteria, total 53 | `server/fixed_scales/fixed_v4.mjs`, frozen `benchmarks/rubrics/fixed-v4.json` | The question counts/maxima match exactly; rubric snapshot hash is `1bdd89598a3b5653fe1416b7cab72631e12833c3c93cdce784960ef8f1d67b93`. |
| §4.1: three judge identities, passes 42/102/423 | `PAPER_JUDGES`, `SEEDS`, `validate`, `judge_one`, seed proxy | Exact identity/seed configuration is enforced. Repeated contexts are independent; seed receipts establish transmission, not unverified provider-side random-number control. |
| Table 2: average passes, then judges, then report percentages | `summarize_scores`, `summarize_models` | Three repeats per judge, equal judge weight, 53-point normalization, equal task weight. Missing configured blocks do not become zeros. |
| §3.4: blinded professional comparisons, randomized sides | `createArenaStore`, `sides`, `publicPair`, private reviewer accounts and Figma alias mappings | The framework supports the stated presentation. Recruiting professionals and removing identity clues inside private images/files require curation. |
| §3.4: direct preference votes aggregated by Bradley–Terry | `bradleyTerryRankings` in `server/arena_tournament.mjs`; version 3 tournament branch in `dashboard` | Use this path explicitly. The demo, version 2 and incremental sorting use different ranking rules. |

## Score calculation

For task t, generation model m, judge j and pass r, the implementation uses:

```text
S(t,m,j,r) = g0(t,m,j,r) × sum of the 22 item scores
J(t,m,j)   = mean of the three complete seeded passes
A(t,m)     = mean of the three complete judge means
P(t,m)     = 100 × A(t,m) / 53
Model(m)   = equal-weight mean of P(t,m) over the configured tasks
```

The manuscript Table 1 allocation is A1–A4: 8, B1–B5: 15, D1–D4: 12, E1–E2: 4, F1–F5: 10, G1–G2: 4. Nine items use 0–3; thirteen use 0–2. Six dimension percentages have different denominators and must not be averaged equally to obtain the overall score.

G0 and the 30–120-character evidence format come from the existing repository rubric and the accompanying local supplementary definition used during development. The supplied main-paper PDF refers full rubric details to supplementary material but does not itself define G0. Exact agreement with a final supplementary PDF has not been independently established. G0 is separate from the 22 scored criteria, and a valid gated zero is distinct from a missing evaluation.

Applying G0 to each displayed dimension, requiring an exact expected screen count/blank-screen acceptance before importing an entire inference batch, and withholding incomplete aggregates are explicit engineering choices. The main paper does not fully specify these edge cases; do not describe them as independently verified historical settings.

## Arena paths and paper use

| Snapshot / option | Actual ranking path | Relation to the paper |
|---|---|---|
| `npm run demo`, version 1 | `pooled-within-case-trueskill-v1` | Synthetic UI demonstration, not the paper's Bradley–Terry aggregation. |
| Version 2 | `balanced-pairwise-win-rate/v2` | Alternative collection/ranking protocol; not a replacement for the reported BT aggregation. |
| Version 3, incremental ranking disabled | `design-arena-bradley-terry-mm/v3` | Implements the paper's stated BT aggregation family on observed preference votes. |
| Version 3, incremental ranking enabled | Within-task incremental sorting; no global BT rating | Optional framework feature, not the paper's model-level ranking calculation. |

For a paper-style round:

1. Prepare a private frozen version 3 snapshot with `tournamentProtocol()` and the intended complete candidate cohort. Professionally curate the task briefs, aligned images and native editable Figma files.
2. Keep the expert reviewer group and sampling policy fixed before collecting comparisons. The repository's four-model/five-battle session design, stopping thresholds and optional active sampling are concrete implementation choices; the supplied main text does not enumerate all of them.
3. Prepare verified anonymous Figma link/title mappings through `server/arena_figma_links.mjs`; inspect content for author/model identity clues. Anonymous URLs alone do not certify blinding of the full external editor.
4. Start with `--incremental-ranking false --public-admin false --show-figma-links true`. Explicit values override prior saved service options. An images-only round omits editable-file inspection described in the paper.
5. Confirm `ranking.method` is `design-arena-bradley-terry-mm/v3`. Direct observed overall votes are the ranking observations; per-screen votes, inferred orders and unobserved pair outcomes must not be added as extra human votes.
6. Preserve the private snapshot, votes, reviewer scope and candidate revisions with the result analysis. Publish only the framework source here.

The BT mode excludes `unable` comparisons and uses decisive observed votes. It reports disconnected or separated graphs instead of inventing a finite unregularized global MLE. Strengths have geometric mean one; rating is `400 × log10(strength)`, centered without an added Elo display offset. The paper reports positive Elo-style values but the supplied text does not fix every numerical normalization. Matching exact ratings requires the historical votes and the historical normalization, not just selecting the same algorithm family.

The code includes observed-ballot agreement utilities, but the published framework and its synthetic tests do not recompute the paper's Kendall τb, 76.58% agreement, ablations, failure prevalence, cost plots or SFT results. These require their proper cohorts, metric/tie policies and private experimental evidence. Do not replace the main paper's aggregate judge mean with a per-judge dashboard number when comparing to human rankings.

## Verification and publication boundary

Revalidated locally on the audit date: all 151 Node tests and all 24 Python tests passed. The exact model/judge sets, seeds, four tools, rubric snapshot, six dimension maxima and example schemas also passed direct invariant checks. Framework-only working-tree/history checks passed before publication.

The code-level checks cover the four-tool list, reference-page/Workspace distinction, exact 22/53 allocation, correct generation/judge model identities, required seeds, complete input coverage, aggregation and missing-score rules. Existing tests also cover blinded Arena payloads, deterministic side assignment, observed-vote BT behavior and the alternative modes.

Only source and this audit explanation are published. No PDF, original task descriptions, actual screenshots, real scores, Figma file identifiers, reviewer identities or ballots are added. Framework-only Git index/tree/history checks remain mandatory. A passing offline test or successful schema validation is not a live Figma/model API experiment and is not evidence that historical model providers enforced the requested seed.
