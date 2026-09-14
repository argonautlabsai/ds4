#!/usr/bin/env python3
"""Build and run bounded reader/Engram fixtures against a supplied clean fork."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).parent/'lib'))
from ds41_benchmark import process_guard


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine-source',required=True,type=Path);p.add_argument('--sanitizers',choices=['address,undefined','undefined'],default='address,undefined');a=p.parse_args()
    source=a.engine_source.resolve();tests=Path(__file__).parent/'tests'
    if not (source/'argodrive_read.h').is_file() or not (source/'ds4_engram.c').is_file():p.error('Select the clean fork checkout.')
    cc=subprocess.check_output(['xcrun','--find','clang'],text=True).strip()
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    with Path('/tmp/argodrive-glm-campaign.lock').open('a+') as lock, tempfile.TemporaryDirectory(prefix='argodrive-reader-tests-') as tmp:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);process_guard()
        for name in ['test_argodrive_read','test_primary_nocache','test_engram_parallel']:
            binary=Path(tmp)/name
            cmd=[cc,'-O1','-g','-fblocks','-fsanitize='+a.sanitizers,'-fno-omit-frame-pointer','-I',str(source),'-isysroot',sdk,
                 str(tests/(name+'.c')),'-o',str(binary),'-pthread']
            subprocess.run(cmd,check=True)
            subprocess.run([str(binary)],check=True,timeout=90,env={k:v for k,v in os.environ.items() if not k.startswith(('DS4_','GLM_','K3_'))})
    print('PASS: reader and Engram fixtures with sanitizers='+a.sanitizers+'. No full-model or GPU inference was run.')


if __name__=='__main__':main()
