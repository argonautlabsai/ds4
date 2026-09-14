#!/usr/bin/env python3
"""Generate tables and publication figures from all 30 qualification arms."""
import argparse
import csv
import json
from pathlib import Path
import statistics as st

LABELS={'upstream':'Upstream · internal','fork-internal':'Fork · internal',
        'fork-plus1':'Fork · internal + Green','fork-plus2':'Fork · internal + Green + White'}
COLORS={'upstream':'#697586','fork-internal':'#22759b','fork-plus1':'#278365','fork-plus2':'#b96923'}


def summarize(q):
    if q['status']!='complete' or len(q['runs'])!=30 or not all(r['output_matches_upstream'] for r in q['runs']):
        raise ValueError('A complete, output-matched 30-arm matrix is required.')
    groups={}
    for r in q['runs']:
        key=(r['variant'],r['prompt_tokens'],r['generated_tokens'])
        groups.setdefault(key,[]).append(r)
    result=[]
    for (variant,pp,tg),arms in groups.items():
        if len(arms)!=3 or sorted(a['repetition'] for a in arms)!=[1,2,3]:raise ValueError('Missing or duplicate repetition')
        item={'variant':variant,'prompt_tokens':pp,'generated_tokens':tg,'repetitions':3}
        for field in ('generation_tok_s','steady_tok_s','prefill_tok_s','first_decode_step_ms'):
            values=[a['result'][field] for a in arms]
            item[field]={'median':st.median(values),'min':min(values),'max':max(values),'values':values}
        baseline={a['repetition']:a for a in groups[('upstream',pp,tg)]}
        gains=[100*(a['result']['generation_tok_s']/baseline[a['repetition']]['result']['generation_tok_s']-1) for a in arms]
        item['paired_generation_gain_percent']={'median':st.median(gains),'min':min(gains),'max':max(gains),'values':gains}
        item['decode_physical_gb_s_by_drive']={d:st.mean(a['phase_analysis']['decode']['drives'][d]['gb_s'] for a in arms) for d in ('internal','Green','White')}
        item['decode_physical_gb_per_token']=st.mean(a['phase_analysis']['decode']['physical_gb_per_token'] for a in arms)
        result.append(item)
    return result,groups


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('pack',type=Path);args=a.parse_args();root=args.pack.resolve()
    q=json.loads((root/'evidence/qualification.json').read_text());summary,groups=summarize(q)
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    def group(v,pp,tg):return next(x for x in summary if (x['variant'],x['prompt_tokens'],x['generated_tokens'])==(v,pp,tg))
    lines=['# DeepSeek V4.1 Flash Q4 — controlled local results','',
           'M5 Max, 128 GiB unified memory. One fixed raw-completion prompt, automatic expert cache, 4096 context allocation, no speculation. Three fresh-process repetitions per cell, rotated order. Q4 weights and output text are unchanged.','',
           'Generation includes the first decode step. Ranges show all three runs; they are not confidence intervals. Prompt processing is measured separately.','',
           '| Configuration | 128 tokens: median [range] | 512 tokens: median [range] | 512 gain vs upstream, paired median [range] |',
           '|---|---:|---:|---:|']
    for v,label in LABELS.items():
        a128=group(v,512,128);a512=group(v,512,512)
        def val(x):return f'{x["median"]:.2f} [{x["min"]:.2f}–{x["max"]:.2f}]'
        gain=a512['paired_generation_gain_percent']
        lines.append(f'| {label} | {val(a128["generation_tok_s"])} | {val(a512["generation_tok_s"])} | {gain["median"]:+.1f}% [{gain["min"]:+.1f}–{gain["max"]:+.1f}%] |')
    best=group('fork-plus2',512,512);internal=group('fork-internal',512,512)
    enclosure_gain=100*(best['generation_tok_s']['median']/internal['generation_tok_s']['median']-1)
    lines+=['',f'Two enclosures add **{enclosure_gain:.1f}%** over the optimized fork on the internal SSD, using the ratio of medians. The overall comparison also includes engine changes; it is not all a storage gain.',
            '',f'The target was 25 generation tok/s; the qualified three-drive median is **{best["generation_tok_s"]["median"]:.2f} tok/s**. The target was not reached. This experiment does not establish a public speed record.',
            '', '## Prompt processing','', '| Prompt tokens | Configuration | Prefill tok/s: median [range] |','|---:|---|---:|']
    for pp,tg,vs in [(512,512,LABELS),(2048,60,['upstream','fork-plus2'])]:
        for v in vs:lines.append(f'| {pp} | {LABELS[v]} | {val(group(v,pp,tg)["prefill_tok_s"])} |')
    lines+=['','The 512-token prefill table uses the three 512-generation arms per configuration. All other prefill observations remain in results.csv. A first decode-step timer is not client time to first response.',
            '', '## Scope and limits','',
            '- A fresh process resets the application cache; no OS page-cache purge is claimed. The fixed prefill warms the cache before generation.',
            '- All 30 performance outputs match their upstream reference for the same prompt and output length. Separate code, prose and reasoning chat outputs also match, but this is a small smoke suite, not a comprehensive quality benchmark.',
            '- The reasoning response gives the correct 2/5 result but exceeds the requested one-sentence format. Both engines do this.',
            '- A test-only genuine half-read followed by EOF rejects a streamed request with a clean prefix, then the same and an unrelated prompt recover exactly on the persistent server. This is one injected failure case, not every lifecycle path.',
            '- Physical-device graphs include other processes on those devices. Phase boundaries use interpolation and adjacent-sample bounds. Whole-arm application expert bytes have a different scope.',
            '- The per-encoder GPU trace is intrusive: it changes encoding boundaries and slows inference. Its section timings rank candidates but are not production critical-path fractions or an upper speed bound.',
            '- Earlier screening had substantial control drift. A separate model copy overlapped one rejected prefetch arm, not this final matrix. All final qualification arms are retained.',
            '- The build is experimental and local. No CUDA inference, comprehensive long-context quality suite, multi-client server qualification or independent hardware replication is claimed.',
            '', 'See reproduce/README.md for exact build and run commands, evidence/ for sanitized logs, and provenance.json for original and sanitized artifact hashes.']
    (root/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','savefig.facecolor':'white'})
    plots=root/'figures';plots.mkdir(exist_ok=True)
    def save(fig,name):
        fig.savefig(plots/(name+'.png'),dpi=180,bbox_inches='tight');fig.savefig(plots/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),sharey=True)
    for ax,tg in zip(axes,[128,512]):
        for i,v in enumerate(LABELS):
            m=group(v,512,tg)['generation_tok_s'];ax.barh(i,m['median'],color=COLORS[v],height=.55)
            ax.errorbar(m['median'],i,xerr=[[m['median']-m['min']],[m['max']-m['median']]],fmt='none',ecolor='#17202a',capsize=4)
            ax.scatter(m['values'],[i]*3,s=20,color='white',edgecolor='#17202a',zorder=5)
            ax.text(m['max']+.35,i,f'{m["median"]:.2f}',va='center',weight='bold')
        ax.axvline(25,color='#9c3434',linestyle='--',linewidth=1);ax.text(25,.04,'25 target',rotation=90,ha='right',va='bottom',transform=ax.get_xaxis_transform(),color='#9c3434')
        ax.set_xlim(0,27);ax.set_yticks(range(4),list(LABELS.values()));ax.set_title(f'{tg} generated tokens');ax.set_xlabel('Generation tokens / second');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    axes[0].invert_yaxis();fig.suptitle('DeepSeek V4.1 Flash Q4 · M5 Max 128 GiB',fontsize=15,weight='bold');fig.text(.5,.01,'512-token prompt · median, full range and three individual runs · includes first decode step',ha='center',fontsize=9);fig.tight_layout(rect=[0,.05,1,.94]);save(fig,'generation')
    fig,ax=plt.subplots(figsize=(10,4.5));bottom=np.zeros(4)
    for d,color in [('internal','#22759b'),('Green','#278365'),('White','#b96923')]:
        values=[group(v,512,512)['decode_physical_gb_s_by_drive'][d] for v in LABELS]
        ax.bar(range(4),values,bottom=bottom,label=d,color=color,width=.6);bottom+=values
    for i,n in enumerate(bottom):ax.text(i,n+.08,f'{n:.2f}',ha='center',weight='bold')
    ax.set_xticks(range(4),['Upstream\ninternal','Fork\ninternal','Fork\n+ Green','Fork\n+ Green + White']);ax.set_ylim(0,max(bottom)*1.25);ax.set_ylabel('Physical reads · decimal GB/s');ax.set_title('SSD reads during 512-token generation');ax.legend(frameon=False,ncol=3);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True);fig.text(.5,.01,'Mean of three decode windows · physical counters can include other processes · not device ceilings',ha='center',fontsize=9);fig.tight_layout(rect=[0,.05,1,1]);save(fig,'drive-contribution')
    representative=sorted(groups[('fork-plus2',512,512)],key=lambda x:x['result']['generation_tok_s'])[1]
    folder=root/'evidence/arms'/representative['tag'];plan=json.loads((folder/'plan.json').read_text());phase=representative['phase_analysis']['decode'];start,end=phase['window_relative_s']
    with (folder/'baseline.csv').open() as f:rows=list(csv.DictReader(f))
    fig,ax=plt.subplots(figsize=(11,4.2))
    for label,color in [('internal','#22759b'),('Green','#278365'),('White','#b96923')]:
        points=[(float(r['t_s']),int(r['v1'])) for r in rows if r['dev']==plan['physical_devices'][label]]
        rates=[((a[0]+b[0])/2-start,(b[1]-a[1])/(b[0]-a[0])/1e9) for a,b in zip(points,points[1:]) if start<=a[0]<b[0]<=end]
        ax.plot([x for x,y in rates],[y for x,y in rates],label=label,color=color,linewidth=1,alpha=.85)
    ax.set_xlim(0,end-start);ax.set_ylim(bottom=0);ax.set_xlabel('Seconds from decode start');ax.set_ylabel('Physical reads · decimal GB/s');ax.set_title('Three-drive decode · median-speed 512-token repetition');ax.legend(frameon=False,ncol=3);ax.grid(alpha=.15);fig.text(.5,.01,'100 ms counter intervals · selected by median generation speed, not by maximum SSD draw',ha='center',fontsize=9);fig.tight_layout(rect=[0,.05,1,1]);save(fig,'drive-timeline')
    print(json.dumps({'three_drive_tg512':best['generation_tok_s'],'enclosure_gain_percent':enclosure_gain,'representative_arm':representative['tag']},indent=2))


if __name__=='__main__':main()
