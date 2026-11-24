# FigmaEval：原生 Figma 设计基准

本仓库提供论文 **FigmaEval: A Benchmark for Evaluating AI Agents in Professional UI Design** 的代码。本次发布基于 `figmaeval-cvpr2027/v1` 协议，实现了论文的核心流程：在原生 Figma 环境中进行推理，并依据评分量表进行评审；同时提供可配置的 Arena 框架，用于人工盲评比较。

**本仓库不发布基准任务文件、设计产物、截图、轨迹、评审者身份、投票记录、评分、凭据、生产环境账号配置或内部服务器路径。** 示例和测试使用占位内容或合成测试数据。演示 PNG 仅在需要时于本地生成，生成的演示资源不会提交到仓库。

## 与论文的对应关系

| 论文要求 | 实现方式与使用说明 |
|---|---|
| 需求规格受约束，设计方案开放 | 读取设计需求、品牌规范、组件和媒体资源，自主设计原生、可编辑的 Figma 界面；不提供原始参考布局。 |
| 84 个任务、783 个必需界面、11 个生成模型 | `scope: full` 校验包含 924 个产物的完整矩阵；`scope: subset` 明确表示仅覆盖部分范围。实际任务资源作为独立的私有输入提供。 |
| 统一的 Claude Code 智能体运行框架 | `scripts/claude_code_harness.py` 让所有生成模型使用相同的 CLI／工具循环；该入口不使用直接调用 SGLang 的循环。 |
| 四个 Figma MCP 工具 | 仅使用 `whoami`、`get_metadata`、`get_screenshot` 和 `use_figma`；支持通过多轮截图检查并修正设计。 |
| 22 项标准、6 个维度、53 分 | 使用冻结的 `fixed_v4` 定义；评审模型查看每个产品界面及其对应的 Figma 图层摘要。 |
| 三位评审模型，每位进行三次指定种子的评审 | 使用 Claude Opus 5.5、GPT-6.1 Sol 和 DeepSeek V4.1 Flash；在独立上下文中分别请求种子 42、102 和 423。 |
| 表 2 的评分汇总方式 | 先对每位评审模型的三次评分取平均，再对三位评审模型取平均，除以 53 进行归一化，最后对各任务等权平均。缺失的评分块保持缺失。 |
| 盲测人工比较与 Bradley–Terry 排名 | 使用 Arena **版本 3 锦标赛**，关闭增量排名，启用私有管理员访问，并提供经过整理的匿名可编辑文件访问方式。演示及其他排名模式并非论文使用的 BT 流程。 |

表 1 的分值分配如下：

| 维度 | 评分项 | 满分 |
|---|---|---:|
| 用户体验 | A1–A4 | 8 |
| 信息组织 | B1–B5 | 15 |
| 布局质量 | D1–D4 | 12 |
| 一致性 | E1–E2 | 4 |
| 视觉呈现 | F1–F5 | 10 |
| 交付质量 | G1–G2 | 4 |
| 总计 | 22 | 53 |

B1–B5 和 D1–D4 各项采用 0–3 分，其余 13 项采用 0–2 分。总体质量由各项得分之和归一化得到，**不是对六个维度的百分比分数进行等权平均**。11 个生成模型分别为 Claude Sonnet 5.5、Claude Opus 5.5、DeepSeek V4 Flash、GPT-6.1 Sol、GPT-6 Astra、Qwen 3.8 Max、Fable 5.1、GLM-5.3 Flash、SenseNova 6.8 Flash、Gemini 3.5 Flash 和 Kimi K3。

## 环境配置

需要 Linux、Python 3.11+、Node.js 22.16+，以及支持 `--bare`、`--restricted`、`--strict-mcp-config`、`--permission-mode dontAsk` 和流式 JSON 输出的 Claude Code CLI。每次调用都会记录实际使用的 CLI 版本。

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

本次发布不授予任何使用许可，许可证方案待定。外部依赖仍遵循各自的许可证。CLI、Figma MCP、模型访问权限、账号和 OAuth 凭据均需事先另行准备。

