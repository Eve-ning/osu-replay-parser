from pathlib import Path
from unittest import TestCase
import datetime

from reamber.osu import OsuMap

from osrparse import parse_replay, parse_replay_file, ReplayEvent, GameMode, Mod
from osrparse.mania import ManiaHitError

RES = Path(__file__).parent / "resources"

class TestManiaHitError(TestCase):

    @classmethod
    def setUpClass(cls):

        cls.replay1_path = RES / "chrono.osr"
        cls.replay2_path = RES / "vitality.osr"
        cls.replay3_path = RES / "robot.osr"
        cls.map1_path = RES / "chrono.osu"
        cls.map2_path = RES / "vitality.osu"
        cls.map2_path = RES / "robot.osu"

    def test_replay_mode(self):
        rep = parse_replay_file(self.replay2_path)
        map = OsuMap.readFile(self.map2_path)

        er = ManiaHitError(rep, map)
        errors = er.errors