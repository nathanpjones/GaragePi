# GaragePi
Overengineer your garage door with your Raspberry Pi!

Use a Raspberry Pi to open or close your garage door and to sense whether it's currently open.
Your spouse will think you're crazy, but it's so cool!

I started with this guide by Chris Driscoll at [Driscosity](http://www.driscocity.com/idiots-guide-to-a-raspberry-pi-garage-door-opener/).
Chris has an awesome guide with step-by-step instructions, pictures, and even a video of the
system in operation. I use this same setup for GaragePi.

What he has is great for a simple opener and status display, but the second time I used it my relay got stuck
closed because of a connection issue (it's javascript based). I also wanted more features and more control
over what was going on.

So I wrote a [Flask](http://flask.pocoo.org/) app (Python) with some JSON/jQuery for keeping the status updated.
I also used Bootstrap for the front end. All these are new to me so forgive / correct any noob mistakes.

# Features

- Open / close the garage door with the press of a button.
- See if garage door is currently open.
- See history of when the door was opened or closed even when it wasn't opened/closed using the app.
- Responsive UI for both desktop and mobile use.
- Show the RPI's internal temps because, well, I can.

#### Planned Features

I'm definitely planning on getting these done.

- Simplify the installation--yeesh it's long.
- Make the password configurable. You can change it yourself, but you have to edit the python source file. Yuck!
- Send an alert if the door is open past a certain time. (I'm always leaving the door open all night.)

Okay, I might never implement these, but here are some ideas for what would make it even better (read more overengineered).

- Add a function to open the door just partway for ventilation.
- Close the door automatically at a certain time or after a certain amount of time.
- Show stats of how much time the door is open, what hours is it most open, 

# Installation

1. Follow all the instructions at [Driscosity](http://www.driscocity.com/idiots-guide-to-a-raspberry-pi-garage-door-opener/)
up until the point where he has you installing WebIOPi.
2. First we need to install git and pull down this repo. Alternatively, you can download these files
some other way. Just put it in `~/garage` to match below.

    ``` bash
    sudo apt-get install git  
    cd ~  
    git clone https://github.com/nathanpjones/GaragePi.git garage
    cd ~/garage
    ```

3. Now we need to set up a virtual environment for the web app.

    ``` bash
    sudo easy_install pip
    sudo pip install virtualenv
    ./setup.sh
    ```
    
4. For the RPi.GPIO library to work correctly, it has to run with root privileges. We'll accomplish this by
having our virtual environment's Python instance to run as root.

    ``` bash
    sudo chown -v root:root ~/garage/venv/bin/python
    sudo chmod u+s ~/garage/venv/bin/python
    ```
    
5. Now we need to create and give the proper access to the `data` folder so everyone can write to it.
***This assumes your username is "pi".***

    ``` bash
    sudo groupadd garage_site
    sudo usermod -a -G garage_site pi
    sudo usermod -a -G garage_site www-data
    sudo chgrp -R garage_site ~/garage/data
    sudo chmod g+w ~/garage/data
    ```

6. Now we need to install and setup the web server that will host our site.
We'll use [lighttpd](http://www.lighttpd.net/) because it's lightweight.

    ``` bash
    sudo apt-get install lighttpd
    ```

7. Let's mark our "fcgi" file as executable so lighttpd can run it.

    ``` bash
    chmod +x ~/garage/garage.fcgi
    ```

8. Now we have to edit lighttpd's config file to start our web app. I prefer nano, but you can use
whichever editor you like.

    ``` bash
    sudo nano /etc/lighttpd/lighttpd.conf
    ```
    
    Add the following line to the `server.modules = (...)` section:
    ```
    "mod_fastcgi",
    ```
    
    Add this section to the end of the file:
    ```
    fastcgi.server = ("/" =>
        ((
            "socket" => "/tmp/garage-fcgi.sock",
            "bin-path" => "/home/pi/garage/garage.fcgi",
            "check-local" => "disable",
            "max-procs" => 1,
            "fix-root-scriptname" => "enable",
        ))
    )

    alias.url = (
        "/static/" => "/home/pi/garage/static/",
    )
    ```

9. Now we have to restart lighttpd to pick up the config changes.

    ``` bash
    sudo service lighttpd restart
    ```
    
10. Whew! That's it. You should now be able to see your web app by going to your raspberry pi's IP address.
