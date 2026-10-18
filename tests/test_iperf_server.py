import socket
import subprocess
import threading
import unittest
from unittest.mock import patch

from g3bench.iperf_server import IperfServer
from g3bench.ui import Dashboard


class FakeProcess:
    def __init__(self):
        self.done = threading.Event()
        self.code = None

    def poll(self):
        return self.code

    def wait(self, timeout=None):
        if not self.done.wait(timeout):
            raise subprocess.TimeoutExpired('iperf3', timeout)
        return self.code

    def finish(self):
        self.code = 0
        self.done.set()


class IperfServerTests(unittest.TestCase):
    def test_disabled_initialization_and_setup_never_launch(self):
        with patch('g3bench.iperf_server.subprocess.Popen') as launch, patch('g3bench.iperf_server.socket.gethostbyname_ex', return_value=('pc', [], ['127.0.0.1', '192.168.1.2'])):
            server = IperfServer()
            self.assertFalse(server.snapshot()['running'])
            self.assertEqual(server.setup()['addresses'], ['192.168.1.2'])
            server.close()
            launch.assert_not_called()

    def test_invalid_input_and_missing_dependency_do_not_launch(self):
        with patch('g3bench.iperf_server.subprocess.Popen') as launch, patch('g3bench.iperf_server.shutil.which', return_value=None):
            server = IperfServer()
            for address, port in [('0.0.0.0', 5201), ('localhost', 5201), (None, 5201), ('224.0.0.1', 5201), ('127.0.0.1;whoami', 5201), ('127.0.0.1', True), ('127.0.0.1', 80)]:
                with self.assertRaises(ValueError):
                    server.start(address, port)
            with self.assertRaisesRegex(ValueError, 'not installed'):
                server.start('127.0.0.1')
            launch.assert_not_called()

    def test_occupied_port_does_not_launch_or_stop_existing_server(self):
        with socket.socket() as peer:
            peer.bind(('127.0.0.1', 0))
            peer.listen()
            with patch('g3bench.iperf_server.shutil.which', return_value='iperf3'), patch('g3bench.iperf_server.subprocess.Popen') as launch, patch('g3bench.iperf_server.stop_process') as stop:
                with self.assertRaisesRegex(ValueError, 'no other server was stopped'):
                    IperfServer().start('127.0.0.1', peer.getsockname()[1])
                launch.assert_not_called()
                stop.assert_not_called()

    def test_owned_server_lifecycle_and_benchmark_guard(self):
        process = FakeProcess()
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        with patch('g3bench.ui.hardware', return_value={}), patch('g3bench.ui.find_engine', return_value=None), patch('g3bench.iperf_server.shutil.which', return_value='iperf3'), patch('g3bench.iperf_server.subprocess.Popen', return_value=process) as launch, patch('g3bench.iperf_server.socket.create_connection'), patch('g3bench.iperf_server.stop_process', side_effect=lambda p: p.finish()) as stop:
            dashboard = Dashboard('build/test-iperf-server')
            server = dashboard.iperf_server
            try:
                self.assertTrue(server.start('127.0.0.1', port)['running'])
                self.assertEqual(launch.call_args.args[0], ['iperf3', '--server', '--bind', '127.0.0.1', '--port', str(port)])
                with self.assertRaisesRegex(ValueError, 'already running'):
                    server.start('127.0.0.1', port)
                with self.assertRaisesRegex(ValueError, 'Stop the temporary'):
                    dashboard.start('cpu')
            finally:
                self.assertFalse(server.close()['running'])
            self.assertFalse(server.watcher.is_alive())
            server.close()
            stop.assert_called_once_with(process)

    def test_early_child_exit_is_not_reported_as_running(self):
        process = FakeProcess()
        process.finish()
        with patch('g3bench.iperf_server.shutil.which', return_value='iperf3'), patch('g3bench.iperf_server.subprocess.Popen', return_value=process), patch('g3bench.iperf_server.stop_process') as stop:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            server = IperfServer()
            with self.assertRaisesRegex(ValueError, 'failed to start'):
                server.start('127.0.0.1', port)
            self.assertFalse(server.snapshot()['running'])
            stop.assert_called_once_with(process)
