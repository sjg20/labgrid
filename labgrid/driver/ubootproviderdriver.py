import attr
import os
import subprocess
import sys

from labgrid.driver.common import Driver
from labgrid.factory import target_factory
from labgrid.step import step
from labgrid.driver.exception import ExecutionError
from labgrid.util.helper import processwrapper
from labgrid.var_dict import get_var

@target_factory.reg_driver
@attr.s(eq=False)
class UBootProviderDriver(Driver):
    """UBootProviderDriver - Build U-Boot image for a board

    Attributes:
        board (str): U-Boot board name, e.g. "gurnard"
        build_base (str):
        source_dir (str): Directory containing U-Boot source (default is current
            directory)

    Paths (environment configuration):
        uboot_build_base: Base output directory for build, e.g. "/tmp/b".
            The build will taken place in build_base/board, e.g. "/tmp/b/gurnard"
    """
    board = attr.ib(validator=attr.validators.instance_of(str))
    bl31 = attr.ib(default='', validator=attr.validators.instance_of(str))
    binman_indir = attr.ib(default='', validator=attr.validators.instance_of(str))

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        env = self.target.env
        if env:
            self.tool = env.config.get_tool('buildman')
        else:
            self.tool = 'buildman'
        self.build_base = env.config.get_path('uboot_build_base')
        self.workdirs = env.config.get_path('uboot_workdirs')
        self.sourcedir = env.config.get_path('uboot_source')

    def get_build_path(self, board=None):
        '''Get the path to use for building the board

        Args:
            board (str): Name of U-Boot board to set up, or None for default
        '''
        pathname = get_var('build-path')
        if not pathname:
            pathname = os.getenv('U_BOOT_BUILD_DIR')
        if not pathname:
            if not board:
                board = self.get_board()
            pathname = os.path.join(self.build_base, board)
        return pathname

    def get_board(self):
        return get_var('use-board', self.board)

    @Driver.check_active
    @step(title='build')
    def build(self):
        """Builds U-Boot

        Performs an incremental build of U-Boot for the selected board,
        returning a single output file produced by the build

        Returns:
            str: Path of build result, e.g. '/tmp/b/orangepi_pc'
        """
        board = self.get_board()
        build_path = self.get_build_path(board)
        commit = get_var('commit')
        patch = get_var('patch')

        env = os.environ
        if self.bl31:
            env['BL31'] = self.bl31
        if self.binman_indir:
            env['BINMAN_INDIRS'] = self.binman_indir

        cmd = [
            self.tool,
            '-o', build_path,
            '-w',
            '--board', board,
            '-W',
            '-ve', '-m',
        ]

        # If we have a commit, use a worktree. Otherwise we just use the source
        # in the current directory
        detail = 'in sourcedir'
        cwd = self.sourcedir

        pathname = os.getenv('U_BOOT_SOURCE_DIR')
        if pathname:
            detail = 'in pytest-source dir'
            cwd = pathname

        workdir = None
        if commit:
            workdir = self.setup_worktree(board, commit)
            cwd = workdir
            detail = 'in workdir'
            if patch:
                self.apply_patch(workdir, patch)
                detail += ' with patch'

        if get_var('do-clean', '0') == '1':
            cmd.append('-m')

        print(f'Building U-Boot {detail} for {board}')
        self.logger.debug(f'cwd:{os.getcwd()} cmd:{cmd}')
        try:
            out = processwrapper.check_output(cmd, cwd=cwd, env=env)
        except subprocess.CalledProcessError as exc:
            raise
        out = out.decode('utf-8', errors='ignore')
        fail = None
        for line in out.splitlines():
            if 'is non-functional' in line:
                fail = line
            self.logger.debug(line)
        if fail:
            raise ValueError(f'build failed: {fail}')

        return build_path

    def setup_worktree(self, board, commit):
        """Make sure there is a worktree for the current board

        If the worktree directory does not exist, it is created

        Args:
            board (str): Name of U-Boot board to set up
            commit (str): Commit to check out (hash or branch name)

        Returns:
            str: work directory for this board
        """
        workdir = os.path.join(self.workdirs, board)
        if not os.path.exists(workdir):
            cmd = [
                'git',
                '--git-dir', self.source_dir,
                'worktree',
                'add',
                board,
                '--detach',
            ]
            self.logger.info(f'Setting up worktree in {workdir}')
            processwrapper.check_output(cmd, cwd=self.workdirs)
        else:
            cmd = [
                'git',
                '-C', workdir,
                'reset',
                '--hard',
            ]
            self.logger.info(f'Reseting up worktree in {workdir}')
            processwrapper.check_output(cmd, cwd=self.workdirs)

        self.select_commit(board, commit)
        return workdir

    def select_commit(self, board, commit):
        """Select a particular commit in the worktree

        Args:
            board (str): Name of U-Boot board to set up
            commit (str): Commit to select (hash or branch name)
        """
        workdir = os.path.join(self.workdirs, board)
        cmd = [
            'git',
            '-C', workdir,
            'checkout',
            commit,
        ]
        self.logger.info(f"Checking out {commit}")
        processwrapper.check_output(cmd)

    def apply_patch(self, workdir, patch):
        """Apply a patch to the workdir

        Apply the patch. If something goes wrong,

        """
        cmd = [
            'git',
            '-C', workdir,
            'apply',
            patch,
        ]
        self.logger.info(f'Applying patch {patch}')
        try:
            processwrapper.check_output(cmd)
        except:
            cmd = [
                'git',
                '-C', workdir,
                "am",
                '--abort',
            ]
            processwrapper.check_output(cmd)
            raise

    def query_info(self, name):
        board = self.get_board()
        if name == 'board':
            return board
        elif name == 'build_path':
            return self.get_build_path(board)
        return None
