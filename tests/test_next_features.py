import argparse
import json
from pathlib import Path
import tempfile
import os
import shutil
import socket
import subprocess
import time
import unittest
from unittest.mock import patch
from g3bench.diagnostics import test_profile, advice
from g3bench.network import measure, measure_iperf, run_network
from g3bench.load import run_load
from g3bench.storage import fio_command, measure_drive, MIB
ROOT=Path(__file__).resolve().parents[1]
class FeatureTests(unittest.TestCase):
    def test_display_paced_gpu_is_measured_but_not_scored(self):
        from g3bench.scoring import scores
        gpu={'width':1280,'height':720,'vsync':True,'scenes':[{'average_fps':60}]*5}
        self.assertIsNone(scores({'gpu':gpu})['gpu'])
        gpu['vsync']=False
        self.assertIsNotNone(scores({'gpu':gpu})['gpu'])
    def test_board_profiles_do_not_invent_board_specific_scores(self):
        self.assertEqual(test_profile({'architecture':'armv6l'},'auto')['name'],'legacy')
        self.assertEqual(test_profile({'architecture':'aarch64'},'auto')['gpu_resolution'],[1280,720])
        self.assertEqual(test_profile({'architecture':'armv6l'},'standard')['name'],'standard')
    def test_random_io_is_time_bounded_and_sequential_is_byte_bounded(self):
        random=fio_command('fio',Path('/tmp/payload'),'random','randwrite','4k',1024)
        self.assertIn('--runtime=20',random);self.assertIn('--time_based=1',random)
        self.assertFalse(any(x.startswith('--io_size=') for x in random))
        self.assertIn('--io_size=1073741824',fio_command('fio',Path('/tmp/payload'),'seq','write','1M',1024))
    def test_random_failure_does_not_suppress_independent_read(self):
        class Process:
            calls=[]
            def __init__(self,args,**kw):self.name=next(x.split('=',1)[1] for x in args if x.startswith('--name='));Process.calls.append(self.name);self.returncode=1 if self.name=='random_write_4k' else 0
            def communicate(self,timeout=None):return json.dumps({'jobs':[{'error':self.returncode,'read':{'io_bytes':16*MIB,'runtime':100,'iops':20},'write':{'io_bytes':16*MIB,'runtime':100,'iops':20}}]}),'device error' if self.returncode else ''
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder,patch('g3bench.storage.subprocess.Popen',Process):
            r=measure_drive({'directory':folder},'fio',16,60,lambda *x:None)
            self.assertEqual(r['tests']['random_read_4k']['status'],'passed')
            self.assertEqual(r['tests']['random_write_4k']['status'],'failed')
            self.assertEqual(list(Path(folder).iterdir()),[])
    def test_network_requires_acknowledgement(self):
        with patch('g3bench.network.transfer') as transfer:
            with self.assertRaises(ValueError):run_network(argparse.Namespace(allow_network=False))
            transfer.assert_not_called()
    def test_http_metrics_are_real_transfers_not_icmp_or_capacity_estimates(self):
        def transfer(url,payload=None):
            size=len(payload) if payload else int(url.split('bytes=')[1]);return {'bytes':size,'seconds':2,'mbps':size*4/1e6,'response_start_ms':10}
        with patch('g3bench.network.transfer',side_effect=transfer):r=measure(lambda x:None,lambda:None)
        self.assertEqual(r['status'],'passed');self.assertEqual(len(r['trials']),6)
        self.assertAlmostEqual(r['download_mbps'],4*1024*1024*4/1e6)
        self.assertIn('not ICMP',r['latency_kind'])
    def test_iperf_uses_both_directions_and_receiver_rate(self):
        raw=json.dumps({'end':{'sum_received':{'bits_per_second':90000000}}})
        with patch('g3bench.network.shutil.which',return_value='iperf3'),patch('g3bench.network.subprocess.run',return_value=argparse.Namespace(returncode=0,stdout=raw,stderr='')) as run:
            r=measure_iperf('192.168.1.2',lambda x:None,lambda:None)
        self.assertEqual(r['download_mbps'],90);self.assertEqual(r['upload_mbps'],90)
        self.assertIn('--reverse',run.call_args_list[1].args[0])
    @unittest.skipUnless(shutil.which('iperf3') and os.environ.get('G3BENCH_RUN_SOCKET_TESTS')=='1','iperf3 socket integration')
    def test_real_loopback_iperf_both_directions(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=subprocess.Popen([shutil.which('iperf3'),'--server','--port',str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            time.sleep(0.5)
            result=measure_iperf('127.0.0.1',lambda x:None,lambda:None,port)
            self.assertEqual(result['status'],'passed',result)
            self.assertGreater(result['upload_mbps'],0);self.assertGreater(result['download_mbps'],0)
        finally:
            server.terminate();server.communicate(timeout=5)
    def test_actual_bounded_load_records_throughput_and_stops(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            self.assertEqual(run_load(argparse.Namespace(load_seconds=1,workers=2,output=folder,open=False)),0)
            r=json.loads(next(Path(folder).glob('*/result.json')).read_text())
            self.assertGreater(r['results']['load']['mb_s'],0)
            self.assertEqual(r['test_status']['load']['status'],'passed')
            self.assertTrue(all(x is None for x in r['scores'].values()))
    def test_advice_distinguishes_software_rendering_and_missing_vulkan_probe(self):
        r=advice({'hardware':{'gpu_renderer':'llvmpipe'},'diagnostics':{'vulkan':{'status':'unavailable'}},'configuration':{},'telemetry':[]})
        self.assertTrue(any(x['title']=='Software graphics detected' for x in r))
        self.assertTrue(any('not evidence' in x['detail'] for x in r))
if __name__=='__main__':unittest.main()
