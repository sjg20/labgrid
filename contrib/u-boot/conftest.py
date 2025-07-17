from pexpect.exceptions import TIMEOUT
import pytest
import subprocess
import sys

@pytest.fixture
def u_boot(request, target, strategy):
    if request.config.option.lg_use_running_system:
        strategy.uboot.assume_active()
        target.activate(strategy.uboot)
    else:
        try:
            strategy.transition("uboot")
        except subprocess.CalledProcessError as exc:
            # Show any build failures
            print(f"Command failure: {' '.join(exc.cmd)}")
            for line in exc.output.splitlines():
                print(line.decode('utf-8'))
        except TIMEOUT:
            # Show any console output when things fail
            console = target.get_active_driver('ConsoleProtocol')
            output = console.read_output()
            sys.stdout.buffer.write(output)
            raise

    yield strategy.uboot

    clog = request.config.option.lg_console_logfile
    if clog:
        print(f"\nWriting console output to {clog}...")

        # The 'target' is available from the fixture arguments
        console = target.get_active_driver('ConsoleProtocol')
        output = console.read_output()
        with open(clog, 'wb') as f:
            f.write(output)
            print(f"Successfully wrote {len(output)} bytes to {clog}.")
