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

- Make the password configurable. You can change it yourself, but you have to edit the python source file. Yuck!
- Send an alert if the door is open past a certain time. (I'm always leaving the door open all night.)

Okay, I might never implement these, but here are some ideas for what would make it even better (read more overengineered).

- Add a function to open the door just partway for ventilation.
- Close the door automatically at a certain time or after a certain amount of time.
- Show stats of how much time the door is open, what hours is it most open, 

# Installation

#### Online Installation

1. Follow all the instructions at [Driscosity](http://www.driscocity.com/idiots-guide-to-a-raspberry-pi-garage-door-opener/)
up until the point where he has you installing WebIOPi.
2. Run the fully automated installer by running this command logged into your Raspberry Pi.

    `curl -s "https://raw.githubusercontent.com/nathanpjones/GaragePi/master/online_install.sh" | bash`

(Click here to view the full contents of [online_install.sh](https://github.com/nathanpjones/GaragePi/blob/master/online_install.sh)
and then [setup.sh](https://github.com/nathanpjones/GaragePi/blob/master/setup.sh) that it will call.)

It might take a while for all this to work, but at the end you should be able to access your site at your Raspberry Pi's
IP address.

This will put everything in `~/garage_pi`. Look to the `data` subfolder for the app logs and the database.

#### Offline Install

If you want to pull down the repo manually (recommended if you want to choose where to install), all you have 
to do is run `setup.sh` in the project root folder.

``` bash
chmod -v +x setup.sh
./setup.sh
```