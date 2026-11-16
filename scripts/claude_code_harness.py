#!/usr/bin/env python3
"""Portable Claude Code batch harness. The CLI owns the model/tool loop."""
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'server'
sys.path.insert(0, str(SERVER))


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.chmod(0o600)
    temp.replace(path)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', value):
        raise ValueError('IDs must contain only letters, digits, dots, underscores and hyphens')
    return value


def resolve(base, value):
    return (Path(base) / value).resolve()


@contextmanager
def lease(name):
    # Shared across output directories/processes. Never start another run for a
    # busy identity or copy. Flock is held until generation AND acceptance finish.
    root = Path(os.environ.get('FIGMA_HARNESS_LOCK_DIR', str(Path.home() / '.cache/figma-harness/locks')))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / (digest(name.encode()) + '.lock')).open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def terminate(proc):
    if proc.poll() is not None:
        return
    os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


def execute(argv, *, directory, env, prompt, timeout, out, err):
    """No shell; terminate the complete CLI/MCP process group on timeout."""
    with Path(out).open('w') as stdout, Path(err).open('w') as stderr:
        proc = subprocess.Popen(argv, cwd=directory, env=env, stdin=subprocess.PIPE,
                                stdout=stdout, stderr=stderr, text=True, start_new_session=True)
        try:
            proc.communicate(prompt, timeout=timeout)
        except BaseException:
            terminate(proc)
            raise
        return proc.returncode


def parse_events(path):
    events = []
    for line in Path(path).read_text().splitlines():
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                events.append(obj)
        except json.JSONDecodeError:
            pass
    final = next((e for e in reversed(events) if e.get('type') == 'result'), {})
    models = sorted({e['message']['model'] for e in events
                     if e.get('type') == 'assistant' and isinstance(e.get('message'), dict)
                     and e['message'].get('model')})
    return events, final, models


def opened_images(events):
    reads, image_results = {}, set()
    for event in events:
        content = (event.get('message') or {}).get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get('type') == 'tool_use' and block.get('name') == 'Read':
                reads[block['id']] = block.get('input', {}).get('file_path')
            if block.get('type') == 'tool_result' and not block.get('is_error'):
                result = block.get('content', [])
                if isinstance(result, list) and any(isinstance(b, dict) and b.get('type') == 'image' for b in result):
                    image_results.add(block.get('tool_use_id'))
    return {str(Path(v).resolve()) for k, v in reads.items() if k in image_results and v}


def clean_environment():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(('ANTHROPIC_', 'CLAUDE_', 'CTTAP_')) and k != 'CLAUDECODE'}


def node_json(config, script, *args):
    return json.loads(subprocess.check_output([config.get('node_bin', 'node'), str(ROOT/'scripts'/script),
                                               *map(str, args)], cwd=ROOT, text=True))


