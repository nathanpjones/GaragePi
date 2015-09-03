#!/bin/bash

# Make sure we're not running at root to start
if [ $(id -u) -eq 0 ]; then
  echo "This should not be run with sudo. It will be called for the"
  echo "commands that require it. Try again without sudo."
else

DIR=$(dirname $(readlink -f "${BASH_SOURCE}"))
USER=$(id -u -n)

# First make sure we're in the project root by checking for one of our source files
if [ ! -f $DIR/garage.py ]; then
  echo "This script should be located in the project root directory."
else

  echo "-------------------"
  echo "Installing GaragePi"
  echo "-------------------"

  # Make sure pip and virtualenv are installed
  echo "Installing pip..."
  curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo python2.7
  echo -e "\nInstalling virtualenv..."
  sudo pip install virtualenv

  # Install virtual environment and requirements
  echo -e "\nSetting up virtual environment..."
  virtualenv --no-site-packages --distribute venv \
  && source venv/bin/activate \
  && pip install -r requirements.txt

  # Make sure our virtual environment's python runs with root privileges.
  # This is so RPi.GPIO has the privileges it needs.
  echo -e "\nLetting our virtual environment's python run as root..."
  sudo chown -v root:root "$DIR/venv/bin/python"
  sudo chmod -v u+s "$DIR/venv/bin/python"

  # Make a instance directory for the site's logs, database,
  # and config and create a group that lets www-data and pi both have
  # write access.
  echo -e "\nCreating instance directory..."
  mkdir -v "$DIR/instance"
  sudo groupadd garage_site
  sudo usermod -a -G garage_site $USER
  sudo usermod -a -G garage_site www-data
  sudo chgrp -v -R garage_site "$DIR/instance"
  sudo chmod -v g+w "$DIR/instance"
  
  if [ ! -f "$DIR/instance/app.cfg" ]; then
    # Copy sample config file over and generate key if
    # config file doesn't already exist.
    cp "$DIR/sample_app.cfg" "$DIR/instance/app.cfg"
    python "$DIR/generate_secret_key.py" >> "$DIR/instance/app.cfg"
  fi
  
  # Install lighttpd, enable fastcgi, and make our fcgi executable
  echo -e "\nInstalling lighttpd..."
  sudo apt-get install lighttpd
  echo -e "\nConfiguring lighttpd to run fastcgi..."
  sudo lighty-enable-mod fastcgi
  chmod -v +x "$DIR/garage.fcgi"
  
  # Add the server config to the end of the file
  echo -e "\nAdding fastcgi server to lighttpd.conf..."
  grep -lq 'BEGIN GaragePi SERVER' /etc/lighttpd/lighttpd.conf
  if [ ! $? -eq 0 ] ; then

sudo bash -c "cat >> /etc/lighttpd/lighttpd.conf << EOF

# BEGIN GaragePi SERVER
fastcgi.server = (\"/\" =>
    ((
        \"socket\" => \"/tmp/garage-fcgi.sock\",
        \"bin-path\" => \"${DIR}/garage.fcgi\",
        \"check-local\" => \"disable\",
        \"max-procs\" => 1,
        \"fix-root-scriptname\" => \"enable\",
    ))
)

alias.url = (
    \"/static/\" => \"${DIR}/static/\",
)
#END OF GaragePi SERVER
EOF"

  fi
  
  # Always restart lighttpd, even if the fastcgi server wasn't installed
  echo -e "\nRestarting lighttpd to pick up changes..."
  sudo service lighttpd restart

  echo -e "\nAll done!"
fi
fi
