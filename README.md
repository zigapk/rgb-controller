# RGB Controller (needs a better name)

I've got a PC with:
- [NZXT Kraken X53](https://www.nzxt.com/products/kraken-x53) cooler and
- [Aura Sync](https://www.asus.com/campaign/aura/us/download.php) motherboard with some led strips attached.

It runs various distributions of Linux, changing on an almost weekly basis.

I wanted a controller that:
1. Uses static color for all the led strips but changes brightness over the day.
2. Sets the NZXT cooler color based on the CPU temperature and brightness (same as above).

This is an attempt at that. It works perfectly fine on my machine. **However**:
1. It has a ton of things hardcoded and likely needs to be modified to work on your computer.
2. Sets colors via shell commands, which is not ideal.
3. Runs as root because I'm lazy.
4. Has no intended future use beyond my machine.

#### Requirements
1. Install Python requirements by running `sudo pip3 install requirements.txt`.
2. Install [OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB). I've build it from source.
3. Python 3. This only applies if you live under a rock. Though I wouldn't blame you after the 2020 we've had.


#### Usage
1. Modify any constants in `rgb_controller.py` you might desire.
2. Run:
- `python3 rgb_controller.py aura` to set the Aura led strip color or
- `python3 rgb_controller.py kraken <interval>` to set the CPU cooler color periodically.

Interval is any positive number and represents the time spent sleeping between color sets. Use -1 to only set once.


#### Systemctl service
To run Kraken color loop in the background (starting on boot), you might want to add systemd service like this one:
```ini
[Unit]
Description=NZXT Kraken AIO liquid cooler RGB controller.

[Service]
WorkingDirectory=/opt/rgb_controller/
ExecStart=/usr/bin/python3 /opt/rgb_controller/rgb_controller.py kraken 0.1
Restart=on-failure

[Install]
WantedBy=default.target
```
Save it as `/etc/systemd/system/kraken_controller.service`, then run:
```shell script
sudo systemctl daemon-reload
sudo systemctl start/enable kraken_controller
```

Additionally, to set Aura brightness every 2 minutes, add a cronjob:
```
*/2 * * * * /usr/bin/python3 /opt/rgb_controller/rgb_controller.py aura
```  

If you want to set aura colors the moment OS boots up, add another systemd service:
```ini
[Unit]
Description=Aura sync color set on boot.

[Service]
Type=oneshot
WorkingDirectory=/opt/rgb_controller/
ExecStart=/usr/bin/python3 /opt/rgb_controller/rgb_controller.py aura

[Install]
WantedBy=default.target
```