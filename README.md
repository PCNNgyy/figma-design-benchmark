# Figma Design Benchmark

A portable framework for native Figma design generation, repeated rubric judging, and blinded human comparisons. This version updates the Claude Code harness to the explicit `figmaeval-cvpr2027/v1` protocol and retains a data-free Arena framework.

**No benchmark task files, design outputs, screenshots, trajectories, reviewer identities, ballots, scores, credentials, production account settings or internal server paths are distributed.** Examples and tests use placeholders or synthetic fixtures. Demo PNGs are generated locally when requested; no generated demo assets are committed.

## Setup

Requires Linux, Python 3.11+, Node.js 22.16+, and a Claude Code CLI supporting `--bare`, `--restricted`, `--strict-mcp-config`, `--permission-mode dontAsk`, and streaming JSON output. Every invocation records the actual CLI version. A local fixture CLI in the tests is not a live provider test.

```bash
npm ci
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
npm install -g @anthropic-ai/claude-code
npm test
npm run test:python
npm run release:check
```

No license is granted by this release; licensing is pending. External dependencies retain their respective licenses. The CLI, Figma MCP, model access, accounts and OAuth credentials are external prerequisites.

## Inference

Copy `examples/inference.example.json` and its query file into `private/`. All example gateways, accounts and Figma file links are placeholders. Put actual credentials only in environment variables and private OAuth files.

```bash
python scripts/claude_code_harness.py inference \
  --config examples/inference.example.json --output outputs/check --validate-only
python scripts/claude_code_harness.py inference \
  --config private/inference.json --output outputs/inference
```

`npm run paper:inference -- ...` is an equivalent entry point using Python 3 on PATH. `--validate-only` checks configuration structure and protocol constraints; it does not check files, credentials, writable seats, quotas or service availability.

Each task/model gets a distinct writable native copy of its read-only source Starter File. The original query contains the source URL once; only that URL is replaced for execution. The four reference pages are `00 · Start Here`, `01 · Foundations`, `02 · Components` and `03 · Media`. A separate, initially empty `03 · Workspace` receives the design. The agent can inspect, create, take screenshots and refine through exactly four Figma MCP tools: `whoami`, `get_metadata`, `get_screenshot` and `use_figma`.

Claude Code owns every model/tool loop. The harness schedules isolated CLI processes, takes account/file locks, records telemetry, and runs deterministic screen-count and blank-screen checks. It does not launch an alternative direct model loop. A failed generation remains failed even if the file happens to contain enough frames.

Configure `paper_model`, `cli_model`, the Anthropic-compatible `base_url`, `api_key_env`, and `returned_model_prefixes` per route. Optional `route_model` starts a loopback routing proxy; it does not translate OpenAI Responses into Anthropic messages. The recorded returned model labels help detect routing errors but are not proof of an underlying provider's identity.

`scope: subset` is for local smoke tests or explicitly scoped comparisons. `scope: full` requires 84 tasks, 783 required screens and all eleven generation models, yielding 924 task/model jobs. The dataset itself is not included. Do not relabel a subset as a full benchmark run.

## Three-judge scoring

Copy `examples/judges.example.json` to a private directory and configure three independent routes: Claude Opus 5.5, GPT-6.1 Sol and DeepSeek V4.1 Flash. The generating DeepSeek model is V4 Flash; it is a separate identity from the V4.1 Flash judge.

```bash
python scripts/claude_code_harness.py judge \
  --config examples/judges.example.json --output outputs/check --validate-only
python scripts/claude_code_harness.py judge \
  --config private/judges.json \
  --from-inference outputs/inference/BATCH_DIRECTORY \
  --output outputs/judges
```

`npm run paper:judge -- ...` is equivalent. `--from-inference` imports every artifact from a complete, accepted new-protocol batch and rejects missing/failed jobs. Alternatively, configure explicit artifacts with the original query, final inventory, matching layer summary, expected screen count, and every product-frame PNG with its node ID. All repetitions use frozen copies of the same evidence.

The protocol requires three independent CLI contexts per judge, with seeds **42, 102 and 423**, and explicit `gate_policy: required`. Each context has only `Read` and no MCP server; every PNG must produce a successful image tool result. The 22 scored criteria sum to 53; G0 is a separate viability gate. Missing images, malformed/missing items, invalid evidence, timeouts and API failures remain missing, not zero scores. A valid G0 failure can produce a genuine zero.

The loopback proxy puts the requested seed into upstream message requests and records forwarding receipts. This needs a compatible gateway: unsupported seed requests fail rather than silently dropping the seed. Receipts prove transmission and HTTP acceptance; provider-side random-seed enforcement remains `unverified` unless independently established. Do not describe three unseeded repetitions as seeded passes or claim deterministic commercial outputs from these receipts alone.

Results include per-judge three-pass means and sample standard deviations, artifact means and dimension percentages in `scores.json`, and equal-task-weight model summaries in `model-scores.json`. A missing repetition prevents that judge's mean; an incomplete judge block prevents the artifact mean. Missing tasks also prevent the configured model aggregate. Full judging needs 8,316 independent invocations. The [protocol](docs/PROTOCOL.md) specifies inputs, checks and limitations.

## Human Arena framework

Start a local synthetic demo:

```bash
npm run demo
# In another terminal, inspect the generated private access codes:
cat outputs/arena-demo/access.json
# Open http://127.0.0.1:18186
```

Use a fresh directory on a later start: `npm run demo -- outputs/demo-2`. To run your own private round:

```bash
npm run arena -- --directory private/arena-round --host 127.0.0.1 --port 18186
```

The framework includes blinded pairwise comparison, per-screen review, progress persistence, annotations, incremental ranking, score display and administration. Offline candidate revision/model expansion helpers preserve unaffected votes and progress on private database clones. Cohort task counts and model identities are supplied by the local manifest, not embedded production data.

A real round needs a private frozen snapshot and its local media. These runtime inputs and the generated SQLite/access files are excluded from Git. No live round, production task list, candidate images or actual ballots are bundled. Admin endpoints require access by default; live Figma links remain off for blinded review. For remote deployment, configure HTTPS and `--secure-cookies true` explicitly.

Bind a new judge batch to your own frozen Arena revision:

```bash
node scripts/export-harness-arena-scores.mjs \
  --arena private/arena-round --batch outputs/judges/BATCH_DIRECTORY \
  --output private/arena-scores
npm run arena -- --directory private/arena-round \
  --judge-scores-directory private/arena-scores
```

The bridge verifies the batch's frozen configuration, rubric, seeded repetitions, successful image reads and exact screenshot hashes. Incomplete judge blocks remain absent. It writes only to the specified local private directory and does not publish data.

## Framework-only publication

```bash
npm run release:check:working
# Stage explicitly reviewed source paths, then inspect the exact Git index:
npm run release:check
python scripts/check-release.py --tree HEAD --history
```

The release check allows framework text, documented placeholder examples and the rubric; it rejects runtime manifests, binary media, datasets, archives, credentials and detected private identifiers. The active GitHub Actions workflow runs this check plus offline Node/Python tests. It does not upload runtime artifacts. See [the publication policy](docs/RELEASE_POLICY.md).

This release does not establish the provenance of historical experiments, certify real provider seed support, or reproduce paper results. Paper claims must be tied to the actual experiment manifests, data and votes, which remain separate from this repository.
