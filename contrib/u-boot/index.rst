
.. _u-boot-integration:

Summary
^^^^^^^
Here is a short list of the available scripts:

ub-int
    Build and boot on a target, starting an interactive session

ub-cli
    Build and boot on a target, ensure U-Boot starts and provide an interactive
    session from there

ub-smoke
    Smoke test U-Boot to check that it boots to a prompt on a target

ub-bisect
    Bisect a git tree to locate a failure on a particular target

ub-pyt
    Run U-Boot pytests on a target

Terminology
^^^^^^^^^^^

target
    A board / DUT which is the target of the script. This is one of the targets
    mentioned in the environment file and typically corresponds to a place,
    although sometimes multiple targets may use the same place.

lg-env
^^^^^^
Usage:
    . lg-env

Purpose:
    Sets the environment variables for your lab, so you can run labgrid-client,
    labgrid-exporter, etc.

lg-client
^^^^^^^^^
Usage:
    lg-client ...

Purpose:
    Runs labgrid-client with the environment variables for your lab, so you can
    use the tool without worrying about all the extra arguments.

Example:
    lg-client places

ub-int
^^^^^^

Usage:

   ub-int [-csv] *target*

====== ====================================================
Flag   Meaning
====== ====================================================
-c     Run 'make mrproper' before building
-n     Don't build U-Boot
-s     Send over USB (instead of writing to boot media)
-t     Don't bootstrap U-Boot
-v     Verbose mode
====== ====================================================

Purpose:
    Invoke this in the U-Boot source tree. It builds U-Boot for the given target
    and starts it on the target, bringing up an interactive U-Boot prompt. Any
    build errors are reported and abort the process. If U-Boot fails to boot,
    this will be visible on the an error is reported.

ub-cli
^^^^^^

Usage:
   ub-cli [-csv] *target*

====== ====================================================
Flag   Meaning
====== ====================================================
-c     Run 'make mrproper' before building
-n     Don't build U-Boot
-s     Send over USB (instead of writing to boot media)
-t     Don't bootstrap U-Boot
-v     Verbose mode
====== ====================================================

Purpose:
    Invoke this in the U-Boot source tree. It builds U-Boot for the given target
    and starts it on the target, ensures that U-Boot starts correctly, then
    brings up an interactive U-Boot prompt. Any build errors are reported and
    abort the process. If U-Boot fails to boot, an error is reported.

ub-bisect
^^^^^^^^^

Usage:
   ub-bisect [-csv] *target* [*commit*]

====== ====================================================
Flag   Meaning
====== ====================================================
-c     Run 'make mrproper' before building
-s     Send over USB (instead of writing to boot media)
====== ====================================================

commit:
    Commit to cherry-pick before trying each bisect commit

Purpose:
    Invoke this in the U-Boot source tree once you have set the 'good and 'bad'
    commits for a bisect. It

    It runs a bisect on the target to identify the commit which broke it.

    For cases where you have a 'fixup' commit that needs to be applied to each
    source tree before testing it, add the *commit* argument, which is then
    cherry-picked to the tree before each attempt.

    It is recommended to make sure the tree is clean before running a bisect.

    Internally, ub-bisect uses _ub-bisect-try to perform each step.

    Note that a bisect may take many minutes, since it must build and load new
    software onto the board in each step, then run the smoke test.

Example:
    good v2022.04      # Commit at which target bbb is known to work
    bad origin/master  # Commit at which bbb is broken
    ub-bisect bbb      # Locate the commit which broke it

ub-smoke
^^^^^^^^

Usage:
   ub-smoke [-cs] *target*

====== ====================================================
Flag   Meaning
====== ====================================================
-c     Run 'make mrproper' before building
-s     Send over USB (instead of writing to boot media)
====== ====================================================

Purpose:
    Invoke this in the U-Boot source tree. It builds U-Boot for the given target
    and starts it on the target, ensures that U-Boot starts correctly. If U-Boot
    fails to boot, the test fails.

ub-pyt
^^^^^^

Usage:
   ub-pyt [-cs] *target* [*test_spec*]

====== ====================================================
Flag   Meaning
====== ====================================================
-c     Run 'make mrproper' before building
-n     Don't build U-Boot
-s     Send over USB (instead of writing to boot media)
-t     Don't bootstrap U-Boot
====== ====================================================

*test_spec*
    Describes the tests to run or not run. This is passed to pytest using the
    -k argument. For example, "not tpm" means to run all tests except those
    containing the word 'tpm'.

Purpose:
    Invoke this in the U-Boot source tree. It builds U-Boot for the given target
    and starts it on the target, ensures that U-Boot starts correctly, then
    runs the tests according *test_spec*. If that is not provided, it runs all
    tests that are enabled for the board.

    You may find it helpful to use this script with 'git bisect'.

Examples:
    ub-pyt bbb help
    git bisect run ub-pyt bbb
