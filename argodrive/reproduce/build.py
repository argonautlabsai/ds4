#!/usr/bin/env python3
"""Build a fresh pinned upstream or experimental fork checkout on macOS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE='bd66c402070042bf0a79ad6ece8242de4c93680c'
ROOT=Path(__file__).resolve().parent.parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant',required=True,choices=['upstream','fork'])
    p.add_argument('--checkout',required=True,type=Path)
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args();checkout=a.checkout.resolve()
    if sys.platform!='darwin':p.error('This campaign build is qualified only for macOS Metal.')
    if checkout.exists() or not 1<=a.jobs<=16:p.error('Use a new checkout directory and 1–16 jobs.')
    candidate=ROOT/'clean-candidate'
    manifest=json.loads((candidate/'manifest.json').read_text())
    for name in ('candidate.patch','argodrive_read.h','argodrive_profile.h'):
        if hashlib.sha256((candidate/name).read_bytes()).hexdigest()!=manifest['files'][name]:
            raise ValueError('Candidate artifact changed: '+name)
    def call(args,**kw):subprocess.run(args,check=True,**kw)
    call(['git','clone','https://github.com/antirez/ds4.git',str(checkout)])
    call(['git','checkout','--detach',BASE],cwd=checkout)
    patch=candidate/'candidate.patch' if a.variant=='fork' else ROOT/'upstream-phase.patch'
    call(['git','apply','--check',str(patch)],cwd=checkout)
    call(['git','apply',str(patch)],cwd=checkout)
    if a.variant=='fork':
        for name in ('argodrive_read.h','argodrive_profile.h'):shutil.copy2(candidate/name,checkout/name)
    cc=subprocess.check_output(['xcrun','--find','clang'],text=True).strip()
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    env=dict(os.environ,SDKROOT=sdk)
    call(['make','-j'+str(a.jobs),'CC='+cc,'ds4-bench','ds4','ds4-server'],cwd=checkout,env=env)
    record={'variant':a.variant,'base_commit':BASE,'compiler':subprocess.check_output([cc,'--version'],text=True),
            'sdk':sdk,'binary_sha256':{n:hashlib.sha256((checkout/n).read_bytes()).hexdigest() for n in ('ds4-bench','ds4','ds4-server')},
            'note':'Local rebuild hashes may differ with toolchain and debug paths. Requalify; never substitute these for the recorded binary hashes.'}
    (checkout/'argodrive-build.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Built '+str(checkout)+'. No inference started.')


if __name__=='__main__':main()
