#!/bin/bash

# make sure that IP address has been grabbed
while ! ip link show wlan0 &>/dev/null; do
	sleep 1
done

echo "Successfully got IP"

# check number of args
if [ "$#" -ne 1 ]; then
	echo "Error: provide exactly one argument"
	echo "Usage: $0 label"
	exit 1
fi

# get label
label="$1"

# get current IP address
ip=$(ip addr show wlan0 | awk '/inet / {print $2}' | cut -d / -f1)

# send address to CASlab server
curl -k -X POST -H "Content-Type: application/json" \
	-d '{"ip": "'$ip'","label": "'$label'"}' https://caslab.case.edu/team/

exit 0