def run_cli(config, model, case, prompt, *, mcp, judge=False, system_prompt=None):
    work = case / 'work'
    work.mkdir(exist_ok=True)
    settings = case / 'settings.json'
    # No shell, filesystem mutation, arbitrary fetch, skills, agents or inherited MCP.
    tools = ['Read'] if judge else ['mcp__figma__whoami', 'mcp__figma__get_metadata',
                                    'mcp__figma__use_figma', 'mcp__figma__get_screenshot']
    save(settings, {'permissions': {'allow': tools,
                                   'deny': ['Bash', 'Write', 'Edit', 'Agent', 'WebFetch', 'WebSearch']}})
    binary = config.get('claude_bin', 'claude')
    version = subprocess.check_output([binary, '--version'], text=True).strip()
    argv = [binary, '--bare', '--restricted', '--settings', str(settings), '--setting-sources', '',
            '--model', model['cli_model'], '--tools', ','.join(['Read'] if judge else []),
            '--allowedTools', ','.join(tools), '--permission-mode', 'dontAsk', '--disable-slash-commands',
            '--strict-mcp-config', '--mcp-config', str(mcp), '--no-session-persistence',
            '--output-format', 'stream-json', '--verbose']
    if model.get('effort'):
        argv += ['--effort', model['effort']]
    if system_prompt:
        system_file = case / 'system-prompt.txt'
        system_file.write_text(system_prompt)
        argv += ['--append-system-prompt', system_prompt]
    argv += ['-p']
    env = clean_environment()
    secret = os.environ.get(model['api_key_env'], '')
    if not secret:
        raise ValueError('Missing credential environment variable: ' + model['api_key_env'])
    env.update(ANTHROPIC_API_KEY=secret, ANTHROPIC_BASE_URL=model['base_url'],
               CLAUDE_CONFIG_DIR=str(case/'cli-config'), CLAUDE_CODE_NO_MODEL_FALLBACK='1',
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1', CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS='1',
               CLAUDE_CODE_DISABLE_AUTO_MEMORY='1', DISABLE_AUTOUPDATER='1',
               CLAUDE_CODE_MAX_OUTPUT_TOKENS=str(model.get('max_output_tokens', 16384)),
               API_TIMEOUT_MS=str(int(config.get('api_timeout_seconds', 900)*1000)))
    proxy = None
    proxy_log = None
    started = time.monotonic()
    try:
        if model.get('route_model'):
            transport = case / 'transport'
            transport.mkdir()
            save(transport/'config.json', {'upstream_base_url': model['base_url'],
                 'model_override': model['route_model'], 'normalize_text_blocks': True})
            proxy_log = (transport/'proxy.log').open('w')
            proxy = subprocess.Popen([config.get('node_bin', 'node'), str(SERVER/'run_compatibility_proxy.mjs'),
                                      '--config', str(transport/'config.json'), '--state', str(transport/'state.json')],
                                     stdout=proxy_log, stderr=proxy_log, start_new_session=True, env=clean_environment())
            for _ in range(100):
                if (transport/'state.json').exists() and read(transport/'state.json').get('status') == 'ready':
                    break
                if proxy.poll() is not None:
                    raise RuntimeError('Compatibility transport exited before ready')
                time.sleep(.1)
            else:
                raise TimeoutError('Compatibility transport startup timeout')
            env['ANTHROPIC_BASE_URL'] = read(transport/'state.json')['url']
        (case/'prompt.txt').write_text(prompt)
        save(case/'invocation.json', {'framework': 'claude-code', 'cli_version': version, 'argv': argv,
             'cwd': str(work), 'prompt_via_stdin': True, 'prompt_sha256': digest(prompt.encode()),
             'configured_cli_model': model['cli_model'], 'configured_route_model': model.get('route_model'),
             'effort_requested': model.get('effort'), 'timeout_seconds': config.get('timeout_seconds', 5400)})
        timed_out = False
        try:
            code = execute(argv, directory=work, env=env, prompt=prompt,
                           timeout=config.get('timeout_seconds', 5400), out=case/'events.jsonl', err=case/'stderr.log')
        except subprocess.TimeoutExpired:
            code, timed_out = None, True
        events, final, models = parse_events(case/'events.jsonl')
        metrics = {'framework': 'claude-code', 'cli_version': version, 'returned_models': models,
                   'duration_ms': round((time.monotonic()-started)*1000), 'usage': final.get('usage'),
                   'model_usage': final.get('modelUsage'), 'num_turns': final.get('num_turns'),
                   'cli_duration_ms': final.get('duration_ms'), 'cli_duration_api_ms': final.get('duration_api_ms'),
                   'total_cost_usd': final.get('total_cost_usd'), 'returncode': code}
        save(case/'generation.json', metrics)
        if timed_out:
            return {**metrics, 'status': 'timeout'}, events
        if code or final.get('is_error') or not final.get('result'):
            return {**metrics, 'status': 'inference_failed' if not judge else 'judge_failed'}, events
        (case/'output.txt').write_text(final['result'])
        return {**metrics, 'status': 'generated'}, events
    finally:
        if proxy:
            terminate(proxy)
        if proxy_log:
            proxy_log.close()


