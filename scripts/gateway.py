"""Bounded mount-free TCP relay to the fixed web service; no request parsing."""

import json
import selectors
import signal
import socket
import socketserver
import sys
import threading
import time


def relay(client, backend, *, idle_seconds=30):
    peers = {client: backend, backend: client}
    for stream in peers:
        stream.settimeout(3)
    active = time.monotonic()
    with selectors.DefaultSelector() as selector:
        for stream in peers:
            selector.register(stream, selectors.EVENT_READ)
        while selector.get_map() and time.monotonic() - active < idle_seconds:
            for key, _events in selector.select(timeout=1):
                data = key.fileobj.recv(64 * 1024)
                if data:
                    peers[key.fileobj].sendall(data)
                    active = time.monotonic()
                else:
                    selector.unregister(key.fileobj)
                    peers[key.fileobj].shutdown(socket.SHUT_WR)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            # No client-controlled destination, URL, headers or filesystem paths.
            with socket.create_connection(("web", 8000), timeout=3) as backend:
                relay(self.request, backend)
        except OSError:
            pass  # Closed/slow connections terminate; never log payloads or credentials.


class Gateway(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False
    request_queue_size = 64

    def __init__(self, address):
        self.slots = threading.BoundedSemaphore(32)
        super().__init__(address, Handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()

    def handle_error(self, request, address):
        sys.stderr.write('{"service":"gateway","event":"connection_failed"}\n')


def main():
    stopping = threading.Event()
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda *_: stopping.set())
    with Gateway(("0.0.0.0", 8000)) as server:
        server.timeout = 0.5
        sys.stdout.write(json.dumps({"service": "gateway", "event": "service_started"}) + "\n")
        while not stopping.is_set():
            server.handle_request()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
