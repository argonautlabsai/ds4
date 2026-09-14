"""Render the frozen campaign, keeping it separate from fresh-clone results."""
import json,statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent
rows=json.loads((root.parent/'frozen-summary.json').read_text())['runs']
variants=['upstream','fork-internal','fork-plus1','fork-plus2']
labels=['Upstream ds4 · internal','Argodrive fork · internal','Argodrive fork · +1 enclosure','Argodrive fork · +2 enclosures']
values=[];ranges=[]
for v in variants:
    data=[r['generation_tok_s'] for r in rows if r['variant']==v and r['prompt_tokens']==512 and r['generated_tokens']==512]
    assert len(data)==3 and all(n>0 for n in data)
    median=statistics.median(data);values.append(median);ranges.append((median-min(data),max(data)-median))
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','font.size':11})
fig,ax=plt.subplots(figsize=(11.8,5.6),dpi=170)
fig.set_facecolor('#f7f9fc');ax.set_facecolor('#f7f9fc')
colors=['#64748b','#4387af','#237aac','#087f72']
y=list(range(4));ax.barh(y,values,height=.53,color=colors,zorder=3)
ax.errorbar(values,y,xerr=[[r[0] for r in ranges],[r[1] for r in ranges]],fmt='none',ecolor='#172331',capsize=5,lw=1.5,zorder=4)
for i,v in enumerate(values):ax.text(v+.45,i,f'{v:.2f}',va='center',fontweight='bold',fontsize=15,color='#172331')
ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlim(0,18);ax.set_xticks([0,3,6,9,12,15,18]);ax.set_xlabel('Generated tokens / second — including the first decode step',labelpad=12)
ax.xaxis.grid(True,color='#dce3eb',zorder=0);ax.tick_params(axis='both',length=0,pad=9,colors='#334155')
for spine in ax.spines.values():spine.set_visible(False)
fig.text(.03,.93,'DeepSeek V4.1 Flash Q4 · historical matched comparison',fontsize=18,fontweight='bold',color='#122033')
fig.text(.03,.873,'M5 Max · 128 GiB · 512 prompt tokens / 512 generated tokens',fontsize=12,color='#526174')
fig.text(.03,.115,'Bars: median of 3 runs. Whiskers: observed min–max. Same prompt and model.',fontsize=10,color='#526174')
fig.text(.03,.067,'Historical campaign, not a fresh-clone result or portable speed guarantee. Publication gates remain open.',fontsize=10,color='#526174')
fig.text(.03,.023,'Engine: antirez/ds4 and contributors. Experimental reader and scheduling: Argonaut Labs.',fontsize=9,color='#526174')
fig.subplots_adjust(left=.30,right=.95,bottom=.25,top=.79)
fig.savefig(root/'v41-historical-inclusive.svg',metadata={'Date':None})
fig.savefig(root/'v41-historical-inclusive.png',metadata={'Software':'Matplotlib'})
print(dict(zip(variants,values)))
