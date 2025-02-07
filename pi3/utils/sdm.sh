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
if [ ! -f raspios_lite_arm64_latest.img ]; then
    echo -e "${GREEN}[INFO]${NC} raspios-official.img not found. Downloading the latest version..."
    curl -L -o raspios_lite_arm64_latest.img.xz https://downloads.raspberrypi.org/raspios_lite_arm64_latest
    echo -e "${GREEN}[INFO]${NC} Uncompressing the image..."
    unxz raspios_lite_arm64_latest.img.xz
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
[ -f $assets/my.plugins ] &&  mv $assets/my.plugins $assets/my.plugins.1

(cat <<EOF
# Plugin List generated $(date +"%Y-%m-%d %H:%M:%S")

# Delete default user pi if it exists
user:deluser=pi

# Add a new user ** change 'myuser' and 'mypassword' **
user:adduser=$username|password=$password

# Install btwifiset (Control Pi's WiFi from your phone)
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#btwifiset
# btwifiset:country=US|timeout=30

# Install apps
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#apps
# apps:name=mybrowsers|apps=firefox,chromium-browser
# apps:name=mytools|apps=keychain,lsof,iperf3,dnsutils

# Configure network ** change 'myssid' and 'mywifipassword' **
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#network
# network:ifname=wlan0|network:wifissid=myssid|wifipassword=mywifipassword|wificountry=US

# This configuration eliminates the need for piwiz 'Pi wizard' so disable it
disables:piwiz

# Uncomment to enable trim on all disks
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#trim-enable
# trim-enable

# Configure localization settings to the same as this system
# https://github.com/gitbls/sdm/blob/master/Docs/Plugins.md#l10n
L10n:host
EOF
    ) | bash -c "cat >|$assets/my.plugins"

sudo sdm --hostname $hostname --customize --plugin @$assets/my.plugins --restart raspios_lite_arm64_latest.img