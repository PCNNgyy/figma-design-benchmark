# Execution and scoring protocol

## Inputs and isolation

The assigned copy contains `00 · Start Here`, `01 · Foundations`, `02 · Components`, `03 · Workspace` and optionally `04 · Media`. The system prompt asks the agent to preserve reference pages and build only in Workspace. The MCP proxy restricts calls to one assigned file and four tool names. Plugin code is powerful: the file restriction is enforced, but arbitrary Plugin API code is not a formal page-level security sandbox. Use disposable task copies and retain reference backups.

Accounts need an editable seat, current OAuth credentials and sufficient MCP quota. Example OAuth JSON is `{"access_token":"replace-locally"}`. Never commit that file. A refreshed token can be written atomically to the same private path. Canonical account identity prevents aliases from bypassing account locks. A shared lock directory is required across schedulers using the same accounts; local locks do not coordinate different machines without a shared filesystem supporting `flock`.

Inputs and models are supplied in local JSON manifests, not embedded production accounts. The example files validate schema without making network requests; placeholders do not represent working accounts or model routes. `--validate-only` validates configuration structure, not credentials, file contents or service availability. The CLI receives prompts via stdin and an isolated working/config directory. Its stream events and stderr remain private runtime artifacts.

## Acceptance

The runner reads a compact final Workspace inventory, preserving node IDs, sizes, product-frame classification and per-board layer counts. Default count rule is `support-board-exclusion/v3`. Optional exact required screen names use `required-named-screens/v1`; names must be reviewed against the brief before running every model. Do not change the expected count to match an output.

Blank rule is `blank-screen-pixels/v2`. It checks the rendered full frame and an inset body region (3% horizontal; 8% top and bottom), composites transparency over white, and uses the original threshold configuration in `benchmark_blank_screens.py`. Zero-descendant product frames also fail structurally, including colored shells. Ambiguous crops are confirmed with native node capture. Read-only checks compare the inventory again after capture to detect changes.

This is a deterministic heuristic, not proof of semantic completeness: sparse legitimate designs may need manual adjudication; colored or partially populated shells can evade pixel thresholds. A pass means only that the configured count and blank heuristics passed. Screenshots are needed by this acceptance stage and by later visual evaluation; they are also available to the inference agent as verification inputs through MCP.

## Telemetry and failures

Each invocation writes an immutable batch folder, per-attempt prompt hash, configured model route, CLI version, requested effort, observed model IDs, raw `usage` and `modelUsage`, wall-clock duration, CLI API duration, turn count and reported cost. Unknown fields remain null. Do not sum overlapping usage objects or infer missing token counts. `duration_ms` measures CLI/transport time; `total_duration_ms` includes acceptance and preparation. Credential values are passed through child environment, not command arguments or manifests. Logs may contain private task contents and are excluded from version control.

A timeout terminates the full CLI process group. A failed generation cannot become successful merely because an old workspace contains enough frames. Re-running uses a fresh attempt folder; restoring or clearing a workspace is a separate explicit operator action. Interrupted mutations are not silently replayed. Production schedulers, login automation and historical server paths are intentionally excluded.

## Judge protocol

Use a frozen artifact PNG list and compact layer summary for every judge, without the generating model's identity or historical score. The harness records image and prompt hashes, starts independent contexts and checks image Read tool-result coverage. Structural rubric evidence comes from the layer summary; the CLI need not reopen the live Figma file. G0 policy is explicit and is never mixed silently in an aggregate. Every rubric item needs an integer score within its own range and nonempty evidence. All 22 items sum to 53 at their maxima.

Three independent repetitions per judge yield mean and sample standard deviation. No mean is emitted for an incomplete judge/artifact block. An equal-weight three-judge mean requires all three blocks. Statistical conclusions across tasks should use task-level aggregation and uncertainty, rather than treating repetitions as extra tasks.

## Arena

A frozen snapshot binds candidates to case/model identities, assigned Workspace URLs and checksummed PNG files. Reviewer APIs blind identities, enforce the intended pair, and record which images were opened. SQLite preserves votes and continuation state. The supplied implementation includes balanced pairwise selection, incremental insertion and per-screen comparisons; choose and freeze one review protocol before collecting paper results. Insertion comparisons require anchors against existing models; a global rank cannot be inferred from an unconnected comparison graph. Demo data validates UI operation only.
