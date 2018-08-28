def blink_brightness(base):
    if base < 10 or base == 50:
        return 25
    if base < 50:
        return 5
    if base < 90:
        return 95
    return 75