def prepare_mcp(config, account, job, case, base):
    auth = resolve(base, account['auth_file'])
    if not auth.is_file():
        raise ValueError('Figma OAuth file missing')
    file_key = node_json(config, 'harness-context.mjs', 'inference', case/'context.json')['file_key']
    mcp = case/'mcp.json'
    save(mcp, {'mcpServers': {'figma': {'command': sys.executable,
         'args': [str(SERVER/'figma_mcp_stdio_proxy.py')], 'env': {
         'FIGMA_MCP_AUTH_FILE': str(auth), 'FIGMA_MCP_ASSIGNED_FILE_KEY': file_key,
         'FIGMA_MCP_ALLOWED_TOOLS': 'whoami,get_metadata,use_figma,get_screenshot',
         'FIGMA_MCP_AWAIT_ASYNC_IIFE': '1', 'FIGMA_MCP_BUDGET_FILE': str(case/'mcp-budget.json')}}}})
    return mcp, file_key


def infer_one(config, job, model, account, case, base):
    from benchmark_artifact_compact import inspect_compact
    from benchmark_blank_screens import check_blank_screens
    from benchmark_frames import benchmark_product_frame, SCREEN_COUNT_RULE_VERSION
    from benchmark_screen_count import evaluate_named_screens
    query = resolve(base, job['query_file']).read_text()
    save(case/'context.json', {'query': query, 'figma_url': job['figma_url'], 'identity': account.get('identity')})
    context = node_json(config, 'harness-context.mjs', 'inference', case/'context.json')
    mcp, file_key = prepare_mcp(config, account, job, case, base)
    # Identity AND file locks cover independent scheduler processes as well.
    with lease('account:' + account.get('identity', str(resolve(base, account['auth_file']))).casefold()), lease('file:' + file_key):
        metrics, _ = run_cli(config, model, case, query, mcp=mcp, system_prompt=context['system_prompt'])
        if metrics['status'] != 'generated':
            return metrics
        save(case/'generation.json', metrics)
        # A separate deterministic read-only check. No model judges acceptance.
        async def inspect():
            return await asyncio.wait_for(inspect_compact(str(mcp), file_key), config.get('check_timeout_seconds', 600))
        inventory = asyncio.run(inspect())
        save(case/'screen-inventory.json', inventory)
        if job.get('required_screen_names'):
            count = evaluate_named_screens(inventory, job['required_screen_names'])
        else:
            actual = sum(benchmark_product_frame(n) for n in inventory['workspace']['children'])
            count = {'rule_version': SCREEN_COUNT_RULE_VERSION, 'expected': job['expected_screens'],
                     'actual': actual, 'passed': actual == job['expected_screens']}
        save(case/'screen-count.json', count)
        blank = asyncio.run(check_blank_screens(mcp, file_key, inventory, count, case,
                                                timeout=config.get('check_timeout_seconds', 600)))
        return {**metrics, 'status': 'success' if count['passed'] and blank['status']=='passed' else 'acceptance_failed',
                'file_key': file_key, 'screen_count': count, 'blank_screen_check': blank}


def judge_one(config, artifact, judge, repetition, case, base):
    from PIL import Image
    work = case/'work'
    work.mkdir()
    paths, proof = [], []
    for i, entry in enumerate(artifact['images'], 1):
        entry = {'path': entry} if isinstance(entry, str) else entry
        source = resolve(base, entry['path'])
        data = source.read_bytes()
        sha = digest(data)
        if entry.get('sha256') and entry['sha256'] != sha:
            raise ValueError('Frozen screenshot changed')
        with Image.open(source) as image:
            if image.format != 'PNG':
                raise ValueError('Judge inputs must be PNG screenshots')
            image.verify()
        dest = work/f'screen-{i:03d}.png'
        dest.write_bytes(data)
        paths.append(str(dest))
        proof.append({'file': dest.name, 'sha256': sha})
    context = {'query': resolve(base, artifact['query_file']).read_text(), 'images': paths,
               'layer_summary': read(resolve(base, artifact['layer_summary_file'])),
               'gate_policy': config['gate_policy']}
    save(case/'context.json', context)
    save(case/'input-proof.json', {'images': proof, 'query_sha256': digest(context['query'].encode()),
                                 'layer_summary_sha256': digest(json.dumps(context['layer_summary'],sort_keys=True).encode())})
    prompt = node_json(config, 'harness-context.mjs', 'judge', case/'context.json')['prompt']
    save(case/'empty-mcp.json', {'mcpServers': {}})
    metrics, events = run_cli(config, judge, case, prompt, mcp=case/'empty-mcp.json', judge=True)
    if metrics['status'] != 'generated':
        return metrics
    missing = sorted(set(paths)-opened_images(events))
    if missing:
        return {**metrics, 'status': 'incomplete_image_coverage', 'missing_images': missing}
    score = node_json(config, 'parse-harness-score.mjs', case/'output.txt', config['gate_policy'])
    return {**metrics, **score, 'status': 'completed', 'images_read': len(paths),
            'image_sha256': [p['sha256'] for p in proof], 'gate_policy': config['gate_policy'],
            'judge_id': judge['id'], 'repeat': repetition}


