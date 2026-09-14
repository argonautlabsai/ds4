"""Sequential same-request upstream/fork HTTP smoke and held-out equality.

No server performance headline. Malformed-request recovery is not disk-fault
recovery. All processes and temporary files belong to this test.
"""
import argparse,fcntl,hashlib,http.client,json,os,signal,socket,subprocess,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'lib'))
from model_support import ds41_fork_profile
from ds41_benchmark import process_guard,check_verification_receipt,digest,shader_identity,swap_used_mb

PROMPTS=[('code','Write only a Python function gcd(a, b) that returns the nonnegative greatest common divisor, including when either argument is zero or negative. Use Euclid\'s algorithm. Do not include Markdown fences.'),
 ('prose','Summarize the following in exactly two sentences, preserving all numbers and the limitation. A laboratory compared three SSD layouts. The final layout used one internal SSD and two external enclosures. It averaged 14.9 generated tokens per second on a 512-token answer. The test used one prompt and did not establish a public record.'),
 ('reasoning','A box contains 3 red balls and 2 blue balls. Two balls are drawn uniformly without replacement. What is the probability they have the same color? Give the reduced fraction and one sentence explaining your calculation.')]

def request(port,payload,stream=False):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=300)
    start=time.monotonic();first=None;parts=[];events=[]
    try:
        body=json.dumps({**payload,'stream':stream}).encode()
        conn.request('POST','/v1/chat/completions',body,{'Content-Type':'application/json'})
        resp=conn.getresponse()
        if resp.status!=200:raise RuntimeError(f'HTTP {resp.status}: '+resp.read(4096).decode(errors='replace'))
        if stream:
            done=False
            while True:
                line=resp.readline()
                if not line:break
                if not line.startswith(b'data: '):continue
                data=line[6:].strip()
                if data==b'[DONE]':done=True;break
                event=json.loads(data);events.append(event)
                for choice in event.get('choices',[]):
                    content=choice.get('delta',{}).get('content')
                    if content:
                        if first is None:first=time.monotonic()-start
                        parts.append(content)
            if not done:raise RuntimeError('Incomplete SSE response')
            text=''.join(parts)
        else:
            event=json.loads(resp.read());events.append(event);text=event['choices'][0]['message'].get('content','')
        if not text:raise RuntimeError('Empty held-out output')
        return {'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'events':events,
                'request_seconds':time.monotonic()-start,'first_content_seconds':first,
                'ttft_scope':'Client-observed first nonempty content delta; loaded persistent server; includes request prefill' if stream else None}
    finally:conn.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('model','receipt','upstream','candidate','out'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--replica',action='append',type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(exist_ok=False)
    model=args.model.resolve();replicas=[p.resolve() for p in args.replica]
    receipt=args.receipt.resolve()
    engines=[('upstream',args.upstream.resolve()),('clean-three-drive',args.candidate.resolve())]
    report={'status':'running','models':{},'scope':'Held-out chat output equality plus invalid-HTTP-request recovery, not read-failure recovery or publication qualification'}
    def save():(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();reference={}
    with Path('/tmp/argodrive-glm-campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            for label,engine in engines:
                process_guard();check_verification_receipt(receipt,model,replicas)
                with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
                argv=[str(engine),'--metal','-m',str(model),'--ssd-streaming','--ctx','4096','--host','127.0.0.1','--port',str(port),'--tokens','128','--power','100','--batched-session','1','--kv-disk-dir',str(out/(label+'-kv')),'--kv-disk-space-mb','256']
                env={k:v for k,v in os.environ.items() if not k.startswith(('DS4_','GLM_','K3_'))}
                if label!='upstream':
                    env.update(ds41_fork_profile(model,replicas)['environment'])
                    env.update(DS4_ARGODRIVE_REPLICAS=','.join(str(p)+'*1' for p in replicas),DS4_ARGODRIVE_PRIMARY_WEIGHT='2')
                rec={'argv':argv,'engine_sha256':digest(engine),'runtime_shader_sha256':shader_identity(engine),'requests':{},'swap':[],'experimental_environment':{k:v for k,v in env.items() if k.startswith('DS4_')}}
                report['models'][label]=rec;save();stop=threading.Event();fault=[];initial=swap_used_mb();proc=None;guard=None
                try:
                    with (out/(label+'.log')).open('w') as log:
                        proc=subprocess.Popen(argv,cwd=engine.parent,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                        began=time.monotonic()
                        def monitor():
                            while not stop.wait(2):
                                try:
                                    used=swap_used_mb();rec['swap'].append({'time':time.time(),'used_mb':used})
                                    if used-initial>256:raise RuntimeError('Swap growth exceeded256MiB')
                                    if time.monotonic()-began>1200:raise RuntimeError('Server test time bound reached')
                                except Exception as exc:
                                    fault.append(str(exc))
                                    if proc.poll() is None:os.killpg(proc.pid,signal.SIGTERM)
                                    return
                        guard=threading.Thread(target=monitor,daemon=True);guard.start()
                        ready=False
                        for _ in range(240):
                            if proc.poll() is not None:raise RuntimeError('Server exited before ready: '+str(fault))
                            try:
                                con=http.client.HTTPConnection('127.0.0.1',port,timeout=1);con.request('GET','/v1/models');res=con.getresponse();data=res.read();con.close()
                                if res.status==200 and json.loads(data).get('object')=='list':ready=True;break
                            except (OSError,http.client.HTTPException):pass
                            time.sleep(.5)
                        if not ready:raise RuntimeError('Server readiness timeout')
                        for name,prompt in PROMPTS:
                            payload={'model':'deepseek-chat','messages':[{'role':'user','content':prompt}],'temperature':0,'seed':42,'max_tokens':128}
                            rec['requests'][name]={'payload':payload,'response':request(port,payload,stream=True)};save()
                            response=rec['requests'][name]['response']
                            if label=='upstream':reference[name]=response['text']
                            elif response['text']!=reference[name]:raise RuntimeError('Held-out text differs: '+name)
                        con=http.client.HTTPConnection('127.0.0.1',port,timeout=10);con.request('POST','/v1/chat/completions',b'{invalid',{'Content-Type':'application/json'});res=con.getresponse();rec['invalid_request_status']=res.status;res.read();con.close()
                        if rec['invalid_request_status']!=400:raise RuntimeError('Malformed request was not rejected')
                        payload=rec['requests']['reasoning']['payload'];again=request(port,payload,stream=True);rec['requests']['reasoning-repeat']={'payload':payload,'response':again}
                        if again['text']!=reference['reasoning']:raise RuntimeError('Repeated request differs after malformed request')
                        if fault:raise RuntimeError('; '.join(fault))
                        rec['status']='complete';save()
                finally:
                    stop.set()
                    if guard:guard.join(timeout=5)
                    if proc and proc.poll() is None:
                        os.killpg(proc.pid,signal.SIGTERM)
                        try:proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                    rec['guard_errors']=fault;save()
            report['status']='complete';report['all_text_equal']=True;save()
        except BaseException as exc:
            report.update(status='stopped',error=str(exc));save();raise
if __name__=='__main__':main()
