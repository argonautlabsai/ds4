from pathlib import Path
import csv,json,re,bisect,sys
out=Path(sys.argv[1]);plan=json.loads((out/'plan.json').read_text())
start=re.search(r'ARGODRIVE_SAMPLER_START_MONO ([0-9.]+)',(out/'sampler.out').read_text())
if not start:raise RuntimeError('No sampler monotonic origin')
origin=float(start[1]);log=(out/'baseline.engine.txt').read_text()
phases={name:(float(a)-origin,float(b)-origin) for name,a,b in re.findall(r'^ARGODRIVE_PHASE (\w+) ([0-9.]+) ([0-9.]+)$',log,re.M)}
rows=list(csv.DictReader((out/'baseline.csv').open()));result={}
for phase,(a,b) in phases.items():
 record={'seconds':b-a,'window_relative_s':[a,b],'drives':{},'scope':'Physical device reads, including other processes; linear boundary estimate with adjacent-sample bounds.'}
 for label,dev in plan['physical_devices'].items():
  points=[(float(r['t_s']),int(r['v1'])) for r in rows if r['dev']==dev]
  ts=[x[0] for x in points]
  if any(points[i][1]<points[i-1][1] for i in range(1,len(points))):raise RuntimeError('Counter reset')
  def at(t):
   right=bisect.bisect_right(ts,t)
   if right==0 or right==len(ts):raise RuntimeError('Phase boundary outside sampler interval')
   t0,v0=points[right-1];t1,v1=points[right]
   return v0+(v1-v0)*(t-t0)/(t1-t0),v0,v1
  va,alo,ahi=at(a);vb,blo,bhi=at(b);n=vb-va
  record['drives'][label]={'read_gb':n/1e9,'gb_s':n/1e9/(b-a),'read_gb_bounds':[max(0,blo-ahi)/1e9,(bhi-alo)/1e9]}
 record['total_gb_s']=sum(v['gb_s'] for v in record['drives'].values())
 if phase=='decode':record['physical_gb_per_token']=sum(v['read_gb'] for v in record['drives'].values())/plan['generated_tokens']
 result[phase]=record
(out/'phase-analysis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
