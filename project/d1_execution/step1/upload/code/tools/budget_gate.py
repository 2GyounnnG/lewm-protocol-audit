"""No launch: reject unknown throughput, projected over-cap, or accrued>=cap."""
import csv,json,argparse
from pathlib import Path
def forecast(rows,measurements,accrued=0,extra=0):
 total=float(accrued)+float(extra);details=[]
 for r in rows:
  if not float(r['units']):continue
  k=r['condition_id']
  if k not in measurements:raise ValueError('Missing measured throughput '+k)
  minutes=float(measurements[k]['upper_minutes_per_unit'])
  if not minutes>0:raise ValueError('Invalid throughput')
  hours=float(r['units'])*minutes/60;total+=hours;details.append(dict(condition=k,gpu_hours=hours))
 return dict(status='PASS' if total<=300 and accrued<300 else 'STOP_OVER_300',forecast_gpu_hours=total,conditions=details)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--measurements',required=True);p.add_argument('--accrued',type=float,default=0);p.add_argument('--extra',type=float,default=0);p.add_argument('--output',required=True);a=p.parse_args()
 r=forecast(list(csv.DictReader(open(a.plan,encoding='utf-8-sig'))),json.loads(Path(a.measurements).read_text()),a.accrued,a.extra);Path(a.output).write_text(json.dumps(r,indent=2))
 if r['status']!='PASS':raise SystemExit(2)
