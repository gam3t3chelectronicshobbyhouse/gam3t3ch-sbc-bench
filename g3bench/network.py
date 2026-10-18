"""Explicit, bounded HTTP transfer measurements; no result upload or idle traffic."""
import argparse
import datetime
import json
import os
from pathlib import Path
import statistics
import math
import re
import shutil
import subprocess
import time
import urllib.request
import webbrowser
from . import VERSION
from .system import hardware, Sampler
from .scoring import scores
from .report import export_report
NETWORK_ID='network-http-0.1'
ENDPOINT='https://speed.cloudflare.com'

def transfer(url, payload=None):
    started=time.monotonic()
    req=urllib.request.Request(url,data=payload,headers={'User-Agent':'GAM3T3CH-Benchmark/0.5','Cache-Control':'no-cache','Content-Type':'application/octet-stream'})
    with urllib.request.urlopen(req,timeout=20) as response:
        first=time.monotonic()
        received=0
        while True:
            chunk=response.read(65536)
            if not chunk:break
            received+=len(chunk)
    seconds=time.monotonic()-started
    count=len(payload) if payload is not None else received
    return {'bytes':count,'seconds':seconds,'mbps':count*8/max(seconds,1e-9)/1e6,'response_start_ms':(first-started)*1000}

def measure(stage,sample):
    latencies=[];trials=[];errors=[]
    for i in range(5):
        stage('NETWORK / HTTP response latency')
        try:latencies.append(transfer(ENDPOINT+'/__down?bytes=0')['response_start_ms'])
        except Exception as exc:errors.append(str(exc))
        sample()
    for direction in ('download','upload'):
        for i in range(3):
            stage('NETWORK / '+direction+' '+str(i+1)+'/3')
            try:
                size=4*1024*1024 if direction=='download' else 2*1024*1024
                trial=transfer(ENDPOINT+'/__down?bytes='+str(size)) if direction=='download' else transfer(ENDPOINT+'/__up',os.urandom(size))
                if direction=='download' and trial['bytes']!=size:raise ValueError('Incomplete download')
                trials.append({'direction':direction,'trial':i+1,**trial})
            except Exception as exc:errors.append(direction+': '+str(exc))
            sample()
    result={'endpoint':ENDPOINT,'method':'single-request HTTPS; includes connection/TLS/response overhead; not line-rate capacity',
            'latency_kind':'HTTP response start, not ICMP ping','latency_ms':statistics.median(latencies) if latencies else None,
            'latency_variation_ms':statistics.pstdev(latencies) if latencies else None,'latency_samples_ms':latencies,'trials':trials,'errors':errors}
    for direction in ('download','upload'):
        group=[r for r in trials if r['direction']==direction]
        result[direction+'_mbps']=sum(r['bytes']*8 for r in group)/sum(r['seconds'] for r in group)/1e6 if group else None
    result['status']='passed' if len(trials)==6 and len(latencies)==5 else 'partial'
    return result

def measure_iperf(host,stage,sample,port=5201):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]{0,252}',host):raise ValueError('Invalid iperf host')
    if type(port) is not int or not 1<=port<=65535:raise ValueError('Invalid iperf port')
    engine=shutil.which('iperf3')
    if not engine:return {'status':'unavailable','endpoint':host,'method':'iperf3 TCP / 10 seconds each direction','reason':'Install iperf3 on each machine and run iperf3 -s on the peer.','trials':[],'errors':[]}
    result={'endpoint':host,'method':'iperf3 TCP / 10 seconds each direction','trials':[],'errors':[]}
    for direction,flags in [('upload',[]),('download',['--reverse'])]:
        stage('NETWORK / iperf3 '+direction)
        try:
            p=subprocess.run([engine,'--client',host,'--port',str(port),'--json','--time','10',*flags],capture_output=True,text=True,timeout=35)
            raw=json.loads(p.stdout)
            if p.returncode or raw.get('error'):raise RuntimeError(raw.get('error') or p.stderr)
            rate=raw['end']['sum_received']['bits_per_second']/1e6
            if not math.isfinite(rate) or rate<=0:raise ValueError('Invalid receiver rate')
            result[direction+'_mbps']=rate;result['trials'].append({'direction':direction,'mbps':rate,'iperf3':raw})
        except (OSError,ValueError,KeyError,RuntimeError,subprocess.SubprocessError) as exc:result['errors'].append(str(exc))
        sample()
    result['status']='passed' if len(result['trials'])==2 else 'partial'
    return result


def run_network(args):
    from .__main__ import atomic_json
    if not getattr(args,'allow_network',False):raise ValueError('Network test contacts Cloudflare and transfers about 18 MiB. Use --allow-network to acknowledge data usage and the external IP-visible endpoint.')
    folder=Path(args.output).resolve()/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'-network-'+os.urandom(3).hex());folder.mkdir(parents=True)
    data={'schema_version':2,'benchmark_version':VERSION,'workload_id':NETWORK_ID,'run_id':folder.name,'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hardware':hardware(),'configuration':{'mode':'network','endpoint':getattr(args,'iperf_host',None) or ENDPOINT,'label':getattr(args,'label','Stock baseline'),'notes':getattr(args,'notes','')},'classification':'NETWORK','status':'running','stage':'Network preflight','results':{},'test_status':{},'telemetry':[],'errors':{},'scores':scores({}),'power':None,'comparison_eligible':False}
    session=getattr(args,'_session',None);started=time.monotonic();owned=session is None
    if owned:
        from .full import ContinuousTelemetry
        session=ContinuousTelemetry(data);session.thread.start()
    if not owned:session.attach(data,started)
    def sample():
        return session.sample()
    def stage(value):
        data['stage']=value
        if owned:session.prefix=value
    code=0
    try:
        result=measure_iperf(args.iperf_host,stage,sample,getattr(args,'iperf_port',5201)) if getattr(args,'iperf_host',None) else measure(stage,sample);data['results']['network']=result;data['status']='complete' if result['status']=='passed' else 'partial'
        data['test_status']['network']={'status':result['status'],'reason':result.get('reason','Send/receive trials; server/path conditions affect results.')}
    except KeyboardInterrupt:
        data['status']='interrupted';data['test_status']['network']={'status':'interrupted','reason':'Stopped by user'};code=130
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        code=1;data['status']='partial';data['errors']['network']=str(exc);data['test_status']['network']={'status':'failed','reason':str(exc)}
    finally:
        session.close() if owned else sample();data['duration_seconds']=time.monotonic()-started;data['stage']=data['status'].title();atomic_json(folder/'result.json',data);export_report(data,folder/'report.html')
    if args.open:webbrowser.open((folder/'report.html').as_uri())
    return code
