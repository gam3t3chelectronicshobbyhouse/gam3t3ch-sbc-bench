"""Sustained stock-setting CPU load with measured SHA-256 throughput and telemetry."""
import concurrent.futures
import datetime
import hashlib
import os
from pathlib import Path
import ssl
import threading
import time
import webbrowser
from . import VERSION
from .system import hardware
from .scoring import scores
from .report import export_report
LOAD_ID='cpu-load-sha256-0.1'

def worker(stop, deadline):
    block=bytes(range(256))*1024
    expected=hashlib.sha256(block).digest()
    count=0
    while not stop.is_set() and time.monotonic()<deadline:
        if hashlib.sha256(block).digest()!=expected:raise RuntimeError('Digest consistency check failed')
        count+=1
    return count*len(block)

def run_load(args):
    from .__main__ import atomic_json
    from .full import ContinuousTelemetry
    seconds=getattr(args,'load_seconds',60)
    workers=getattr(args,'workers',None) or min(os.cpu_count() or 1,8)
    if not 1<=seconds<=600 or not 1<=workers<=64:raise ValueError('Load duration must be 1–600 seconds and workers 1–64')
    folder=Path(args.output).resolve()/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'-load-'+os.urandom(3).hex());folder.mkdir(parents=True)
    data={'schema_version':2,'benchmark_version':VERSION,'workload_id':LOAD_ID,'run_id':folder.name,'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hardware':hardware(),'configuration':{'mode':'load','workers':workers,'seconds':seconds,'openssl':ssl.OPENSSL_VERSION,'label':getattr(args,'label','Stock baseline'),'notes':getattr(args,'notes','')},'classification':'CPU_LOAD','status':'running','stage':'Sustained CPU / SHA256','results':{},'test_status':{},'telemetry':[],'errors':{},'scores':scores({}),'power':None,'comparison_eligible':False}
    session=getattr(args,'_session',None);owned=session is None;started=time.monotonic()
    if owned:
        session=ContinuousTelemetry(data);session.prefix='Sustained CPU / SHA256';session.thread.start()
    else:session.attach(data,started)
    session.sample();stop=threading.Event();code=0
    pool=concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    try:
        load_started=time.monotonic();deadline=load_started+seconds
        futures=[pool.submit(worker,stop,deadline) for _ in range(workers)]
        while time.monotonic()<deadline:
            for future in futures:
                if future.done():future.result()
            time.sleep(min(0.2,max(0,deadline-time.monotonic())))
        counts=[f.result() for f in futures];wall=time.monotonic()-load_started
        data['results']['load']={'workload_id':LOAD_ID,'bytes':sum(counts),'seconds':wall,'mb_s':sum(counts)/wall/1e6,'workers':workers,'worker_bytes':counts,'digest_consistency':'passed','openssl':ssl.OPENSSL_VERSION}
        data['status']='complete';data['test_status']['load']={'status':'passed','reason':'Sustained parallel SHA-256 completed. Throughput is separate from baseline scoring; not a full hardware stability certification.'}
    except KeyboardInterrupt:
        code=130;data['status']='interrupted';data['test_status']['load']={'status':'interrupted','reason':'Stopped by user'}
    except Exception as exc:
        code=1;data['status']='partial';data['errors']['load']=str(exc);data['test_status']['load']={'status':'failed','reason':str(exc)}
    finally:
        stop.set();pool.shutdown(wait=True);session.close() if owned else session.sample()
        data['duration_seconds']=time.monotonic()-started;data['stage']=data['status'].title()
        temps=[s['temperature_c'] for s in data['telemetry'] if s.get('temperature_c') is not None]
        data['thermal_summary']={'peak_c':max(temps,default=None),'start_c':temps[0] if temps else None,'end_c':temps[-1] if temps else None}
        atomic_json(folder/'result.json',data);export_report(data,folder/'report.html')
    if args.open:webbrowser.open((folder/'report.html').as_uri())
    return code
