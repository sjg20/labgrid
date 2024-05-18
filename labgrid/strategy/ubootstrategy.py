import enum

import attr
import sys

from ..factory import target_factory
from .common import Strategy, StrategyError
from labgrid.var_dict import get_var


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
    """UbootStrategy - Strategy to switch to uboot or shell"""
    bindings = {
        "power": "PowerProtocol",
        "console": "ConsoleProtocol",
        "uboot": "UBootDriver",
        "shell": "ShellDriver",
        "reset": "ResetProtocol",
    }

    status = attr.ib(default=Status.unknown)

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        self.bootstrapped = False

    def bootstrap(self):
        builder = self.target.get_driver("UBootProviderDriver")
        if get_var('do-build', '0') == '1':
            image_dir = builder.build()
        else:
            image_dir = builder.get_build_path()
        print(f'Bootstrapping U-Boot from dir {image_dir}')

        writer = self.target.get_driver("UBootWriterDriver")
        writer.write(image_dir)
        self.bootstrapped = True

    def start(self):
        "Start U-Boot, by powering on / resetting the board"""
        if not self.bootstrapped and get_var('do-bootstrap', '0') == '1':
            self.transition(Status.bootstrap)
        else:
            writer = self.target.get_driver("UBootWriterDriver")
            writer.prepare_boot()

        self.target.activate(self.console)
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
            # interrupt uboot
            self.target.activate(self.uboot)
            output = self.console.read_output()
            sys.stdout.buffer.write(output)
            print('\nU-Boot is ready')
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
