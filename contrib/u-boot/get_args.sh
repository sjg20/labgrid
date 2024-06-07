#!/bin/bash

# Decode arguments
# This decodes and removes the flags and the target argument
# It returns with the next argument in $1

# Usage
# . get_arg.sh
#
# The allowed_args variable must be set to the list of valid args for this
# script, e.g. "cnstv"

# 1 to bootstrap the board, i.e. write U-Boot to it and start it up
export bootstrap=1

# 1 to build U-Boot, else the existing build will be used
export build=1

# 1 to clean the build directory before starting the build
export clean=0

# -v to show variables and use verbose mode in Labgrid
export V=

# 1 to bootstrap over USB using the boot ROM
export send=0

# 1 to reset the board before connecting
export reset=1

# selects the target strategy-state to use, in Labgrid's UBootStrategy
export strategy="-s start -e off"

# --no-prompt-wait to tell pytest not to wait for a U-Boot prompt
export no_prompt_wait=

# build path to use (empty to use default)
export build_dir=

while getopts "${allowed_args}" opt; do
	case $opt in
	d )
	  build_dir="$OPTARG"
	  ;;
	c )
	  clean=1
	  ;;
	B )
	  build=0
	  ;;
	h )
	  usage
	  ;;
	s )
	  send=1
	  ;;
	R )
	  reset=0
	  bootstrap=0
	  build=0
	  strategy=
	  no_prompt_wait="--no-prompt-wait"
	  ;;
	T )
	  bootstrap=0
	  build=0
	  ;;
	v )
	  V=-v
	  ;;
	\? )
	  echo "Invalid option: $OPTARG" 1>&2
	  exit 1
	  ;;
	esac
done

shift $((OPTIND -1))

target="$1"
shift

[[ -z "${target}" ]] && usage "Missing target"

# vars is passed to labgrid itself; these vars are parsed by UBootStrategy
vars="-V do-bootstrap ${bootstrap} -V do-build ${build} -V do-clean ${clean}"
vars+=" -V do-send ${send}"
[ -n "${build_dir}" ] && vars+=" -V build-dir ${build_dir}"

# lg_vars is passed to Labgrid's pytest plugin
lg_vars="--lg-var do-bootstrap ${bootstrap} --lg-var do-build ${build}"
lg_vars+=" --lg-var do-clean ${clean} --lg-var do-send ${send}"
[ -n "${build_dir}" ] && lg_vars+=" --lg-var build-dir ${build_dir}"

export vars lg_vars target

if [ -n "${V}" ]; then
	echo "vars: ${vars}"
	echo "lg_vars: ${lg_vars}"
fi
