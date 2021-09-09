#!/bin/bash

set -e
set -u



if [ ! -n "${1:-}" ]; then
	echo "You have set a node name"
	exit 1;
fi

ansible-playbook -i nodes/inventory -l ${1:-} ansible/playbook.yml 
