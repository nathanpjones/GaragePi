#!/usr/bin/env bash

# Make sure we're not running at root to start
if [ $(id -u) -eq 0 ]; then
  echo "This should not be run with sudo. It will be called for the"
  echo "commands that require it. Try again without sudo."
else

SETUP_DIR=$(dirname $(readlink -f "${BASH_SOURCE}"))
DIR=$(dirname "$SETUP_DIR")

# Remove backend service
echo "Stopping garagepi service..."
sudo service garagepi stop
echo "Removing garagepi service from startup list..."
sudo update-rc.d garagepi remove
echo "Removing garagepi service..."
sudo rm /etc/init.d/garagepi

# Remove fastcgi server config
echo -e "\nStopping lighttpd..."
sudo service lighttpd stop
echo "Removing fastcgi server from lighttpd config..."
sudo sed -i '/# BEGIN GaragePi SERVER/,/#END OF GaragePi SERVER/d' /etc/lighttpd/lighttpd.conf

# Remove specially created user group
echo -e "\nRemoving 'garage_site' group..."
sudo groupdel garage_site

cat << EOF

UNINSTALL COMPLETE!

Services were removed, however, not everything was undone since we
don't want to uninstall things you may want to keep.

Here are some commands for a full uninstall:
  sudo apt-get remove --purge git
  sudo lighty-disable-mod fastcgi
  sudo apt-get remove --purge lighttpd
  rm -rf "${DIR}"
EOF

fi
