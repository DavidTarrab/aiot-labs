"""Small USB raw-REPL utility for diagnostics and explicit firmware upload."""
import argparse
from pathlib import Path
import time
import serial


def execute(port, code, timeout=15):
    with serial.Serial(port, 115200, timeout=0.1) as connection:
        connection.write(b"\x03\x03")
        time.sleep(0.2)
        connection.reset_input_buffer()
        connection.write(b"\x01")
        start = time.monotonic()
        banner = b""
        while not banner.endswith(b">"):
            banner += connection.read(4096)
            if time.monotonic() - start > 5:
                raise RuntimeError("Cannot enter raw REPL; close other serial monitors")
        for offset in range(0, len(code), 128):
            connection.write(code[offset:offset + 128].encode())
            time.sleep(0.01)
        connection.write(b"\x04")
        result = b""
        start = time.monotonic()
        while not result.endswith(b"\x04>"):
            result += connection.read(4096)
            if time.monotonic() - start > timeout:
                connection.write(b"\x03\x02")
                raise TimeoutError(result.decode(errors="replace"))
        connection.write(b"\x02")
    if not result.startswith(b"OK"):
        raise RuntimeError(result.decode(errors="replace"))
    stdout, stderr = result[2:-1].split(b"\x04", 2)[:2]
    if stderr:
        raise RuntimeError(stderr.decode())
    return stdout.decode()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--code")
    group.add_argument("--upload", nargs="+")
    group.add_argument("--start", help="Run a previously uploaded script and leave it running")
    args = parser.parse_args()
    if args.code:
        print(execute(args.port, args.code, timeout=70))
    elif args.start:
        with serial.Serial(args.port, 115200, timeout=0.2) as connection:
            connection.write(b"\x03\x03\x02\r\n")
            time.sleep(0.2)
            # A soft reset clears imported modules and stale asyncio TCP listeners.
            connection.write(b"\x04")
            time.sleep(2)
            connection.reset_input_buffer()
            command = "exec(open(%r).read(), {'__name__':'__main__'})\r\n" % args.start
            connection.write(command.encode())
            time.sleep(3)
            print(connection.read(8192).decode(errors="replace"))
    else:
        for name in args.upload:
            path = Path(name)
            content = path.read_bytes()
            # New filenames only by default; keep existing main.py untouched.
            code = "f=open(%r,'wb')\n" % path.name
            for offset in range(0, len(content), 256):
                code += "f.write(%r)\n" % content[offset:offset + 256]
            code += "f.close()\nprint('uploaded',%r)" % path.name
            print(execute(args.port, code))