## 推理

将 `examples/inference.example.json` 及其查询文件复制到 `private/`。示例中的所有网关、账号和 Figma 文件链接均为占位内容。真实凭据仅应存放于环境变量和私有 OAuth 文件中。

```bash
python scripts/claude_code_harness.py inference \
  --config examples/inference.example.json --output outputs/check --validate-only
python scripts/claude_code_harness.py inference \
  --config private/inference.json --output outputs/inference
```

`npm run paper:inference -- ...` 是等价入口，使用 PATH 中的 Python 3。`--validate-only` 检查配置结构与协议约束，不检查文件、凭据、可写席位、配额或服务可用性。

每个任务／模型组合都会获得一份独立、可写的原生副本，其来源是只读的 Starter File。原始查询中只包含一次源文件 URL，执行时仅替换该 URL。四个参考页面分别为 `00 · Start Here`、`01 · Foundations`、`02 · Components` 和 `03 · Media`。另设一个初始为空的 `03 · Workspace` 页面，用于放置设计。智能体仅通过四个 Figma MCP 工具进行检查、创建、截图和迭代完善：`whoami`、`get_metadata`、`get_screenshot` 和 `use_figma`。

每个模型／工具循环均由 Claude Code 负责。运行框架调度隔离的 CLI 进程，对账号和文件加锁，记录遥测，并执行确定性的界面数量检查与空白界面检查。它不会启动另一套直接调用模型的循环。即使文件中恰好包含足够数量的 Frame，失败的生成任务仍记为失败。

为每条路由配置 `paper_model`、`cli_model`、兼容 Anthropic 的 `base_url`、`api_key_env` 和 `returned_model_prefixes`。可选的 `route_model` 会启动一个本机回环路由代理；该代理不会将 OpenAI Responses 转换为 Anthropic messages。每次调用都会记录配置中的模型标识和实际返回的模型标识。

`scope: subset` 用于本地冒烟测试或明确限定范围的比较。`scope: full` 要求包含 84 个任务、783 个必需界面以及全部 11 个生成模型，共产生 924 个任务／模型作业。本仓库不包含数据集本身。

## 三位评审模型评分

将 `examples/judges.example.json` 复制到私有目录，并配置三条独立路由：Claude Opus 5.5、GPT-6.1 Sol 和 DeepSeek V4.1 Flash。用于生成的 DeepSeek 模型是 V4 Flash，与用作评审的 V4.1 Flash 是不同的模型标识。

```bash
python scripts/claude_code_harness.py judge \
  --config examples/judges.example.json --output outputs/check --validate-only
python scripts/claude_code_harness.py judge \
  --config private/judges.json \
  --from-inference outputs/inference/BATCH_DIRECTORY \
  --output outputs/judges
```

`npm run paper:judge -- ...` 是等价入口。`--from-inference` 从完整且已通过验收的新协议批次中导入所有产物，并拒绝存在缺失或失败作业的批次。也可以显式配置产物，提供原始查询、最终界面清单、匹配的图层摘要、预期界面数量，以及每个产品 Frame 的 PNG 和节点 ID。所有重复评审均使用同一份证据的冻结副本。

协议要求每位评审模型使用三个独立的 CLI 上下文，种子分别为 **42、102 和 423**，并显式设置 `gate_policy: required`。每个上下文仅有 `Read` 工具，不配置 MCP 服务器；每张 PNG 都必须成功产生图像工具读取结果。22 个计分项的满分合计为 53；G0 是独立的可用性门槛。缺失图片、格式错误或缺失的评分项、无效证据、超时和 API 失败均保持缺失，不记为零分。有效判定的 G0 未通过可以产生真实的零分。

本机回环代理会在上游消息请求中转发配置的种子，并记录请求哈希和 HTTP 响应状态。所配置的网关须支持相应消息格式与种子参数。

