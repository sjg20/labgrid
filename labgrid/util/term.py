import asyncio
import logging
import os
import sys
from pexpect import TIMEOUT
import termios

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
'''
async def connect_stdin_stdout():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    rprotocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: rprotocol, sys.stdin)

    reader = asyncio.StreamWriter()
    wprotocol = asyncio.StreamWriterProtocol(reader)
    await loop.connect_write_pipe(lambda: wprotocol, sys.stdout)

    #w_transport, w_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
    #writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
    return reader, writer
'''

async def stdio(limit=asyncio.streams._DEFAULT_LIMIT):
    loop = asyncio.get_event_loop()

    reader = asyncio.StreamReader(limit=limit, loop=loop)
    await loop.connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(reader, loop=loop), sys.stdin)

    writer_transport, writer_protocol = await loop.connect_write_pipe(
        lambda: asyncio.streams.FlowControlMixin(loop=loop),
        os.fdopen(sys.stdout.fileno(), 'wb'))
    writer = asyncio.streams.StreamWriter(
        writer_transport, writer_protocol, None, loop)

    return reader, writer

async def reader():


async def internal(console):
    # Set up the console for use
    # Based on https://github.com/pyserial/pyserial/blob/master/examples/rfc2217_server.py
    # and https://github.com/pyserial/pyserial/blob/master/serial/tools/miniterm.py
    # (inspired by tbot channel.py)
    #tty.setcbreak(fd)
    #tty.setraw(fd)

    BUF_SIZE = 1024
    loop = asyncio.get_event_loop()

    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] = new[3] & ~termios.ICANON & ~termios.ECHO & ~termios.ISIG
        new[6][termios.VMIN] = 1
        new[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, new)
        print('console.serial', console.serial)
        #console.serial.nonblocking()

        reader, writer = await stdio()
        #while True:
                #res = await reader.read(100)
                #if not res:
                    #break
                #writer.write(res)
                #await writer.drain()

        done = False
        while not done:
            try:
                indata = console.read(BUF_SIZE, timeout=0)
                if indata:
                    print('indata', indata)
                    #sys.stdout.buffer.write(indata)
                    #sys.stdout.buffer.flush()
                    writer.write(indata)
                    await writer.drain()
            except TIMEOUT:
                #print('timeout')
                pass
            #continue
            outdata = await reader.read(BUF_SIZE)
            #outdata = sys.stdin.buffer.read(BUF_SIZE)
            if outdata:
                print('outdata', outdata)
                #console.write(outdata)
                loop.call_soon(console.write, outdata)
                #await writer.drain()
            await asyncio.sleep(.01)

    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, old)
