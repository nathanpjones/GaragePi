# GaragePi
Overengineer your garage door with your Raspberry Pi!

Use a Raspberry Pi to open or close your garage door and to sense whether it's currently open. You can do this from the 
comfort of your couch or anywhere in the world (with an [appropriate VPN connection][vpn]). Your spouse may think you're 
crazy, but it's so cool!

I started with this guide by Chris Driscoll at [Driscosity]. Chris has an awesome guide with step-by-step
instructions, pictures, and even a video of the system in operation. I use this same hardware setup for GaragePi.

What he has is great for a simple opener and status display, but the second time I used it my relay got stuck closed
because of a connection issue (it's javascript based). I also wanted more features and more control over what was going
on.

So I wrote a [Flask] app (Python) with some JSON/jQuery for keeping the status updated. I also used Bootstrap for the
front end. All these are new to me so forgive / correct any noob mistakes.

[Flask]: http://flask.pocoo.org/

#### Feb 2016 Update - IFTTT Maker Support!

GaragePi now supports [IFTTT] alerts through the new [Maker Channel]. It will generate events when an open or close is
detected and even at a designated time.

See [below](#ifttt-events) for alert details and how to set them up.

I also pulled the app into two parts, one for the webserver and one that's always running and talking to the RPi. This 
makes it so the webserver doesn't have to run with root privileges. More importantly, this also enables a whole lot of 
other features that require running all the time instead of just within a web request.

#### Screenshots

<div>

<a href="http://www.nathanpjones.com/wp/wp-content/uploads/2015/08/01-Door-Open.png">
<img src="http://www.nathanpjones.com/wp/wp-content/uploads/2015/08/01-Door-Open.png" width="250" height="445">
</a>

<a href="http://www.nathanpjones.com/wp/wp-content/uploads/2015/08/02-Close-Button-Pushed.png">
<img src="http://www.nathanpjones.com/wp/wp-content/uploads/2015/08/02-Close-Button-Pushed.png" width="250" height="445">
</a>

<a href="http://www.nathanpjones.com/wp/wp-content/uploads/2015/08/03-After-Closed.png">
<img src="http://www.nathanpjones.com/wp/wp-content/uploads/2015/08/03-After-Closed.png" width="250" height="445">
</a>

<a href="http://www.nathanpjones.com/wp/wp-content/uploads/2015/08/04-History.png">
<img src="http://www.nathanpjones.com/wp/wp-content/uploads/2015/08/04-History.png" width="250" height="445">
</a>

<a href="http://www.nathanpjones.com/wp/wp-content/uploads/2015/08/05-History-Landscape.png">
<img src="http://www.nathanpjones.com/wp/wp-content/uploads/2015/08/05-History-Landscape.png" width="445" height="250">
</a>

</div> 

# Features

- Open / close the garage door with the press of a button.
- See if garage door is currently open.
- See history of when the door was opened or closed even when it wasn't opened/closed using the app.
- Garage door activity generates [IFTTT] events.
- Responsive UI for both desktop and mobile use.
- Show the RPI's internal temps because, well, I can.

#### Planned Features

I'm definitely planning on getting these done.

- Make the password configurable. You can change it yourself, but you have to edit a config file.
- ~~Send an alert if the door is open past a certain time. (I'm always leaving the door open all night.)~~ *Done!*

Okay, I might never implement these, but here are some ideas for what would make it even better (read more 
overengineered).

- Add a function to open the door just partway for ventilation.
- Close the door automatically at a certain time or after a certain amount of time.
- Show stats of how much time the door is open, what hours it's most open, or other interesting trends. 

# Installation

#### Online Installation

1. Follow all the instructions at [Driscosity] up until the point where he has you installing WebIOPi. Basically, just
   do the hardware bit and the RPi environment setup.
2. Run the fully automated installer by running this command logged into your Raspberry Pi.  

    `curl -s "https://raw.githubusercontent.com/nathanpjones/GaragePi/master/setup/online_install.sh" | bash`

    (If you want to know what's going on, here are the full contents of [online_install.sh] and then [setup.sh] that is 
called next.)

It will take a while for the setup scripts to run, but at the end you should be able to access your site at your 
Raspberry Pi's IP address.

The online install will put everything in `~/garage_pi`. Look to the `instance` subfolder for the app logs and the 
database.

#### Offline Install

If you want to pull down the repo manually (recommended if you want to choose where to install), all you have to do is
navigate to the project root folder and run the following command.

``` bash
source setup/setup.sh
```

#### Configuration

The app configuration file is found in `instance/app.cfg`.

1. Navigate to the project root. If you used the online installer, run `cd ~/garage_site`.
2. Run `nano instance/app.cfg` to open the config file.
3. Locate the `PASSWORD` field and change it from the default to something unique for you. You may also change the
   login `USERNAME` if you like.
4. Set the `RELAY_PIN` and `REED_PIN` if your hardware configuration differs from the [Driscosity] setup.
5. Have a look through the other settings such as the [IFTTT settings](#configuring-events) to see if any
   other changes are appropriate.
6. Press <kbd>CTRL</kbd>+<kbd>X</kbd>. Answer <kbd>Y</kbd> when prompted to save and then press <kbd>Enter</kbd> to
   overwrite the existing file.

#### Uninstall

I've included an uninstall script. You can run it with the following command.

``` bash
source setup/uninstall.sh
```

This isn't a complete uninstall because I don't keep track of everything you had installed when you started. It does 
remove the GaragePi related services and lets you know what else you might want to remove.

Once you've run the uninstall script, it's safe to simply delete the project root folder.

``` bash
rm -rf ~/garage_pi
```

# IFTTT Events

GaragePi supports generating [IFTTT] events using the [Maker Channel].

#### Available Events

- `garage_door_opened` - Fired when door is opened
- `garage_door_closed` - Fired when door is closed
- `garage_door_changed` - Fired when door is opened or closed. `Value1` is set to either `opened` or `closed`.
- `garage_door_warning` - Fired when door is open at a given time of day. `Value1` is set to `open`. 

#### Configuring Events

To enable IFTTT events, you must first obtain your maker key. You should see listed on the front page of the Maker
Channel.

1. Open up `instance/app.cfg`
2. Locate the line that starts with `IFTTT_MAKER_KEY` and input your maker key between the single quotes. It should 
   look something like, `IFTTT_MAKER_KEY = 'c-jfLKBJEfijas3r28VBL'`
3. If you want to use the door warning, change `DOOR_OPEN_WARNING_TIME` to the desired time. Make sure to use 24-hour
   format with just hours and seconds, for example, `DOOR_OPEN_WARNING_TIME = "18:30"`


[vpn]: http://readwrite.com/2014/04/10/raspberry-pi-vpn-tutorial-server-secure-web-browsing
[IFTTT]: https://ifttt.com/
[Maker Channel]: https://ifttt.com/maker
[online_install.sh]: https://github.com/nathanpjones/GaragePi/blob/master/setup/online_install.sh 
[setup.sh]: https://github.com/nathanpjones/GaragePi/blob/master/setup/setup.sh
[Driscosity]: http://www.driscocity.com/idiots-guide-to-a-raspberry-pi-garage-door-opener/
