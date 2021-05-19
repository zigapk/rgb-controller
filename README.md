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
2. Runs as root because I'm lazy.
3. Has no intended future use beyond my machine.

#### Requirements

1. Install Python requirements by running `sudo pip3 install requirements.txt`.
2. Install [OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB). I've built it from source.
3. Python 3. This only applies if you live under a rock. Though I wouldn't blame you after the 2020 we've had.

#### Usage

1. Modify any constants in `rgb_controller.py` you might desire.
2. Run:

```shell
    python3 rgb_controller.py aura [kraken_interval] [aura_interval]
```

to set the Aura and Kraken led strip color periodically based on time of day and CPU temperature.

Interval is any positive number and represents the time spent sleeping between color set cycles. Use -1 to only set
once. Note that the intervals are introduced to the cycle like `time.sleep(interval)` and therefore do not take into
account the active part of the cycle. In other words, they are nowhere near accurate.

#### Systemctl service

To run rgb_controller loop in the background (starting on boot), need to add two systemd services like this:

```shell script
sudo cp openrgb.service /etc/systemd/system/
sudo cp rgb_controller.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openrgb
sudo systemctl enable --now rgb_controller
```

`rgb_controller` service depends on `openrgb`, so make sure you start it first.