def validate(config, mode):
    if mode == 'judge' and config.get('gate_policy') not in ('required', 'disabled'):
        raise ValueError('Set explicit gate_policy: required or disabled')
    models = config.get('judges' if mode == 'judge' else 'models', [])
    ids = [identifier(m['id']) for m in models]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Unique model IDs required')
    for m in models:
        if not m.get('cli_model') or not m.get('base_url') or not m.get('api_key_env'):
            raise ValueError('Models require cli_model, base_url and api_key_env')
    if mode == 'judge':
        if len(models) != 3 or len({m.get('route_model',m['cli_model']) for m in models}) != 3:
            raise ValueError('Three distinct judge model routes required')
        if not isinstance(config.get('repetitions'), int) or config['repetitions'] < 1:
            raise ValueError('Positive independent repetition count required')
        rows = config['artifacts']
        for r in rows:
            if not r.get('images') or not r.get('layer_summary_file'):
                raise ValueError('All screenshots and a layer summary are required')
    else:
        accounts = config['accounts']
        account_ids = [identifier(a['id']) for a in accounts]
        if len(set(account_ids)) != len(account_ids):
            raise ValueError('Duplicate account ID')
        rows = config['jobs']
        urls = []
        for r in rows:
            if r['account_id'] not in account_ids or r['model_id'] not in ids:
                raise ValueError('Unknown account/model')
            if not isinstance(r['expected_screens'], int) or r['expected_screens'] < 1:
                raise ValueError('Positive expected_screens required')
            if r.get('required_screen_names') and len(r['required_screen_names']) != r['expected_screens']:
                raise ValueError('Required names must match expected screen count')
            match = re.search(r'^https://(?:www\.)?figma\.com/(?:design|file)/([A-Za-z0-9]+)(?:/|$)', r['figma_url'])
            if not match:
                raise ValueError('Expected assigned Figma copy URL')
            urls.append(match[1])
        if len(set(urls)) != len(urls):
            raise ValueError('Every job needs a distinct writable Figma copy')
    row_ids = [identifier(r['id']) for r in rows]
    if not rows or len(set(row_ids)) != len(row_ids):
        raise ValueError('Unique nonempty job/artifact IDs required')
    if not isinstance(config.get('concurrency', 1), int) or config.get('concurrency',1) < 1:
        raise ValueError('Positive concurrency required')


def worker(config_file, mode, row_id, case, judge_id=None, repetition=1):
    os.umask(0o077)
    config = read(config_file)
    base = Path(config_file).parent
    started = time.monotonic()
    case = Path(case).resolve()
    case.mkdir(parents=True, exist_ok=False)
    try:
        if mode == 'inference':
            job = next(r for r in config['jobs'] if r['id']==row_id)
            model = next(m for m in config['models'] if m['id']==job['model_id'])
            account = next(a for a in config['accounts'] if a['id']==job['account_id'])
            result = infer_one(config, job, model, account, case, base)
        else:
            artifact = next(r for r in config['artifacts'] if r['id']==row_id)
            judge = next(m for m in config['judges'] if m['id']==judge_id)
            result = judge_one(config, artifact, judge, repetition, case, base)
    except Exception as error:
        # Preserve metrics even if acceptance/score parsing fails after generation.
        metrics = read(case/'generation.json') if (case/'generation.json').exists() else {}
        # Exception messages may contain a remote body; store only the type here.
        result = {**metrics, 'status': 'error', 'error_type': type(error).__name__}
    result.update(id=row_id, mode=mode, judge_id=judge_id, repeat=repetition if judge_id else None,
                  total_duration_ms=round((time.monotonic()-started)*1000))
    save(case/'result.json', result)
    return result


