#!/bin/bash

# Make sure we're not running at root to start
if [ $(id -u) -eq 0 ]; then
  echo "This should not be run with sudo. It will be called for the"
  echo "commands that require it. Try again without sudo."
  exit 1
fi

SETUP_DIR=$(dirname $(readlink -f "${BASH_SOURCE}"))
DIR=$(dirname "$SETUP_DIR")
USER=$(id -u -n)
INSTANCE_DIR=${DIR}/instance
RESOURCE_DIR=${DIR}/resource
STATIC_DIR=${DIR}/webserver/static

# First make sure we're in the project root by checking for one of our source files
if [ ! -f ${DIR}/requirements.txt ]; then
  echo "This script should be located in the project root directory."
  exit 1
fi

if [ -z "$(python3 -V 2>/dev/null)" ]; then
  echo "Python 3 is required but isn't installed."
  echo "Easiest way to get it is to upgrade to Raspbian Jessie."
  exit 1
fi

echo "-------------------"
echo "Installing GaragePi"
echo "-------------------"

# Make sure we can update packages first. We'll need to install lighttpd later on.
if [ "$1" != "NO_APT_UPDATE" ]; then
  echo "Updating packages..."
  sudo apt-get update -q
  if [ $? -ne 0 ]; then
    echo "Failed to update packages. Check your internet connection."
    exit 1;
  fi
fi

# Make sure pip and virtualenv are installed. Install using python2 as this is more reliable.
echo "Installing pip..."
curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo python2
if [ $? -ne 0 ]; then exit 1; fi
echo -e "\nInstalling virtualenv..."
sudo pip install virtualenv
if [ $? -ne 0 ]; then exit 1; fi

# Install virtual environment and requirements
echo -e "\nSetting up virtual environment..."
virtualenv --python python3 --no-site-packages --distribute venv \
&& source venv/bin/activate \
&& pip install -r "${DIR}/requirements.txt"
if [ $? -ne 0 ]; then exit 1; fi

# Make an instance directory for the site's logs, database,
# and config and create a group that lets www-data and pi both have
# write access.
echo -e "\nCreating instance directory..."
mkdir -v "${INSTANCE_DIR}"
sudo groupadd garage_site
sudo usermod -a -G garage_site $USER
sudo usermod -a -G garage_site www-data
sudo chgrp -v -R garage_site "${INSTANCE_DIR}"
sudo chmod -v g+w "${INSTANCE_DIR}"

# Copy default config file over and generate key if
# config file doesn't already exist.
if [ ! -f "${INSTANCE_DIR}/app.cfg" ]; then
  cp "${RESOURCE_DIR}/default_app.cfg" "${INSTANCE_DIR}/app.cfg"
  python3 "${SETUP_DIR}/generate_secret_key.py" >> "${INSTANCE_DIR}/app.cfg"
fi

# Install the daemon for the backend
sudo cp "${SETUP_DIR}/garage_daemon.sh" /etc/init.d/garagepi
sudo sed -i -e "s#/home/pi/garagepi#${DIR}#g" /etc/init.d/garagepi
sudo chmod u+x /etc/init.d/garagepi
sudo update-rc.d garagepi defaults

# Get the name of the frontend host
ValidIpAddressRegex="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$";
ValidHostnameRegex="^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$";
echo -e "\n---------------------------------------------------\n"
read -p "Please enter the name or IP address of the frontend server: " FRONTEND
while ! [[ ${FRONTEND} =~ ${ValidIpAddressRegex} ]] && ! [[ ${FRONTEND} =~ ${ValidHostnameRegex} ]] ; do
    echo "### Invalid Entry ### - Please enter a valid IP address or hostname"
    echo -e "   For example: 31.13.70.36 or www.facebook.com\n---\n"
    read -p "Please enter the name or IP address of the FRONTEND server: " FRONTEND
done
sudo sed -i -e "s#www.mywebserver.com#${FRONTEND}#g" ${INSTANCE_DIR}/app.cfg

# Start the garagepi service
echo -e "\Starting 'garagepi' service..."
sudo service garagepi start

echo -e "\nAll done!"
