from datetime import datetime
import time
import sensors
import sys
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType
from openrgb.orgb import Device

# Expected CPU temperature range.
CPU_TEMP_RANGE_MAX = 53
CPU_TEMP_RANGE_MIN = 38

# Desired color scheme.
CPU_TEMP_COLOR_MAX = 0xff0000
CPU_TEMP_COLOR_MIN = 0x9575CD
AURA_COLOR = 0x651FFF
KRAKEN_LOGO_COLOR = CPU_TEMP_COLOR_MIN

# Sunset and sunrise time in hours past midnight constants.
TIME_SUNRISE = 7.5  # 7:30 am
TIME_SUNSET = 19.5  # 7:30 pm

# Min and max brightness during the day.
BRIGHTNESS_AURA_MIN = 0.1
BRIGHTNESS_AURA_MAX = 0.7
BRIGHTNESS_KRAKEN_MIN = 0.4
BRIGHTNESS_KRAKEN_MAX = 1.0

# Sensor name and address.
SENSOR_PREFIX = 'k10temp'
SENSOR_ADDR = 195
SENSOR_FEATURE_LABEL = 'Tdie'


def hex_to_rgb(hex_color: int) -> tuple:
    """
    Converts hex color to red, green and blue components.
    :param hex_color: int
    :return: Tuple of ints (red, green, blue)
    """
    r = (hex_color & 0xff0000) >> 16
    g = (hex_color & 0x00ff00) >> 8
    b = (hex_color & 0x0000ff) >> 0
    return r, g, b


def rgb_to_hex(r: float, g: float, b: float) -> int:
    """
    Converts red, green and blue color components to hex value.
    :param r: Red.
    :param g: Green.
    :param b: Blue.
    :return: Hex color value.
    """

    # convert to int
    r = round(r)
    g = round(g)
    b = round(b)

    # handle out of range numbers
    r = min(max(0, r), 255)
    g = min(max(0, g), 255)
    b = min(max(0, b), 255)

    # join colors
    hex_color = (r << 16) | (g << 8) | b

    return hex_color


def validate_color(r: float, g: float, b: float) -> tuple:
    """
    Rounds the color components into ints and makes sure they are between 0 and 255.
    :param r: Red.
    :param g: Green.
    :param b: Blue.
    :return:
    """
    r, g, b = round(r), round(g), round(b)
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return r, g, b


def get_cpu_temperature() -> float:
    """
    Returns CPU temperature in degrees celsius read from sensors based on constants specified in file header.
    :return: CPU temperature in degrees celsius.
    """
    # Iter sensors.
    for chip in sensors.iter_detected_chips():
        if chip.addr == SENSOR_ADDR and chip.prefix.decode('utf-8') == SENSOR_PREFIX:
            # Sensor matches, try reading features.
            for feature in chip:
                if feature.label == SENSOR_FEATURE_LABEL:
                    return feature.get_value()


def get_brightness() -> float:
    """
    Calculate brightness ratio based on the time of day.
    :return: Brightness ratio between 0 and 1 (1 at mid_day and 0 during the night)
    """
    dt = datetime.now()
    hours = dt.hour + dt.minute / 60

    if hours <= TIME_SUNRISE or hours >= TIME_SUNSET:
        return 0

    # calculate mid_day time (does not necessarily match noon)
    mid_day = (TIME_SUNRISE + TIME_SUNSET) / 2

    if hours < mid_day:
        return (hours - TIME_SUNRISE) / (mid_day - TIME_SUNRISE)
    else:
        return 1 - (hours - mid_day) / (TIME_SUNSET - mid_day)


def get_kraken_brightness() -> float:
    """
    Calculates kraken brightness based on the time of day and BRIGHTNESS_KRAKEN_MIN and BRIGHTNESS_KRAKEN_MAX params.
    :return: Kraken brightness (float).
    """
    ratio = get_brightness()
    return BRIGHTNESS_KRAKEN_MIN + ratio * (BRIGHTNESS_KRAKEN_MAX - BRIGHTNESS_KRAKEN_MIN)


