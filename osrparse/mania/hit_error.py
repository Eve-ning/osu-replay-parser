import sys, importlib
from dataclasses import dataclass, field
from typing import List

from osrparse import parse_replay_file, ReplayEvent, Replay
from reamber.osu.OsuMap import OsuMap

@dataclass
class ManiaHitErrorEvents:
    hit_error: List[List[int]]
    rel_error: List[List[int]]
    hit_map:   List[List[int]]
    rel_map:   List[List[int]]
    hit_rep:   List[List[int]]
    rel_rep:   List[List[int]]

@dataclass
class ManiaHitError:
    rep: Replay
    map: OsuMap
    keys: int   = field(init=False)
    judge: dict = field(init=False)
    debug: bool = False

    def __post_init__(self):
        self.keys = int(self.map.circleSize)
        OD = self.map.overallDifficulty
        self.judge = dict(
            J300G=16,
            J300=64 - 3 * OD,
            J200=97 - 3 * OD,
            J100=127 - 3 * OD,
            J50=151 - 3 * OD,
            JMISS=188 - 3 * OD,
        )

    @property
    def errors(self):
        hit_rep, rep_releases = self.parse_replay()
        hit_map, map_releases = self.parse_map()
        return self.sync(hit_map, map_releases, hit_rep, rep_releases)

    def parse_replay(self):
        rep_data = self.rep.play_data

        # Reformat data from relative offsets to absolute.
        prev = 0
        t = 0
        rep_events = []
        for d in rep_data:
            d: ReplayEvent
            t += d.time_since_previous_action
            if prev != d.x:
                rep_events.append((t, int(d.x)))
            prev = d.x

        # Reformat hits and rels to individual actions
        hit_rep = [[] for _ in range(self.keys)]
        rel_rep = [[] for _ in range(self.keys)]
        status = [False] * self.keys
        for ev in rep_events:

            offset = ev[0]
            keys = ev[1]

            if offset < 0: continue  # Ignore key presses < 0ms

            for k in range(self.keys):
                if keys & (2 ** k) != 0 and not status[k]:
                    # k is pressed and wasn't pressed before
                    hit_rep[k].append(offset)
                    # Update status to pressed
                    status[k] = True
                elif status[k] and keys & (2 ** k) == 0:
                    # k is not pressed and was pressed before
                    rel_rep[k].append(offset)
                    # Update status to released
                    status[k] = False

        return hit_rep, rel_rep

    def parse_map(self):
        hit_map_ = [*[(h.offset, h.column) for h in self.map.notes.hits()],
                    *[(h.offset, h.column) for h in self.map.notes.holds()]]
        rel_map_ = [(int(h.tailOffset()), h.column) for h in self.map.notes.holds()]

        hit_map = [[] for _ in range(self.keys)]
        for h in hit_map_:
            hit_map[h[1]].append(h[0])

        rel_map = [[] for _ in range(self.keys)]
        for h in rel_map_:
            rel_map[h[1]].append(h[0])

        hit_map = [sorted(i) for i in hit_map]
        rel_map = [sorted(i) for i in rel_map]

        return hit_map, rel_map

    def sync(self, hit_map, rel_map, hit_rep, rel_rep):
        hit_error = self._find_error(hit_map, hit_rep)
        rel_error = self._find_error(rel_map, rel_rep)
        return ManiaHitErrorEvents(hit_error=hit_error,
                                   rel_error=rel_error,
                                   hit_map=hit_map,
                                   rel_map=rel_map,
                                   hit_rep=hit_rep,
                                   rel_rep=rel_rep)

    # %%
    def _find_error(self, map, rep):
        error = [[] for _ in range(self.keys)]
        for k in range(self.keys):
            map_k = map[k]
            rep_k = rep[k]

            map_i = 0
            rep_i = 0
            while map_i < len(map_k) and rep_i < len(rep_k):
                map_hit = map_k[map_i]
                rep_hit = rep_k[rep_i]

                if rep_hit < map_hit - self.judge['JMISS']:
                    # Early No Hit
                    rep_i += 1
                    if self.debug: self. _print_status("--", k, rep_hit, map_hit)
                elif map_hit - self.judge['JMISS'] <= rep_hit < map_hit - self.judge['J50']:
                    # Early Miss
                    map_i += 1
                    rep_i += 1
                    error[k].append((rep_hit - map_hit))
                    if self.debug: self._print_status("EM", k, rep_hit, map_hit)
                elif map_hit - self.judge['J50'] <= rep_hit < map_hit + self.judge['JMISS']:
                    # Valid Hit
                    map_i += 1
                    rep_i += 1
                    error[k].append((rep_hit - map_hit))
                    if self.debug: self._print_status("OK", k, rep_hit, map_hit)
                elif rep_hit > map_hit + self.judge['JMISS']:
                    # Late No Hit
                    map_i += 1
                    error[k].append(self.judge['JMISS'])
                    if self.debug: self._print_status("LM", k, rep_hit, map_hit)
                else:
                    raise Exception(f"{map_hit} unmatched with {rep_hit}")
        return error

    @staticmethod
    def _print_status(status, col, hit, note):
        print(f"{status}, COL: {col}, Error: {hit - note:<5}, Hit: {hit:<6}, Note: {note:<6}")

    @classmethod
    def count_error(cls, error):
        JUDGE_COUNT = dict(
            J300G=0,
            J300=0,
            J200=0,
            J100=0,
            J50=0,
            JMISS=0
        )
        for key_error in error:
            for error_ in key_error:
                e = abs(error_)
                if e <= cls.judge['J300G']:
                    JUDGE_COUNT['J300G'] += 1
                elif e <= cls.judge['J300']:
                    JUDGE_COUNT['J300'] += 1
                elif e <= cls.judge['J200']:
                    JUDGE_COUNT['J200'] += 1
                elif e <= cls.judge['J100']:
                    JUDGE_COUNT['J100'] += 1
                elif e <= cls.judge['J50']:
                    JUDGE_COUNT['J50'] += 1
                else:
                    JUDGE_COUNT['JMISS'] += 1

        return JUDGE_COUNT


