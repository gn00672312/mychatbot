import unittest
from datetime import datetime, timedelta
import sys

from mychatbot.echobot.views import get_weather_info, get_game_day_weather_info


class APITester(unittest.TestCase):

    def test_get_weather_info(self):
        today = datetime.utcnow() + timedelta(hours=8)

        sys.stdout.buffer.write(get_weather_info(today).encode("utf-8"))

    def test_get_game_day_weather_info(self):
        info = get_game_day_weather_info()

        sys.stdout.buffer.write(info.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
