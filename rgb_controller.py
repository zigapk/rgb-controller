from datetime import datetime
import time
import sensors
import sys
import subprocess

# Expected CPU temperature range.
CPU_TEMP_RANGE_MAX = 53
CPU_TEMP_RANGE_MIN = 33

# Desired color scheme.
# CPU_TEMP_COLOR_MAX = 0xD500F9
CPU_TEMP_COLOR_MAX = 0xff0000
CPU_TEMP_COLOR_MIN = 0xffffff
KRAKEN_LOGO_COLOR = CPU_TEMP_COLOR_MIN

# Sunset and sunrise time in hours past midnight constants.
TIME_SUNRISE = 7.5  # 7:30 am
TIME_SUNSET = 19.5  # 7:30 pm

# Min and max brightness during the day.
BRIGHTNESS_AURA_MIN = 0.01
BRIGHTNESS_AURA_MAX = 0.65
BRIGHTNESS_KRAKEN_MIN = 0.25
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


def set_aura_static_color(hex_color: int):
    """
    Sets Aura Sync color to static using OpenRGB binary via shell interface.
    :param hex_color: Hex color to set.
    :return:
    """
    cmd = ['OpenRGB', '-d', '0', '-c', '{0:06X}'.format(hex_color)]
    subprocess.run(cmd)


def set_kraken_static_color(hex_color: int, ring=False, logo=False):
    """
    Sets NZXT Kraken color to static using liquidctl via shell interface.
    :param logo: Set logo color.
    :param ring: Set ring color.
    :param hex_color:
    :return:
    """
    if ring and logo:
        cmd = ['liquidctl', 'set', 'sync', 'color', 'fixed', '{0:06X}'.format(hex_color)]
        subprocess.run(cmd)
    elif ring:
        cmd = ['liquidctl', 'set', 'ring', 'color', 'fixed', '{0:06X}'.format(hex_color)]
        subprocess.run(cmd)
    elif logo:
        cmd = ['liquidctl', 'set', 'logo', 'color', 'fixed', '{0:06X}'.format(hex_color)]
        subprocess.run(cmd)


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


def get_brightness(kraken=False, aura=False) -> float:
    """
    Calculates brightness based on the time of day.
    Linear scale between SUNRISE and SUNSET is used.
    :return: Brightness between BRIGHTNESS_MIN and BRIGHTNESS_MAX.
    """

    # check arguments
    if not kraken and not aura:
        raise
    if aura and kraken:
        raise

    brightness_min = BRIGHTNESS_KRAKEN_MIN if kraken else BRIGHTNESS_AURA_MIN
    brightness_max = BRIGHTNESS_KRAKEN_MAX if kraken else BRIGHTNESS_AURA_MAX

    dt = datetime.now()
    hours = dt.hour + dt.minute / 60

    # return minimal brightness over night
    if hours <= TIME_SUNRISE or hours >= TIME_SUNSET:
        return brightness_min

    # calculate mid_day time (does not necessarily match noon)
    mid_day = (TIME_SUNRISE + TIME_SUNSET) / 2

    if hours <= mid_day:
        # morning
        ratio = (hours - TIME_SUNRISE) / (mid_day - TIME_SUNRISE)
        return ratio * (brightness_max - brightness_min) + brightness_min
    else:
        # afternoon
        ratio = (hours - mid_day) / (TIME_SUNSET - mid_day)
        return ratio * (brightness_max - brightness_min) + brightness_min


def get_color() -> int:
    """
    Calculates color based on CPU temperature.
    Temperature over CPU_TEMP_RANGE_MAX results in CPU_TEMP_COLOR_MAX.
    Temperature below CPU_TEMP_RANGE_MIN results in CPU_TEMP_COLOR_MIN.
    :return: Hex color based on CPU temperature.
    """

    # cpu temperature in C
    temp = get_cpu_temperature()

    # relative distance between MIN and MAX temperature
    ratio = (temp - CPU_TEMP_RANGE_MIN) / (CPU_TEMP_RANGE_MAX - CPU_TEMP_RANGE_MIN)

    # clip ratio between 0 and 1
    ratio = min(1, max(0, ratio))

    # get color components
    r_min, g_min, b_min = hex_to_rgb(CPU_TEMP_COLOR_MIN)
    r_max, g_max, b_max = hex_to_rgb(CPU_TEMP_COLOR_MAX)

    # calculate colors
    r = ratio * (r_max - r_min) + r_min
    g = ratio * (g_max - g_min) + g_min
    b = ratio * (b_max - b_min) + b_min

    return rgb_to_hex(r, g, b)


def run_kraken(interval: float):
    """
    Sets cooler color in a loop. Takes time of day and CPU temperature into account.
    :param interval: Time between cycles in seconds.
    :return:
    """
    # init sensors
    sensors.init()

    while True:
        # calculate ring color based on CPU temperature
        ring_hex_color = get_color()
        r, g, b = hex_to_rgb(ring_hex_color)

        # calculate brightness
        brightness = get_brightness(kraken=True)

        # apply brightness
        r *= brightness
        g *= brightness
        b *= brightness

        # set kraken ring color
        set_kraken_static_color(rgb_to_hex(r, g, b), ring=True)

        # read logo color
        logo_hex_color = KRAKEN_LOGO_COLOR
        r, g, b = hex_to_rgb(logo_hex_color)

        # calculate logo brightness
        brightness = get_brightness(kraken=True)

        # apply brightness
        r *= brightness
        g *= brightness
        b *= brightness

        # set logo color
        set_kraken_static_color(rgb_to_hex(r, g, b), logo=True)

        # sleep for a predefined amount of time
        if interval < 0:
            return
        time.sleep(interval)


def run_aura():
    """
    Sets the Aura Sync color and brightness based on the current time of day.
    :return:
    """
    # use main color for aura
    hex_color = CPU_TEMP_COLOR_MIN
    r, g, b = hex_to_rgb(hex_color)

    # calculate brightness
    brightness = get_brightness(aura=True)

    # apply brightness
    r *= brightness
    g *= brightness
    b *= brightness

    # set aura sync color
    set_aura_static_color(rgb_to_hex(r, g, b))


def refuse_to_work():
    """
    A dummy panic function.
    :return:
    """
    print('Invalid arguments, read the documentation first.')
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        refuse_to_work()

    cmd = sys.argv[1]

    if cmd == 'kraken':
        if len(sys.argv) < 3:
            refuse_to_work()

        # run kraken loop
        interval = float(sys.argv[2])
        run_kraken(interval)

    elif cmd == 'aura':
        run_aura()
    else:
        refuse_to_work()


if __name__ == '__main__':
    main()
