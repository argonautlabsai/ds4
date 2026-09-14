#!/usr/bin/env python3
"""Align routed-reader/Engram application counters with physical read windows.

The source counters exclude mmap/prefill paths and residency hits. A physical
minus application residual is disclosed, not attributed to cache without evidence.
"""
import argparse,json,re,subprocess,sys
from pathlib import Path

def reconcile(log,phases,labels):
    snapshots={name:list(map(int,values.split())) for name,values in
        re.findall(r'^ARGODRIVE_BYTES (\w+) ([0-9 ]+)$',log,re.M)}
    if any(len(v)!=4 for v in snapshots.values()):raise ValueError('Bad byte snapshot')
    result={}
    for phase in ('prefill','decode'):
        start=snapshots[phase+'_start'];end=snapshots[phase+'_end']
        delta=[b-a for a,b in zip(start,end)]
        if min(delta)<0:raise ValueError('Application counter reset')
        drives={}
        for i,label in enumerate(labels):
            physical=phases[phase]['drives'][label]
            application=delta[i]+(delta[3] if i==0 else 0)
            drives[label]={'routed_reader_bytes':delta[i],'engram_read_bytes':delta[3] if i==0 else 0,
                'instrumented_application_bytes':application,'physical_read_bytes_estimate':physical['read_gb']*1e9,
                'physical_minus_instrumented_bytes':physical['read_gb']*1e9-application,
                'physical_read_bytes_bounds':[x*1e9 for x in physical['read_gb_bounds']]}
        result[phase]={'seconds':phases[phase]['seconds'],'drives':drives,
            'scope':'Matched phase window; routed reader and Engram successful pread bytes only. Excludes mmap/prefill loads, cache hits, metadata and unrelated processes. Physical-minus-instrumented residual is unassigned.'}
    final={int(i):int(n) for i,n in re.findall(r'^ds4: Argodrive source\[(\d+)\] bytes=(\d+)$',log,re.M)}
    closure=all(final.get(i)==snapshots['decode_end'][i] for i in range(len(labels)))
    first=re.search(r'^ARGODRIVE_FIRST_TOKEN_READY ([0-9.]+) ([0-9.]+)$',log,re.M)
    return {'application_counter_closure':closure,'physical_attribution_complete':False,'phases':result,
        'prefill_to_first_token_selection_seconds':float(first[2])-float(first[1]) if first else None,
        'timing_scope':'Loaded benchmark, prompt sync to first argmax selection; excludes HTTP and model startup.',
        'physical_gate':'Residuals measured, causes unestablished; do not claim exact physical attribution.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('arm',type=Path);a=p.parse_args()
    subprocess.run([sys.executable,str(Path(__file__).with_name('analyze-phases.py')),str(a.arm)],check=True,stdout=subprocess.DEVNULL)
    plan=json.loads((a.arm/'plan.json').read_text());phases=json.loads((a.arm/'phase-analysis.json').read_text())
    result=reconcile((a.arm/'baseline.engine.txt').read_text(),phases,list(plan['physical_devices']))
    (a.arm/'byte-reconciliation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
