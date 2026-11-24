# FigmaEval

Official implementation of **FigmaEval: A Benchmark for Evaluating AI Agents in Professional UI Design**.

FigmaEval evaluates AI agents on interface design in native, editable Figma environments. The benchmark includes 84 tasks and 783 screens. This repository provides code for design generation, automated scoring, and blinded human evaluation.

## Repository structure

| Path | Description |
|---|---|
| `scripts/claude_code_harness.py` | Design generation and automated scoring |
| `server/figma_mcp_stdio_proxy.py` | Figma MCP integration |
| `benchmarks/rubrics/` | Evaluation rubrics |
| `arena/`, `server/benchmark_arena.mjs` | Human evaluation interface and server |
| `examples/` | Configuration examples |
| `tests/` | Tests |

## Installation

Requirements: Linux, Python 3.11+, and Node.js 22.16+.

```bash
npm ci
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
npm install -g @anthropic-ai/claude-code
```

## Usage

Use `examples/inference.example.json` and `examples/judges.example.json` to configure model APIs, Figma OAuth, and task files. Save your configurations in `private/`.

```bash
# Generate designs
npm run paper:inference -- \
  --config private/inference.json --output outputs/inference

# Score generated designs
npm run paper:judge -- \
  --config private/judges.json \
  --from-inference outputs/inference/BATCH_DIRECTORY \
  --output outputs/judges
```

Replace `BATCH_DIRECTORY` with the batch directory created during design generation.

To try the human evaluation interface:

```bash
npm run demo
```

After starting the demo, run `cat outputs/arena-demo/access.json` in another terminal to find the access codes, then open the [local interface](http://127.0.0.1:18186). The demo uses synthetic data.
