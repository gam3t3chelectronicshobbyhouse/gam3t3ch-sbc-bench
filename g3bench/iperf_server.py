"""Explicit temporary iperf3 host; no process or listener until Start is clicked."""
import ipaddress
import shutil
import socket
import subprocess
import threading
import time

from .showcase import process_options, stop_process


class IperfServer:
    def __init__(self):
        self.lock = threading.RLock()
        self.process = None
        self.watcher = None
        self.address = None
        self.port = 5201
        self.message = "Server stopped."

    def snapshot(self):
        with self.lock:
            running = self.process is not None and self.process.poll() is None
            return {"running": running, "address": self.address, "port": self.port,
                    "message": self.message, "available": bool(shutil.which("iperf3"))}

    def setup(self):
        addresses = []
        try:
            for address in socket.gethostbyname_ex(socket.gethostname())[2]:
                ip = ipaddress.ip_address(address)
                if ip.version == 4 and not ip.is_loopback and not ip.is_unspecified and address not in addresses:
                    addresses.append(address)
        except OSError:
            pass
        return {**self.snapshot(), "addresses": addresses}

    def start(self, address, port=5201):
        try:
            ip = ipaddress.IPv4Address(address) if isinstance(address, str) else None
        except ipaddress.AddressValueError:
            ip = None
        if ip is None or ip.is_unspecified or ip.is_multicast or int(ip) == 0xffffffff:
            raise ValueError("Enter a specific local IPv4 address, not 0.0.0.0 or a hostname")
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Server port must be 1024–65535")
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise ValueError("Server already running. Stop it before changing its address or port.")
            engine = shutil.which("iperf3")
            if not engine:
                raise ValueError("iperf3 is not installed. Use the setup command below, then Refresh setup.")
            # A nonlocal address or existing daemon must fail before launching our process.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                try:
                    probe.bind((str(ip), port))
                except OSError as exc:
                    raise ValueError("Cannot bind this local address/port. Check the IP or an existing iperf3 server; no other server was stopped.") from exc
            process = subprocess.Popen([engine, "--server", "--bind", str(ip), "--port", str(port)],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, **process_options())
            self.process, self.address, self.port = process, str(ip), port
            # Bounded readiness check occurs only during this explicit Start request.
            deadline = time.monotonic() + 3
            ready = False
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    with socket.create_connection((str(ip), port), timeout=0.1):
                        ready = True
                    break
                except OSError:
                    time.sleep(0.05)
            if not ready or process.poll() is not None:
                stop_process(process)
                self.process = None
                self.message = "Server failed to start. Check iperf3 and the selected address/port."
                raise ValueError(self.message)
            self.message = "Temporary server running. Stop it before benchmarking this machine."
            self.watcher = threading.Thread(target=self._wait, args=(process,), daemon=True)
            self.watcher.start()
            return self.snapshot()

    def _wait(self, process):
        code = process.wait()  # Sleeps until exit; no polling while hosting.
        with self.lock:
            if self.process is process:
                self.process = None
                self.message = f"Server exited (code {code}). Refresh setup or start it again."

    def close(self):
        with self.lock:
            process, watcher = self.process, self.watcher
            self.process = None
            self.message = "Server stopped. No startup service was installed."
        if process is not None:
            stop_process(process)
        if watcher is not None:
            watcher.join(timeout=6)
        return self.snapshot()
