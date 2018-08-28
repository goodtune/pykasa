import json
import uuid

import requests
from pykasa.utils import blink_brightness


class KasaAPI(object):
    """
    API interactions.
    """

    ENDPOINT = "https://wap.tplinkcloud.com/"

    @property
    def url(self):
        return self.ENDPOINT + "?token=" + self.token

    def get_device_dict(self):
        return {device["deviceId"]: device for device in self.get_device_list()}

    def get_device_list(self):
        res = requests.post(self.url, json=dict(method="getDeviceList"))
        res.raise_for_status()
        data = res.json()
        return data["result"]["deviceList"]

    def _passthrough(self, device_id, cmd):
        res = requests.post(
            self.url,
            json=dict(
                method="passthrough",
                params=dict(deviceId=device_id, requestData=json.dumps(cmd)),
            ),
        )
        res.raise_for_status()
        return res.json()

    def set_brightness(self, bulb, brightness=None, duration=1.0):
        cmd = {
            "smartlife.iot.smartbulb.lightingservice": {
                "transition_light_state": {
                    "brightness": brightness,
                    "transition_period": 1000 * duration,
                }
            }
        }
        return self._passthrough(bulb, cmd)

    def turn_off_bulb(self, bulb):
        cmd = {
            "smartlife.iot.smartbulb.lightingservice": {
                "transition_light_state": {"on_off": 0}
            }
        }
        return self._passthrough(bulb, cmd)

    def turn_on_bulb(self, bulb, brightness=None, duration=1.0):
        cmd = {
            "smartlife.iot.smartbulb.lightingservice": {
                "transition_light_state": {"on_off": 1}
            }
        }
        if brightness is not None:
            return (
                self._passthrough(bulb, cmd),
                self.set_brightness(bulb, brightness, duration),
            )
        return (self._passthrough(bulb, cmd), None)

    def blink(self, bulb, count=1, brightness=None):
        cmd = {"smartlife.iot.smartbulb.lightingservice": {"get_light_state": ""}}
        raw = self._passthrough(bulb, cmd)["result"]["responseData"]
        data = json.loads(raw)
        state = data["smartlife.iot.smartbulb.lightingservice"]["get_light_state"]

        on_off = bool(state["on_off"])

        if on_off:
            on_brightness = state["brightness"]
        else:
            on_brightness = state["dft_on_state"]["brightness"]

        # If not specified, attempt to pick a suitable blink brightness based
        # on the current brightness setting.
        if brightness is None:
            brightness = blink_brightness(on_brightness)

        # Start our blink. If off, turn on before flicking to new brightness.
        if not on_off:
            self.turn_on_bulb(bulb, brightness)
        else:
            self.set_brightness(bulb, brightness)

        # Restore the brightness. This is the count=1 scenario complete (unless
        # we turned on first, in which case we'll turn off below).
        self.set_brightness(bulb, on_brightness)

        # Perform any additional flickers if count > 1.
        for i in range(1, count):
            self.set_brightness(bulb, brightness)
            self.set_brightness(bulb, on_brightness)

        # Turn off again if we sparked up to perform our flicker.
        if not on_off:
            self.turn_off_bulb(bulb)


class TokenAPI(KasaAPI):
    """
    When you already have your token, pass it directly in.
    """

    def __init__(self, token):
        self.token = token


class UsernameAPI(KasaAPI):
    """
    When you have a username and password, determine the token.
    """

    def __init__(self, username, password):
        res = requests.post(
            self.ENDPOINT,
            json=dict(
                method="login",
                params=dict(
                    appType="Kasa_Android",
                    cloudUserName=username,
                    cloudPassword=password,
                    terminalUUID=str(uuid.uuid4()),
                ),
            ),
        )
        res.raise_for_status()
        data = res.json()
        self.token = data["result"]["token"]
