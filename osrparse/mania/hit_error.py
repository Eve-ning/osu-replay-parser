import sys, importlib
from dataclasses import dataclass, field
from typing import List, Union, Tuple

from osrparse import parse_replay_file, ReplayEvent, Replay, Mod
from reamber.osu.OsuMap import OsuMap

@dataclass
class ManiaHitErrorEvents:
    hit_errors: List[List[List[int]]]
    rel_errors: List[List[List[int]]]
    hit_map:    List[List[int]]
    rel_map:    List[List[int]]
    ln_len_map: List[List[int]]
    hit_reps:   List[List[List[int]]]
    rel_reps:   List[List[List[int]]]

@dataclass
class ManiaHitError:
    reps: Union[List[Replay], Replay]
    map: OsuMap
    keys: int   = field(init=False)
    judge: dict = field(init=False)
    debug: bool = False

    def __post_init__(self):
        # Cast to list if not list
        self.reps = self.reps if isinstance(self.reps, list) else [self.reps]
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

    def errors(self):
        """ Parses Both replay and map and calculates their errors.

        :return dict(hit_error=hit_error,
                     rel_error=rel_error,
                     hit_map=hit_map,
                     rel_map=rel_map,
                     hit_reps=hit_reps,
                     rel_reps=rel_reps)
        """
        hit_rep, rel_rep = self.parse_replays()
        hit_map, rel_map, ln_len_map = self.parse_map(self.map)
        return self._sync(hit_map, rel_map, ln_len_map, hit_rep, rel_rep)

    def parse_replays(self) -> Tuple[List[List[List[int]]], List[List[List[int]]]]:
        """ Parses the map and returns the list of hit and release locations

        Returns Hit[Replay][Key][Offsets], Rel[Replay][Key][Offsets]

        :return rep_hit, rep_rel
        """
        hit_reps = []
        rel_reps = []
        for rep in self.reps:
            assert isinstance(rep, Replay), f"Recieved reps is not of Replay. {type(rep)}"
            rep_data = rep.play_data

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

            if rep.mod_combination == Mod.Mirror:
                hit_reps.append(list(reversed(hit_rep)))
                rel_reps.append(list(reversed(rel_rep)))
            else:
                hit_reps.append(hit_rep)
                rel_reps.append(rel_rep)

        return hit_reps, rel_reps

    @staticmethod
    def parse_map(map: OsuMap):
        """ Parses the map and returns the list of hit and release locations

        :return: map_hit, map_rel
        """
        hit_map_ = [*[(h.offset, h.column) for h in map.notes.hits()],
                    *[(h.offset, h.column) for h in map.notes.holds()]]
        rel_map_    = [(int(h.tailOffset()), h.column) for h in map.notes.holds()]
        ln_len_map_ = [(int(h.length), h.column) for h in map.notes.holds()]

        hit_map = [[] for _ in range(int(map.circleSize))]
        for h in hit_map_:
            hit_map[h[1]].append(h[0])

        rel_map = [[] for _ in range(int(map.circleSize))]
        for h in rel_map_:
            rel_map[h[1]].append(h[0])

        ln_len_map = [[] for _ in range(int(map.circleSize))]
        for h in ln_len_map_:
            ln_len_map[h[1]].append(h[0])

        hit_map    = [sorted(i) for i in hit_map]
        rel_map    = [sorted(i) for i in rel_map]
        ln_len_map = [sorted(i) for i in ln_len_map]

        return hit_map, rel_map, ln_len_map

    def _sync(self,
              hit_map: List[List[int]],
              rel_map: List[List[int]],
              ln_len_map: List[List[int]],
              hit_reps: List[List[List[int]]],
              rel_reps: List[List[List[int]]],
              ):
        hit_errors = self._find_error(hit_map, hit_reps)
        rel_errors = self._find_error(rel_map, rel_reps)
        return ManiaHitErrorEvents(hit_errors=hit_errors,
                                   rel_errors=rel_errors,
                                   hit_map=hit_map,
                                   rel_map=rel_map,
                                   hit_reps=hit_reps,
                                   rel_reps=rel_reps,
                                   ln_len_map=ln_len_map)

    # %%
    def _find_error(self,
                    map: List[List[int]],
                    reps: List[List[List[int]]]):
        # errors is for ALL REPLAYS
        errors = []
        for rep in reps:
            # error is for A SINGLE REPLAY
            error = [[] for _ in range(self.keys)]
            for k in range(self.keys):
                map_k = map[k]
                rep_k = rep[k]

                map_i = 0
                rep_i = 0
                while True:
                    if map_i >= len(map_k):
                        # map is complete
                        break
                    elif rep_i >= len(rep_k):
                        # replay is complete
                        # If map isn't complete, we need to pad it with the missing hits
                        # This occurs if the player just doesn't hit the last few notes.
                        for _ in range(map_i, len(map_k)):
                            error[k].append(self.judge['JMISS'])
                        break

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
                        # Not too sure if we have Late Misses
                        # If the judgement counts are off, this is the reason.
                        # Valid Hit
                        map_i += 1
                        rep_i += 1
                        error[k].append((rep_hit - map_hit))
                        if self.debug: self._print_status("OK", k, rep_hit, map_hit)
                    elif rep_hit >= map_hit + self.judge['JMISS']:
                        # Late No Hit
                        map_i += 1
                        error[k].append(self.judge['JMISS'])
                        if self.debug: self._print_status("--", k, rep_hit, map_hit)
                    else:
                        raise Exception(f"{map_hit} unmatched with {rep_hit}")
            errors.append(error)
        return errors

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


