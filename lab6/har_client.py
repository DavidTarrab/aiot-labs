"""Desktop TCP commands, compatible with the Lab 5 newline-delimited protocol."""
import json
import socket


class SmartwatchClient:
    def __init__(self, host, port=8080, timeout=150):
        self.host = host.strip()
        self.port = int(port)
        self.timeout = timeout

    def send_command(self, name, args=None):
        payload = json.dumps({"name": name, "args": args or []}) + "\n"
        with socket.create_connection((self.host, self.port), self.timeout) as connection:
            connection.sendall(payload.encode())
            with connection.makefile("rb") as stream:
                # 3 x 128 floats plus timing metadata exceed Lab 5's 4096-byte reply limit.
                reply = stream.readline(65537)
        if len(reply) > 65536 or not reply.endswith(b"\n"):
            raise RuntimeError("Incomplete or oversized ESP32 response")
        response = json.loads(reply)
        if response.get("ok") is not True:
            raise RuntimeError(response.get("error", "ESP32 command failed"))
        return response["result"]
