#!/bin/bash

# make sure that IP address has been grabbed
while ! curl -s https://api.ipify.org &>/dev/null; do
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
# manually test with: 
# IPV4: echo $(curl -s https://api.ipify.org)
# IPV6: echo $(curl -s https://api6.ipify.org)
# IPV4/6: echo $(curl -s https://api64.ipify.org)
ip=$(curl -s https://api64.ipify.org)

# send address to CASlab server
curl -k -X POST -H "Content-Type: application/json" \
	-d '{"ip": "'$ip'","label": "'$label'"}' https://caslab.case.edu/team/

exit 0
