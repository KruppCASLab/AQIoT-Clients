#!/bin/bash
cd /home/aqiot/aqiot
curl https://krupp.dev/aqiot/code.py > new.py
RC=$?
if [[ $RC -eq 0 ]]; then
  cp new.py code.py
else
  echo "run.sh - Could not check for update to script $RC"
fi
source .venv/bin/activate
python3 -u code.py