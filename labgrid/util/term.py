import asyncio
import collections
import logging
import os
import sys
from pexpect import TIMEOUT
import serial_asyncio
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

BUF_SIZE = 1024

'''
async def read_console(console, writer):
    while True:
        try:
            indata = console.read(BUF_SIZE, timeout=0)
            if indata:
                #print('indata', indata)
                #sys.stdout.buffer.write(indata)
                #sys.stdout.buffer.flush()
                writer.write(indata)
                await writer.drain()
        except TIMEOUT:
            #print('timeout')
            pass
        await asyncio.sleep(.001)

async def read_serial(console, reader):
    while True:
        #continue
        outdata = await reader.read(BUF_SIZE)
        #outdata = sys.stdin.buffer.read(BUF_SIZE)
        if outdata:
            print('outdata', outdata)
            #console.write(outdata)
            loop.call_soon(console.write, outdata)
            #await writer.drain()
        await asyncio.sleep(.0001)
'''

async def use_serial_connection(serial, loop=None, limit=None):
    """A wrapper for create_serial_connection() returning a (reader,
    writer) pair.

    The reader returned is a StreamReader instance; the writer is a
    StreamWriter instance.

    The arguments are all the usual arguments to Serial(). Additional
    optional keyword arguments are loop (to set the event loop instance
    to use) and limit (to set the buffer limit passed to the
    StreamReader.

    This function is a coroutine.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    if limit is None:
        limit = asyncio.streams._DEFAULT_LIMIT
    reader = asyncio.StreamReader(limit=limit, loop=loop)
    protocol = asyncio.StreamReaderProtocol(reader, loop=loop)
    transport, _ = await serial_asyncio.connection_for_serial(loop, lambda: protocol, serial)
    writer = asyncio.StreamWriter(transport, protocol, reader, loop)
    return reader, writer

async def transfer_data(reader, writer):
    print('start')
    while True:
        data = await reader.read()
        print('data', data)
        await writer.write(data)

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
    # Set up the console for use
    # Based on https://github.com/pyserial/pyserial/blob/master/examples/rfc2217_server.py
    # and https://github.com/pyserial/pyserial/blob/master/serial/tools/miniterm.py
    # (inspired by tbot channel.py)
    #tty.setcbreak(fd)
    #tty.setraw(fd)

    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] = new[3] & ~(termios.ICANON | termios.ECHO | termios.ISIG)
        new[6][termios.VMIN] = 0
        new[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, new)

        #print('console.serial', console.serial)
        #console.serial.nonblocking()

        #cons_reader, cons_writer = await stdio()
        done = False

        #time.sleep(1)

        #output = console.read_output()
        #output = self.console.read_output()
        #sys.stdout.buffer.write(output)
        #print(f'\nU-Boot is ready')

        await run(serial)

        #ser_reader, ser_writer = await use_serial_connection(console.serial)

        #to_ser = asyncio.create_task(transfer_data(cons_reader, ser_writer))
        #to_con = asyncio.create_task(transfer_data(ser_reader, cons_writer))
        #await asyncio.gather(to_ser) #, to_con)

        #read_console_task = asyncio.create_task(read_console(console, writer))
        #read_serial_task = asyncio.create_task(read_serial(console, reader))
        #await read_console_task
        #await read_serial_task
        #while True:
                #res = await reader.read(100)
                #if not res:
                    #break
                #writer.write(res)
                #await writer.drain()

    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, old)
