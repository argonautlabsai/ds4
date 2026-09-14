#!/usr/bin/env python3
"""Reproduce one explicit DeepSeek arm; no automatic tuning or promotion."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from ds41_benchmark import plan, run
from model_support import ds41_fork_profile


def physical_map(paths):
    containers = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'apfs', 'list', '-plist']))['Containers']
    result = {}
    for label, path in paths:
        mount = Path(path).resolve().parent
        while mount.parent != mount and not os.path.ismount(mount):
            mount = mount.parent
        info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', str(mount)]))
        volume = info['DeviceIdentifier']
        matches = [c for c in containers if c['ContainerReference'] == info.get('APFSContainerReference') or
                   any(v['DeviceIdentifier'] == volume for v in c.get('Volumes', []))]
        if len(matches) != 1 or len(matches[0].get('PhysicalStores', [])) != 1:
            raise ValueError('Expected one APFS physical store for ' + str(path))
        store = matches[0]['PhysicalStores'][0]['DeviceIdentifier']
        store_info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', store]))
        result[label] = store_info['ParentWholeDisk']
    if len(set(result.values())) != len(result):
        raise ValueError('Sources must be on distinct physical SSDs.')
    return result


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('action', choices=['plan', 'run'])
    for name in ('engine', 'model', 'prompt', 'out'):
        a.add_argument('--'+name, required=True, type=Path)
    a.add_argument('--variant', choices=['upstream', 'fork'], required=True)
    a.add_argument('--replica', action='append', default=[], type=Path)
    a.add_argument('--receipt', type=Path)
    a.add_argument('--prompt-tokens', choices=[512, 2048], type=int, default=512)
    a.add_argument('--tokens', choices=[60, 128, 512], type=int, default=512)
    a.add_argument('--sampler', type=Path)
    a.add_argument('--accounting', action='store_true', help='Capture phase-boundary expert and Engram application bytes')
    a.add_argument('--timeout', type=int, default=1800)
    args = a.parse_args()
    if len(args.replica)>2 or (args.replica and args.variant=='upstream'):
        a.error('Only the fork supports replicas; choose at most two.')
    profile = ds41_fork_profile(args.model, args.replica)
    if profile['errors']:
        a.error('; '.join(profile['errors']))
    env = profile['environment'] if args.variant=='fork' else {'DS4_ARGODRIVE_PHASES':'1'}
    if args.accounting:
        if args.variant != 'fork': a.error('Accounting requires this fork build.')
        env['DS4_ARGODRIVE_ACCOUNTING'] = '1'
    # Harness validates and sets the actual replica paths after receipt checks.
    env = {k:v for k,v in env.items() if k not in ('DS4_ARGODRIVE_REPLICAS','DS4_ARGODRIVE_PRIMARY_WEIGHT')}
    p = plan(args.engine,args.model,args.prompt,args.out,args.prompt_tokens,args.tokens)
    if args.action == 'plan':
        print(json.dumps({**p, 'requested_variant':args.variant,
                          'requested_replicas':[str(x) for x in args.replica],
                          'requested_environment':env, 'launches_engine':False}, indent=2))
        return
    sources = [('internal',args.model), *[(f'enclosure{i}',p) for i,p in enumerate(args.replica,1)]]
    devices = physical_map(sources)
    result = run(p,timeout=args.timeout,replicas=args.replica,verification_receipt=args.receipt,
                 primary_weight=2,sampler_binary=args.sampler,devices=devices,
                 experimental_env=env,max_swap_growth_mb=256)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
