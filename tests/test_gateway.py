"""Opaque TCP forwarding preserves bytes and both directions' half-close."""

import socket
import threading

from scripts.gateway import relay


def test_gateway_preserves_large_response_and_client_half_close():
    client, inbound = socket.socketpair()
    outbound, backend = socket.socketpair()
    streams = (client, inbound, outbound, backend)
    for stream in streams:
        stream.settimeout(5)
    errors = []
    payload = b"synthetic-response-" * 10_000

    def forward():
        try:
            relay(inbound, outbound)
        except Exception as exc:
            errors.append(exc)

    def respond():
        try:
            assert backend.recv(100) == b"synthetic-request"
            assert backend.recv(1) == b""
            backend.sendall(payload)
            backend.shutdown(socket.SHUT_WR)
        except Exception as exc:
            errors.append(exc)

    forwarding = threading.Thread(target=forward, daemon=True)
    responding = threading.Thread(target=respond, daemon=True)
    forwarding.start()
    responding.start()
    try:
        client.sendall(b"synthetic-request")
        client.shutdown(socket.SHUT_WR)
        received = bytearray()
        while data := client.recv(32 * 1024):
            received.extend(data)
        assert bytes(received) == payload
        forwarding.join(timeout=5)
        responding.join(timeout=5)
        assert not forwarding.is_alive() and not responding.is_alive() and not errors
    finally:
        for stream in streams:
            stream.close()
