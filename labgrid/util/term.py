import asyncio
import collections
import logging
import os
import sys
from pexpect import TIMEOUT
import termios
import time

EXIT_CHAR = 0x1d    # FS (Ctrl + ])

async def microcom(session, host, port, place, resource, logfile, listen_only):
    call = ['microcom', '-q', '-s', str(resource.speed), '-t', f"{host}:{port}"]

    if listen_only:
        call.append("--listenonly")

    if logfile:
        call.append(f"--logfile={logfile}")
    logging.info(f"connecting to {resource} calling {' '.join(call)}")
    try:
        p = await asyncio.create_subprocess_exec(*call)
    except FileNotFoundError as e:
        raise ServerError(f"failed to execute microcom: {e}")
    while p.returncode is None:
        try:
            await asyncio.wait_for(p.wait(), 1.0)
        except asyncio.TimeoutError:
            # subprocess is still running
            pass

        try:
            session._check_allowed(place)
        except UserError:
            p.terminate()
            try:
                await asyncio.wait_for(p.wait(), 1.0)
            except asyncio.TimeoutError:
                # try harder
                p.kill()
                await asyncio.wait_for(p.wait(), 1.0)
            raise
    if p.returncode:
        print("connection lost", file=sys.stderr)
    return p.returncode

BUF_SIZE = 1024

async def run(serial):
    prev = collections.deque(maxlen=2)

    deadline = None
    to_serial = b''
    next_serial = time.monotonic()
    txdelay = serial.txdelay
    while True:
        try:
            data = serial.read(size=BUF_SIZE, timeout=0.001)
            if data:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()

        except TIMEOUT:
            pass

        data = os.read(sys.stdin.fileno(), BUF_SIZE)
        if data:
            if not deadline:
                deadline = time.monotonic() + 500  # 500ms
            prev.extend(data)
            count = prev.count(EXIT_CHAR)
            if count == 2:
                break

            to_serial += data

        if to_serial and time.monotonic() > next_serial:
            serial.write(to_serial[:1])
            to_serial = to_serial[1:]

        if deadline and time.monotonic() > deadline:
            prev.clear()
            deadline = None
        time.sleep(.005)

    # Blank line to move past any partial output
    print()

async def internal(serial):
    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] = new[3] & ~(termios.ICANON | termios.ECHO | termios.ISIG)
        new[6][termios.VMIN] = 0
        new[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, new)

        await run(serial)

    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, old)
