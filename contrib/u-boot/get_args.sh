#!/bin/bash

# Decode arguments
# This decodes and removes the flags and the target argument
# It returns with the next argument in $1

export bootstrap=1
export build=1
export clean=0
export V=
export send=0
export reset=1
export strategy="-s start"
export no_prompt_wait=

while getopts "${allowed_args}" opt; do
	case $opt in
	c )
	  clean=1
	  ;;
	n )
	  build=0
	  ;;
	s )
	  send=1
	  ;;
	r )
	  reset=0
	  bootstrap=0
	  strategy=
	  no_prompt_wait="--no-prompt-wait"
	  ;;
	t )
	  bootstrap=0
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

target=$1
shift

[[ -z "${target}" ]] && usage "Missing target"

vars="-V do-bootstrap ${bootstrap} -V do-build ${build} -V do-clean ${clean}"
vars+=" -V do-send ${send}"

lg_vars="--lg-var do-bootstrap ${bootstrap} --lg-var do-build ${build}"
lg_vars+=" --lg-var do-clean ${clean} --lg-var do-send ${send}"

export vars lg_vars target
