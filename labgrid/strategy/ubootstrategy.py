import enum
import sys
import time

import attr
from pexpect import TIMEOUT

from ..factory import target_factory
from .common import Strategy, StrategyError
from ..var_dict import get_var
from ..driver.servodriver import ServoResetDriver


class Status(enum.Enum):
    """States supported by this strategy:

        unknown: State is not known
        off: Power is off
        bootstrap: U-Boot has been written to the board
        start: Board has started booting
        uboot: Board has stopped at the U-Boot prompt
        shell: Board has stopped at the Linux prompt
    """
    unknown, off, bootstrap, start, uboot, shell = range(6)


@target_factory.reg_driver
@attr.s(eq=False)
class UBootStrategy(Strategy):
    """UbootStrategy - Strategy to switch to uboot or shell

    Args:
        send_only (bool): True if the board only supports sending over USB, no
            flash

    Variables:
        do-build: Build U-Boot before bootstrapping it
        do-bootstrap: Bootstrap U-Boot by writing it to the board
        do-send: Bootstrap over USB instead of using boot media
    """
    bindings = {
        "power": "PowerProtocol",
        "console": "ConsoleProtocol",
        "uboot": "UBootDriver",
        "shell": "ShellDriver",
        "reset": {"ResetProtocol", None},
        "recovery": {"RecoveryProtocol", None},
    }

    status = attr.ib(default=Status.unknown)
    send_only = attr.ib(default=False, validator=attr.validators.instance_of(bool))

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        self.bootstrapped = False

    def use_send(self):
        return self.send_only or get_var('do-send', '0') == '1'

    def bootstrap(self):
        builder = self.target.get_driver("UBootProviderDriver")
        if get_var('do-build', '0') == '1':
            image_dirs = builder.build()
        else:
            image_dirs = builder.get_build_paths()
        print(f"Bootstrapping U-Boot from dir {' '.join(image_dirs)}")

        writer = self.target.get_driver("UBootWriterDriver")
        if self.use_send():
            self.target.activate(self.power)
            self.target.activate(self.reset)

            # Hold the board in reset, except for Servo since this prevents the
            # USB-download mode from working (at least with snow)
            if not isinstance(self.reset, ServoResetDriver):
                self.reset.set_reset_enable(True, mode='warm')

            if self.power != self.reset:
                self.power.on()

            self.target.activate(self.recovery)
            self.recovery.set_enable(True)

            # Do the Servo reset now
            if isinstance(self.reset, ServoResetDriver):
                self.reset.set_reset_enable(True, mode='warm')
                time.sleep(1)

            self.target.activate(self.console)

            # Release reset
            self.reset.set_reset_enable(False, mode='warm')

            # Give the board time to notice
            time.sleep(.2)
            self.recovery.set_enable(False)

            writer.send(image_dirs)
        else:
            writer.write(image_dirs)
        self.bootstrapped = True

    def start(self):
        "Start U-Boot, by powering on / resetting the board"""
        if not self.bootstrapped and get_var('do-bootstrap', '0') == '1':
            self.transition(Status.bootstrap)
        else:
            writer = self.target.get_driver("UBootWriterDriver")
            writer.prepare_boot()
        if not self.use_send():
            self.target.activate(self.console)
            if self.reset:
                self.target.activate(self.reset)

                # Hold in reset across the power cycle, to avoid booting the
                # board twice
                self.reset.set_reset_enable(True)
            if self.reset != self.power:
                self.power.cycle()

            # Here we could await a console, if it depends on the board
            # being powered. The above console activate would need be
            # dropped. However, this doesn't seem to work:
            # self.target.await_resources([self.console.port], 10.0)
            # self.target.activate(self.console)  # for zynq_zybo
            if self.reset:
                self.reset.set_reset_enable(False)

    def transition(self, status):
        if not isinstance(status, Status):
            status = Status[status]
        if status == Status.unknown:
            raise StrategyError(f"can not transition to {status}")
        elif status == self.status:
            return # nothing to do
        elif status == Status.off:
            self.target.deactivate(self.console)
            self.target.activate(self.power)
            self.power.off()
        elif status == Status.bootstrap:
            self.bootstrap()
        elif status == Status.start:
            self.transition(Status.off)
            self.start()
        elif status == Status.uboot:
            self.transition(Status.start)

            start = time.time()
            try:
                # interrupt uboot
                self.target.activate(self.uboot)
            except TIMEOUT:
                output = self.console.read_output()
                sys.stdout.buffer.write(output)
                raise

            # For debugging
            #output = self.console.read_output()
            #sys.stdout.buffer.write(output)
            duration = time.time() - start
            print(f'\n{{lab ready in {duration:.1f}s: {self.uboot.version}}}')
        elif status == Status.shell:
            # transition to uboot
            self.transition(Status.uboot)
            self.uboot.boot("")
            self.uboot.await_boot()
            self.target.activate(self.shell)
            self.shell.run("systemctl is-system-running --wait")
        else:
            raise StrategyError(f"no transition found from {self.status} to {status}")
        self.status = status

    def force(self, status):
        if not isinstance(status, Status):
            status = Status[status]
        if status == Status.off:
            self.target.activate(self.power)
        elif status == Status.uboot:
            self.target.activate(self.uboot)
        elif status == Status.shell:
            self.target.activate(self.shell)
        else:
            raise StrategyError("can not force state {}".format(status))
        self.status = status
