#!/bin/bash

GREEN='\033[0;32m'
ORANGE='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if sdm is installed
if ! command -v sdm &> /dev/null
then
    echo -e "${GREEN}[INFO]${NC} sdm is not installed. Installing..."
    curl -L https://raw.githubusercontent.com/gitbls/sdm/master/EZsdmInstaller | bash
else
    echo -e "${GREEN}[INFO]${NC} sdm is already installed."
fi

# Check if .img exists
if [ ! -f build/raspios_lite_arm64_latest.img ]; then
    echo -e "${GREEN}[INFO]${NC} raspios-official.img not found. Downloading the latest version..."
    curl -L -o build/raspios_lite_arm64_latest.img.xz https://downloads.raspberrypi.org/raspios_lite_arm64_latest
    echo -e "${GREEN}[INFO]${NC} Uncompressing the image..."
    unxz build/raspios_lite_arm64_latest.img.xz
    echo -e "${GREEN}[INFO]${NC} Download and rename completed."
else
    echo -e "${GREEN}[INFO]${NC} raspios_lite_arm64_latest.img already exists."
fi

# Request and save hostname, username, and password
read -p "Enter hostname: " hostname
read -p "Enter username: " username
read -p "Enter password: " password
echo

echo -e "${GREEN}[INFO]${NC} Hostname: $hostname"
echo -e "${GREEN}[INFO]${NC} Username: $username"
echo -e "${GREEN}[INFO]${NC} Password: $password"

echo -e "${GREEN}[INFO]${NC} Hostname, username, and password have been saved to variables."

[ $EUID -eq 0 ] && sudo="" || sudo="sudo"

[ "$sudo" != "" ] && assets="." || assets="/etc/sdm/local-assets"
[ -f $assets/build/my.plugins ] &&  mv $assets/build/my.plugins $assets/build/my.plugins.1

## ================================================
## Create a plugin list
## ================================================
(cat <<EOF
# Plugin List generated $(date +"%Y-%m-%d %H:%M:%S")

# Delete default user pi if it exists
user:deluser=pi

# Add a new user ** change 'myuser' and 'mypassword' **
user:adduser=$username|password=$password

# Install btwifiset (Control Pi's WiFi from your phone)
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#btwifiset
# btwifiset:country=US|timeout=30

# Unintall and Install apps
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#apps
# apps:remove=python3|apps=pypy3-dev
# apps:apps=python3.11-dev
apps:apps=pypy3-dev

# Copy files to Pi
# 
copyfile:"from=../code.py|to=/home/$username/AQIoT/|mkdirif=yes"
copyfile:"from=../config.json|to=/home/$username/AQIoT/|mkdirif=yes"
copyfile:"from=../requirements.txt|to=/home/$username/AQIoT/|mkdirif=yes"
copyfile:"from=../.bashrc|to=/home/$username/"

# Configure network ** change 'myssid' and 'mywifipassword' **
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#network
# network:ifname=wlan0|wifissid=myssid|wifipassword=mywifipassword|wificountry=US

# This configuration eliminates the need for piwiz 'Pi wizard' so disable it
disables:piwiz

# Uncomment to enable trim on all disks
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#trim-enable
# trim-enable

# Configure localization settings to the same as this system
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#l10n
L10n:host

# Configure the serial port
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#serial
serial:disableshell|enableuart

EOF
    ) | bash -c "cat >|$assets/build/my.plugins"

## ================================================
## Setup Python Virtual Environment in Post-Install
## ================================================

(cat <<EOF
#!/bin/bash
#
# Sample sdm Custom Phase script
#
function loadparams() {
    source \$SDMPT/etc/sdm/sdm-readparams
}
# \$1 is the phase: "0", "1", or "post-install"

#
# Main code for the script
#
phase=\$1
pfx="\$(basename \$0)"     #For messages
loadparams

if [ \$phase == "0" ]
then
    #
    # In Phase 0 all references to directories in the image must be preceded by \$SDMPT
    #
    logtoboth "* \$pfx Phase 0"

# INSERT Your Custom Phase 0 code here
    
    logtoboth "* \$pfx Phase 0 Completed"

elif [ "\$phase" == "1" ]
then
    #
    # Phase 1 (in nspawn)
    #
    logtoboth "* \$pfx Phase 1"
    logfreespace "at start of \$pfx Phase 1"
    #
    # INSERT your Custom Phase 1 customization stuff here
    # In Phase 1 all references to directories in the image can be direct
    #
    logfreespace "at end of \$pfx Phase 1"
    logtoboth "* \$pfx Phase 1 Completed"
else
    #
    # Post-install edits
    #
    logtoboth "* \$pfx Custom Phase post-install"
    logfreespace "at start of \$pfx Custom Phase post-install"
    #
    # INSERT Your Custom Phase post-install code here
    # In Phase post-install all references to directories in the image can be direct
    #
    # cd /home/$username/
    # source .bashrc
    pypy3 -m venv /home/$username/.aqiotenv
    /home/$username/.aqiotenv/bin/python -m pip install -r /home/$username/AQIoT/requirements.txt
    chown $username:$username /home/$username/ -R

    logfreespace "at end of \$pfx Custom Phase post-install"
    logtoboth "* \$pfx Custom Phase post-install Completed"
fi
EOF
    ) | bash -c "cat >|$assets/build/python-setup"

sudo sdm --hostname $hostname --customize --plugin @$assets/build/my.plugins --cscript $assets/build/python-setup --restart build/raspios_lite_arm64_latest.img  --extend --xmb 512