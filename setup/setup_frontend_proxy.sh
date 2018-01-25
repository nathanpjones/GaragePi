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

# Install the daemon for the proxy
sudo cp "${SETUP_DIR}/garage_proxy_daemon.sh" /etc/init.d/garagepiproxy
sudo sed -i -e "s#/home/pi/garagepiproxy#${DIR}#g" /etc/init.d/garagepiproxy
sudo chmod u+x /etc/init.d/garagepiproxy
sudo update-rc.d garagepiproxy defaults

# Install lighttpd, enable fastcgi, and make our fcgi executable
echo -e "\nInstalling lighttpd..."
sudo apt-get install lighttpd -y
if [ $? -ne 0 ]; then
    echo "There was a problem installing lighttpd. Setup cannot continue."
    exit 1
fi
echo -e "\nConfiguring lighttpd to run fastcgi..."
sudo lighty-enable-mod fastcgi
chmod -v +x "$DIR/start_webserver.fcgi"

# Add the server config to the end of the file
echo -e "\nAdding fastcgi server to lighttpd.conf..."
grep -lq 'BEGIN GaragePi SERVER' /etc/lighttpd/lighttpd.conf
if [ ! $? -eq 0 ] ; then

  sudo bash -c "cat >> /etc/lighttpd/lighttpd.conf << EOF

# BEGIN GaragePi SERVER
fastcgi.server = (\"/\" =>
    ((
        \"socket\" => \"/tmp/garage-fcgi.sock\",
        \"bin-path\" => \"${DIR}/start_webserver.fcgi\",
        \"check-local\" => \"disable\",
        \"max-procs\" => 1,
        \"fix-root-scriptname\" => \"enable\",
    ))
)

alias.url += (
    \"/static/\" => \"${STATIC_DIR}/\",
)
#END OF GaragePi SERVER
EOF"

fi

# Start the garagepi service
echo -e "\Starting 'garagepi' service..."
sudo service garagepi start

# Always restart lighttpd, even if the fastcgi server wasn't installed
echo -e "\nRestarting lighttpd to pick up changes..."
sudo service lighttpd restart

echo -e "\nAll done!"
