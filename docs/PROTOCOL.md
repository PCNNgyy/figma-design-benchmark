# Execution and scoring protocol

Protocol identifier: `figmaeval-cvpr2027/v1`.

## Inputs and file isolation

The immutable task query names one read-only original Starter File exactly once. Every task/model receives a distinct writable native copy. Models of the same task must share the original brief and source file. The harness freezes input text and replaces only the original URL with the assigned copy URL.

The paper Starter pages are `00 · Start Here`, `01 · Foundations`, `02 · Components` and `03 · Media`. Reference pages must exist and be nonempty. The separate `03 · Workspace` starts empty or is created by the agent. Workspace inspection matches its name, so the Media page cannot be mistaken for the deliverable. Legacy `04 · Media` inputs need an explicit local preparation step; the runner does not silently rename or clear them.

The unified Claude Code context has exactly four MCP tools: `whoami`, `get_metadata`, `get_screenshot` and `use_figma`. Shell, arbitrary file writes, web fetch and subagents are disabled. Iterative screenshot inspection and repair remain available during inference. The historical profile that disables inference screenshots is not used by this entry point.

The MCP proxy enforces the assigned file key. Preserving the reference pages is a system-prompt constraint, not a formal page-level sandbox for arbitrary Plugin API code. Use disposable copies. The curator must independently inspect the reference resources for original-layout leakage; a page-name check cannot establish that fact.

Accounts need current private OAuth credentials, a writable seat and sufficient quota. One queue runs per account; canonical account identities and assigned files are locked across local processes. Runners sharing accounts across machines need a shared lock directory with working flock semantics. The framework does not provision production accounts or log into a browser.

`scope: full` requires 84 distinct tasks, 783 specified screens and all eleven generation models, for 924 distinct task/model jobs. `scope: subset` is explicitly partial. These checks establish the configured matrix shape, not the quality or identity of an unavailable dataset.

## Acceptance and evidence

After successful CLI completion, a read-only compact inventory records every Workspace node and per-product-frame structural summary. Count checks use the fixed expected screen count or reviewed exact screen names. Expected counts must not be edited to fit generated outputs.

Blank-screen rule `blank-screen-pixels/v2` checks the full rendered frame and an inset body (3% horizontal; 8% top and bottom), composites transparency over white, and checks zero-descendant product frames. Ambiguous blank crops are confirmed by native capture. Inventory and layer summary are compared again after capture to detect changes.

These are engineering heuristics, not semantic requirement satisfaction or a design-quality score. Failed or unavailable checks remain failed. An incomplete inference batch cannot silently become a smaller judging cohort through `--from-inference`. Source query hashes, assignment identities and accepted artifact evidence are rechecked during import.

All judge inputs are frozen once per batch: original query, complete inventory, matching layer summary and PNGs covering exactly every product frame. Every board needs structural fields. Frozen content hashes and protocol implementation hashes prevent repetitions from silently using different local inputs or code revisions.

## Judge execution

Judges are Claude Opus 5.5, GPT-6.1 Sol and DeepSeek V4.1 Flash, with three fresh CLI contexts each. Repeat 1 requests seed 42, repeat 2 requests 102, and repeat 3 requests 423. No prior response, generation model name or historical score is added to the scoring prompt.

Each judge context permits only Read, has no MCP server, and must produce successful image tool results for all screenshots before its output can count as complete. A tool call without an image result is insufficient. This proves that images entered the tool flow, not that the model understood them correctly.

The local routing proxy injects the requested seed into upstream message JSON and records the forwarded body hash and HTTP response status. Conflicting seeds fail. Unsupported gateways are not retried without seed. Receipt fields keep provider-side seed enforcement `unverified`; forwarding a seed is not proof of deterministic commercial model execution.

The frozen fixed-v4 rubric has 22 integer criteria with maxima 2 or 3, totaling 53. G0 is a separate binary viability gate; `gate_policy` is required. G1/G2 use the structural summary as well as screenshot context. Evidence must be nonempty and 30–120 characters for each item. Missing/duplicated items, invalid values, unavailable images or evidence mismatch prevent completion.

## Aggregation and failures

For one artifact, judge and seed, the score is G0 times the sum of the 22 criteria. A legitimate G0 failure is a score of zero; a missing output is null. Each judge mean requires all three distinct repeats and their matching seeds/input hashes. The artifact mean requires all three complete judge blocks. Percentage scores divide by 53.

Dimension percentages normalize by each dimension's maximum. The implementation also applies that repetition's G0 to each displayed dimension, so a gated zero does not display full dimension marks. This is an explicit display convention; it is not evidence about historical experiment aggregation.

Model summaries weight the configured tasks equally. Missing configured tasks prevent the aggregate. Do not compare uneven task subsets as a full model ranking. Sample standard deviation uses the three repetitions with n−1 denominator; repetitions are not additional independent tasks. Full evaluation has 924 artifacts and 8,316 judge contexts.

Each attempt saves CLI version, returned model labels, requested effort, raw usage/modelUsage, durations, turn counts and CLI-reported cost. Unknown values stay null. Do not sum overlapping usage objects. CLI-reported costs under gateway aliases are not verified billing. A price-based paper cost analysis needs its own frozen price table and accounting policy.

Timeouts terminate the entire CLI/MCP process group. Runtime errors and incomplete batches produce nonzero exit status and preserved private diagnostics. Re-running uses a fresh attempt and prepared copy; interrupted writes are not silently replayed. The framework does not select additional runs because a score is low.

## Arena runtime boundary

The repository provides the Arena source and a synthetic fixture generator. Private snapshots, candidate images, source manifests, accounts, annotations, votes, score exports, SQLite files and logs belong in ignored runtime directories, not Git.

A round binds local candidate identities to versioned screenshot hashes. Reviewer APIs conceal model identities and scores during blinded comparison. Private database clones can be revised or extended using explicit expected candidate replacements/additions; unchanged votes and pending screen work remain attached to their evidence. Revisions do not manufacture votes or establish ranking links between unconnected models.

The harness-to-Arena bridge reads the batch's frozen configuration, validates the current rubric, repeated seeds, read-image coverage and screenshot revision, then writes a local private score export. It does not publish the snapshot or scores. Keep actual task resources and historical result bundles separate from this source release.
