# Figma Design Benchmark

Code for running editable interface design tasks in Figma, scoring their screenshots with three model judges, and collecting blinded human comparisons in an Arena.

This release contains a **Claude Code harness** for generation and judging. Claude Code owns the model/tool loop; Python schedules isolated CLI processes, records telemetry and runs deterministic acceptance checks. The optional local proxy only adapts Anthropic-compatible transport and model routing. It does not implement an alternative agent loop.

## Contents

- `scripts/claude_code_harness.py`: inference and independent repeated judging.
- `server/figma_mcp_stdio_proxy.py`: authenticated, assigned-file-scoped Figma MCP.
- `server/benchmark_*`: screen inventory, screen count, native capture and blank-screen acceptance.
- `benchmarks/rubrics/fixed-v4.json` and `server/fixed_scales/fixed_v4.mjs`: 22-item rubric, maximum 53 points.
- `server/benchmark_arena.mjs` and `arena/`: blinded comparison, per-screen review, task selection, saved progress, incremental ranking and administration.
- `tests/`: deterministic regression tests and synthetic integration fixtures.

Actual benchmark task files, design outputs, screenshots, trajectories, credentials, scores and human ballots are not included. The offline demo creates synthetic layouts, never benchmark results. No license is granted by this release; licensing is pending. External dependencies retain their respective licenses.

## Setup

Requires Linux, Node.js 22.16+ and Python 3.11+. The harness was checked against Claude Code **2.1.310**; use a CLI version supporting `--bare`, `--restricted`, `--strict-mcp-config`, `--permission-mode dontAsk`, and streaming JSON output. CLI availability and model availability are separate requirements.

```bash
npm ci
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
npm install -g @anthropic-ai/claude-code
claude --version
npm test
python -m unittest discover -s tests -p 'test_*.py'
```

An optional GitHub Actions template is provided in `examples/ci-workflow.example.yml`; it runs offline tests without API keys.

The CLI and Figma MCP are external dependencies. This repository neither bundles Claude Code nor grants access to Figma or commercial model APIs.

## Inference

Copy `examples/inference.example.json` to `private/inference.json`, put the task query in a private text file, and configure a **dedicated writable Figma copy per task/model**. Paths in configuration are relative to that configuration file. Use a fresh output directory for each invocation.

```bash
export MODEL_API_KEY='your-local-credential'
python scripts/claude_code_harness.py inference \
  --config private/inference.json --output outputs/inference --validate-only
python scripts/claude_code_harness.py inference \
  --config private/inference.json --output outputs/inference
```

Configure each model's Anthropic-compatible `base_url` and `cli_model`. An optional `route_model` starts a loopback compatibility proxy which substitutes the requested upstream model; it **does not translate OpenAI/Responses protocols into Anthropic**. Non-Anthropic models require a gateway implementing Anthropic messages, tools and image inputs. Record and inspect both configured and returned model IDs; model names alone are not proof of the underlying provider. `effort` records the requested CLI setting, not a claim that every provider honors it.

Each configured account runs a sequential queue; independent account queues run up to `concurrency`. OS locks also protect the account identity and file across processes. Set the same `FIGMA_HARNESS_LOCK_DIR` for runners sharing accounts, and use canonical, unique account identities. The runner uses the supplied OAuth `access_token` file; obtaining/refreshing OAuth and provisioning editable copies are prerequisites, not automated here. See [the protocol](docs/PROTOCOL.md).

Generation is successful only when the CLI completes, the screen count passes and the **v2 blank-screen check** passes. An unavailable check remains an error. Acceptance is not a semantic requirement-satisfaction score. The runner preserves each attempt and does not clear or retry an existing Figma workspace automatically.

## Three-model judging

`examples/judges.example.json` specifies three distinct judge routes, three repetitions each and concurrency 8. Supply all artifact PNGs, the original task query and a layer-summary JSON from the final `screen-inventory.json`. Configure `gate_policy` explicitly: `disabled` sums the 22 scores; `required` additionally applies the rubric's G0 gate. Keep that policy fixed within a comparison.

```bash
python scripts/claude_code_harness.py judge \
  --config private/judges.json --output outputs/judges --validate-only
python scripts/claude_code_harness.py judge \
  --config private/judges.json --output outputs/judges
```

Each repetition starts a fresh CLI context with only `Read` and no MCP server. Every screenshot must produce a successful image Read result. Missing images, malformed scores, timeouts and API errors stay incomplete; they never become zero scores. Each artifact/judge mean is published only after all repetitions complete, and the three-judge mean only after all judges complete. Raw score evidence and observed CLI telemetry remain in private output folders.

## Human Arena

```bash
npm run demo
# In a second local terminal:
cat outputs/arena-demo/access.json
# Open http://127.0.0.1:18186 and enter a generated reviewer access code.
```

Use a fresh demo directory on subsequent starts: `npm run demo -- outputs/demo-2`. For a real frozen Arena snapshot:

```bash
npm run arena -- --directory private/arena-round --host 127.0.0.1 --port 18186
```

A round requires `snapshot.json` and its verified local media. The server creates private access codes and a SQLite database. Preserve these to resume review. Admin endpoints require admin access by default. Run behind an HTTPS reverse proxy and use `--secure-cookies true` for remote deployments. Keep live Figma links disabled during blinded review; author/model names inside screenshots must also be redacted by the dataset curator.

To display fresh harness scores in an Arena round, use candidate IDs as artifact IDs and provide the exact frozen PNGs in their snapshot order:

```bash
node scripts/export-harness-arena-scores.mjs \
  --arena private/arena-round --batch outputs/judges/BATCH_DIRECTORY \
  --config private/judges.json --output private/arena-scores
npm run arena -- --directory private/arena-round \
  --judge-scores-directory private/arena-scores
```

The bridge verifies the configuration hash, rubric, repetitions and image hashes against the frozen candidate revision. Incomplete judge blocks remain missing.

## Research scope

This release identifies its framework as `claude-code` and retains the actual CLI version, returned models and usage. Historical experiments may have used different orchestration, routing or gate settings. Publishing this implementation does not retroactively establish the provenance of any historical result or guarantee identical outputs. Paper claims must be tied to the run manifests of the experiments actually reported. The dataset and historical result bundles are separate releases.
