#!/usr/bin/env python3
"""Read each complete model once and write a local, file-identity-bound receipt."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).parent/'lib'))
from ds41_benchmark import digest, file_identity, process_guard
from model_support import DS41_Q4_BYTES, DS41_Q4_SHA256


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',required=True,type=Path)
    p.add_argument('--replica',action='append',default=[],type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    if len(a.replica)>2 or a.out.exists():p.error('At most two replicas and a new receipt path are required.')
    paths=[x.resolve() for x in [a.model,*a.replica]]
    if len(set(paths))!=len(paths):p.error('Choose distinct files.')
    records=[]
    with Path('/tmp/argodrive-glm-campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);process_guard()
        for path in paths:
            before=file_identity(path)
            if not path.is_file() or path.stat().st_size!=DS41_Q4_BYTES:raise ValueError('Wrong model size: '+str(path))
            print('Reading full SHA-256: '+str(path),flush=True)
            sha=digest(path)
            if file_identity(path)!=before or sha!=DS41_Q4_SHA256:raise ValueError('Model changed or checksum mismatch: '+str(path))
            mount=path.parent
            while mount.parent!=mount and not os.path.ismount(mount):mount=mount.parent
            info=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist',str(mount)]))
            records.append({'path':str(path),'identity':before,'sha256':sha,'volume_uuid':info.get('VolumeUUID')})
        with a.out.open('x') as f:json.dump({'source':records[0],'replicas':records[1:]},f,indent=2);f.write('\n')
    print('Receipt written. This does not qualify performance or model quality.')


if __name__=='__main__':main()
