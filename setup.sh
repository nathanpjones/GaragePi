#! /bin/sh

echo ""
echo "This will create the virtual environment for GaragePi."
echo " "
echo "WARNING: You should NOT run this with sudo!"
echo "			             			  "
echo "	    Press Enter when ready        "
echo "									  "

read

virtualenv --no-site-packages --distribute venv
&& source venv/bin/activate
&& pip install -r requirements.txt