结果包括 `scores.json` 中每位评审模型三次评分的均值与样本标准差、产物均分和各维度百分比分数，以及 `model-scores.json` 中按任务等权汇总的模型结果。缺少任意一次重复评审时，不计算该评审模型的均分；任意评审模型的评分块不完整时，不计算该产物的均分。缺少任务时，也不计算配置范围内的模型汇总结果。完整评审需要 8,316 次独立调用。

## 人工 Arena 框架

**请显式选择排名模式。** `npm run demo` 使用旧版 TrueSkill 流程，生成一个合成的版本 1 轮次，用于测试界面，并非论文中的 Bradley–Terry 评测。版本 2 使用平衡配对胜率。版本 3 在关闭增量排名时使用 Bradley–Terry。可选的增量模式仅报告任务内排序，不计算全局 BT 评分。

若要按论文方式开展人工评测，请使用 `server/arena_tournament.mjs` 中的 `tournamentProtocol()` 准备私有的**版本 3**快照，招募专业设计师，并在收集投票前冻结候选集合。提供标准化的设计需求、对齐的截图和匿名可编辑 Figma 文件；使用 `server/arena_figma_links.mjs` 校验私有匿名链接映射，并检查文件标题与内容中是否存在可识别身份的信息。随后启动：

```bash
npm run arena -- --directory private/paper-arena --host 127.0.0.1 --port 18186 \
  --incremental-ranking false --public-admin false --show-figma-links true
```

显式传入的参数会覆盖已保存的服务设置。检查管理员面板中的 `ranking.method`：与论文一致的 BT 流程应显示 `design-arena-bradley-terry-mm/v3`。发送给评审者的数据不包含模型身份和自动评分；左右分配按每一对候选以确定性方式随机化。匿名链接映射和所有可编辑文件均作为私有运行时输入提供，不属于仓库内容。

BT 实现统计实际观测到、可判定胜负的投票，并排除 `unable`。当比较图不连通或存在统计分离（separation）时，系统会报告该情况，不给出有限的全局排名。显示的评分为 `400 × log10(strength)`，强度的几何平均值归一化为 1。

仅测试界面的本地冒烟测试：

```bash
npm run demo
cat outputs/arena-demo/access.json
```

后续启动时请使用新目录：`npm run demo -- outputs/demo-2`。运行自己的私有轮次：

```bash
npm run arena -- --directory private/arena-round --host 127.0.0.1 --port 18186
```

该框架提供盲测成对比较、逐屏评审、进度持久化、标注、增量排名、评分展示和管理功能。离线候选版本修订／模型扩展辅助工具在私有数据库副本上操作，保留不受影响的投票和进度。候选集合的任务数量和模型身份由本地清单提供，代码中不嵌入生产环境数据。

真实轮次需要私有的冻结快照及其本地媒体资源。这些运行时输入以及生成的 SQLite／访问配置文件均不纳入 Git。本仓库不附带实际运行的评测轮次、生产任务列表、候选图片或真实投票记录。管理员端点默认要求访问授权；用于盲测评审的实时 Figma 链接默认关闭。远程部署时，请显式配置 HTTPS 和 `--secure-cookies true`。

将新的评审批次绑定到自己的冻结 Arena 版本：

```bash
node scripts/export-harness-arena-scores.mjs \
  --arena private/arena-round --batch outputs/judges/BATCH_DIRECTORY \
  --output private/arena-scores
npm run arena -- --directory private/arena-round \
  --judge-scores-directory private/arena-scores
```

桥接程序会校验批次的冻结配置、评分量表、带种子的重复评审、成功的图像读取记录，以及完全一致的截图哈希。不完整的评审模型评分块保持缺失。程序只写入指定的本地私有目录，不会发布数据。

## 仅发布框架代码

```bash
npm run release:check:working
npm run release:check
python scripts/check-release.py --tree HEAD --history
```

发布检查允许框架文本、文档中说明的占位示例和评分量表，拒绝运行时清单、二进制媒体、数据集、压缩归档、凭据以及检测到的私有标识信息。已启用的 GitHub Actions 工作流会执行该检查以及离线 Node／Python 测试，不上传运行时产物。
