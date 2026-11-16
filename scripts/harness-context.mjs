import fs from 'node:fs';
import {benchmarkDesignSystemPrompt,benchmarkDesignTarget} from '../server/benchmark_design.mjs';
import {getScaleMethod} from '../server/fixed_scales/index.mjs';
import {buildFixed20Prompt} from '../server/fixed20_scale.mjs';
const [mode,file]=process.argv.slice(2), input=JSON.parse(fs.readFileSync(file,'utf8'));
if(mode==='inference') {
  const target=benchmarkDesignTarget(input.query,input.figma_url);
  console.log(JSON.stringify({file_key:target.fileKey,system_prompt:benchmarkDesignSystemPrompt({identity:input.identity},target)}));
} else if(mode==='judge') {
  const def=getScaleMethod('fixed_v4');
  let prompt=buildFixed20Prompt(def.prompt_template,{query:input.query,
    imageBlock:input.images.map((p,i)=>`第 ${i+1} 屏：${p}`).join('\n'),
    layerSummary:input.layer_summary,questions:def.questions,layerLabel:def.layer_label,layerHints:def.layer_hints});
  if(input.gate_policy==='disabled') {
    const start=prompt.indexOf('二、G0 是前置门槛，不计分'),end=prompt.indexOf('三、A1~F5 分档打分',start);
    if(start<0||end<start)throw Error('Cannot safely remove G0 instructions');
    prompt=prompt.slice(0,start)+'二、评分方式\n对全部 22 项逐项打分；没有前置门槛，总分直接加总，满分 53 分。\n\n'+prompt.slice(end);
    prompt=prompt.replace('某张图打不开，就在 G0 里说明，并在受影响的题目证据里注明「第 N 屏无法读取」。','某张图无法辨认，就在受影响的题目证据里注明「第 N 屏无法辨认」。')
      .replace('只有确实没有收到或无法辨认的图像，才按下方 G0 和量表判定。','只有确实没有收到或无法辨认的图像，才在相关量表项证据中说明并按分档判定。')
      .replace(/^\s*"g0":\s*\{[^\n]*\},?\r?\n/gmi,'');
    if(/\bG0\b/i.test(prompt))throw Error('Unexpected G0 instruction');
  } else if(input.gate_policy!=='required')throw Error('Explicit gate_policy required');
  console.log(JSON.stringify({prompt:'Use Read to open EVERY image listed below before scoring. Text summaries are not substitutes for reading images.\n'+prompt}));
} else throw Error('Unknown context mode');
