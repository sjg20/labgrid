import asyncio
import logging

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