def summarize_scores(config, results):
    rows = []
    for artifact in config['artifacts']:
        per_judge = []
        for judge in config['judges']:
            selected = [r for r in results if r['id']==artifact['id'] and r['judge_id']==judge['id']]
            scores = [r['score_total'] for r in selected if r['status']=='completed']
            complete = len(scores)==config['repetitions']
            per_judge.append({'judge_id': judge['id'], 'completed': len(scores), 'expected': config['repetitions'],
                              'mean': statistics.mean(scores) if complete else None,
                              'stddev': statistics.stdev(scores) if complete and len(scores)>1 else None})
        complete = all(r['mean'] is not None for r in per_judge)
        rows.append({'artifact_id':artifact['id'], 'judges':per_judge, 'complete':complete,
                     'mean_score':statistics.mean(r['mean'] for r in per_judge) if complete else None})
    return rows


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['inference', 'judge'])
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--worker-id', help=argparse.SUPPRESS)
    parser.add_argument('--judge-id', help=argparse.SUPPRESS)
    parser.add_argument('--repeat', type=int, default=1, help=argparse.SUPPRESS)
    args = parser.parse_args()
    config_file = args.config.resolve()
    config = read(config_file)
    validate(config, args.mode)
    if args.validate_only:
        print(json.dumps({'valid':True, 'mode':args.mode, 'network_calls':0}))
        return
    if args.worker_id:
        worker(config_file,args.mode,args.worker_id,args.output,args.judge_id,args.repeat)
        return
    run = args.output.resolve()/('batch-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    save(run/'manifest.json',{'framework':'claude-code','mode':args.mode,'configuration_sha256':digest(config_file.read_bytes()),
                             'historical_results_reused':False})
    results=[]
    def launch(item):
        row, judge_id, repeat = item
        name=row['id']+(f'--{judge_id}--r{repeat}' if judge_id else '')
        case=run/name
        argv=[sys.executable,str(Path(__file__).resolve()),args.mode,'--config',str(config_file),
              '--output',str(case),'--worker-id',row['id']]
        if judge_id:
            argv+=['--judge-id',judge_id,'--repeat',str(repeat)]
        code=subprocess.call(argv)
        if code or not (case/'result.json').exists():
            return {'id':row['id'],'judge_id':judge_id,'repeat':repeat,'status':'worker_failed'}
        return read(case/'result.json')
    if args.mode=='inference':
        # One sequential queue per account; account queues run concurrently.
        groups=[[r for r in config['jobs'] if r['account_id']==a['id']] for a in config['accounts']]
        def account_queue(rows):
            return [launch((r,None,1)) for r in rows]
        with ThreadPoolExecutor(max_workers=min(config.get('concurrency',len(groups)),len(groups))) as pool:
            for values in pool.map(account_queue,groups):
                results.extend(values)
                save(run/'results.json',results)
    else:
        items=[(a,j['id'],r) for a in config['artifacts'] for j in config['judges'] for r in range(1,config['repetitions']+1)]
        with ThreadPoolExecutor(max_workers=config.get('concurrency',8)) as pool:
            for value in pool.map(launch,items):
                results.append(value)
                save(run/'results.json',results)
        save(run/'scores.json',summarize_scores(config,results))
    print(json.dumps({'directory':str(run),'total':len(results),
                      'passed':sum(r['status'] in ('completed','success') for r in results)}))


if __name__=='__main__':
    main()