def get_aura_brightness() -> float:
    """
    Calculates AuraSync brightness based on the time of day and BRIGHTNESS_AURA_MIN and BRIGHTNESS_AURA_MAX params.
    :return: Aura brightness (float).
    """
    ratio = get_brightness()
    return BRIGHTNESS_AURA_MIN + ratio * (BRIGHTNESS_AURA_MAX - BRIGHTNESS_AURA_MIN)


def get_color() -> int:
    """
    Calculates color based on CPU temperature.
    Temperature over CPU_TEMP_RANGE_MAX results in CPU_TEMP_COLOR_MAX.
    Temperature below CPU_TEMP_RANGE_MIN results in CPU_TEMP_COLOR_MIN.
    :return: Hex color based on CPU temperature.
    """

    # cpu temperature in C
    temperature = get_cpu_temperature()

    # relative distance between MIN and MAX temperature
    ratio = (temperature - CPU_TEMP_RANGE_MIN) / (CPU_TEMP_RANGE_MAX - CPU_TEMP_RANGE_MIN)

    # clip ratio between 0 and 1
    ratio = min(1.0, max(0.0, ratio))

    # get color components
    r_min, g_min, b_min = hex_to_rgb(CPU_TEMP_COLOR_MIN)
    r_max, g_max, b_max = hex_to_rgb(CPU_TEMP_COLOR_MAX)

    # calculate colors
    r = ratio * (r_max - r_min) + r_min
    g = ratio * (g_max - g_min) + g_min
    b = ratio * (b_max - b_min) + b_min

    return rgb_to_hex(r, g, b)


def loop(interval: float, mod_aura: int):
    """
    Sets cooler color in a loop. Takes time of day and CPU temperature into account.
    :param interval: Time between cycles in seconds.
    :param mod_aura: How many kraken cycles pass between each aura cycle.
    :return:
    """
    # init sensors
    sensors.init()

    # init openrgb client
    client = OpenRGBClient()
    kraken = client.get_devices_by_type(DeviceType.LEDSTRIP)[0]  # weird type for a COOLER, I know
    ring = kraken.zones[1]
    logo = kraken.zones[2]
    aura = client.get_devices_by_type(DeviceType.MOTHERBOARD)[0]
    aura.zones[1].resize(120)

    # count kraken cycles
    count = 0

    while True:
        # calculate ring color based on CPU temperature
        ring_hex_color = get_color()
        r, g, b = hex_to_rgb(ring_hex_color)

        # calculate brightness
        brightness = get_kraken_brightness()

        # apply brightness
        r *= brightness
        g *= brightness
        b *= brightness

        # round to int
        r, g, b = validate_color(r, g, b)

        # set kraken ring color
        ring.set_color(RGBColor(r, g, b))

        # read logo color
        logo_hex_color = KRAKEN_LOGO_COLOR
        r, g, b = hex_to_rgb(logo_hex_color)

        # calculate logo brightness
        brightness = get_kraken_brightness()

        # apply brightness
        r *= brightness
        g *= brightness
        b *= brightness

        # round to int
        r, g, b = validate_color(r, g, b)

        # set logo color
        logo.set_color(RGBColor(r, g, b))

        # set aura color if needed
        if count % mod_aura == 0:
            set_aura_color(aura)
            count = 0

        # sleep for a predefined amount of time
        if interval < 0:
            return
        time.sleep(interval)
        count += 1


def set_aura_color(aura: Device):
    """
    Sets Aura color once.
    :return:
    """
    # use main color for aura
    hex_color = AURA_COLOR
    r, g, b = hex_to_rgb(hex_color)

    # calculate brightness
    brightness = get_aura_brightness()

    # apply brightness
    r *= brightness
    g *= brightness
    b *= brightness

    # round to int
    r, g, b = validate_color(r, g, b)
    # set aura sync color
    aura.set_color(RGBColor(r, g, b))


def main():
    if len(sys.argv) < 3:
        print('Invalid arguments, read the documentation first.')
        sys.exit(1)

    interval_kraken = float(sys.argv[1])
    interval_aura = float(sys.argv[2])
    loop(interval_kraken, round(interval_aura / interval_kraken))


if __name__ == '__main__':
    main()
