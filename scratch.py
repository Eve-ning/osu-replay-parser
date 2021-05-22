import sys, importlib

from matplotlib import pyplot as plt

from osrparse import parse_replay_file, ReplayEvent
from osrparse.mania import ManiaHitError
from reamber.osu.OsuMap import OsuMap
import numpy as np
import pandas as pd
from os import walk
#%%
MAP = "azimuth"
_, _, filenames = next(walk(f"rsc/{MAP}/rep/"))
reps = [parse_replay_file(f"rsc/{MAP}/rep/{f}") for f in filenames]
map = OsuMap.readFile(f"rsc/{MAP}/{MAP}.osu")
#%%
er = ManiaHitError(reps, map)
errors = er.errors()

rep_errors = []
for rep_hit_error, rep_rel_error in zip(errors.hit_errors, errors.rel_errors):
    rep_errors.append([*[e for k in rep_hit_error for e in k],
                       *[e for k in rep_rel_error for e in k]])
map_hit    = [e for k in errors.hit_map for e in k]
map_rel    = [e for k in errors.rel_map for e in k]
map_ln_len = [e for k in errors.ln_len_map for e in k]
#%%
INTERVAL = 5
LN_WGT = 0.25
map_ln_wgt = (np.asarray(map_ln_len) / 400) - 1
ar_map = np.asarray([*map_hit, *map_rel])
ar_wgt = np.hstack([np.ones(len(map_hit)),
                    np.ones(len(map_rel)) *
                    np.sqrt(np.where(map_ln_wgt < 0, 0, map_ln_wgt) + 1)])

df_map = pd.DataFrame(ar_wgt, index=ar_map)
df_map = df_map.sort_index()
df_map.index = pd.to_datetime(df_map.index, unit='ms')

df_map_roll = df_map.groupby(pd.Grouper(freq=f'{INTERVAL}s')).sum() / INTERVAL
df_map_roll['std'] = ((df_map_roll - df_map_roll.mean()) / df_map_roll.std())

ar_error = np.asarray(rep_errors, dtype=int)
df_error = pd.DataFrame(np.abs(ar_error.transpose()), index=ar_map)
df_error = df_error.sort_index()
df_error.index = pd.to_datetime(df_error.index, unit='ms')

df_error_roll = df_error.groupby(pd.Grouper(freq=f'{INTERVAL}s')).sum() / INTERVAL
df_error_roll = (df_error_roll - df_error_roll.mean()) / df_error_roll.std()
df_error_roll['mean'] = df_error_roll.mean(axis=1)
#%%
plt.style.use('dark_background')
fig, ax1 = plt.subplots(2, sharex=True, figsize=(10,5))

ax1[0].plot(df_error_roll.loc[:, df_error_roll.columns != 'mean'], linewidth=1, c='gray', alpha=0.7)
ax1[0].plot(df_error_roll.loc[:, df_error_roll.columns == 'mean'], linewidth=3, c='orange', alpha=0.8)
ax1[0].set_ylabel('Error', c='orange')
ax1[0].tick_params(axis='y', labelcolor='orange')
ax1[0].tick_params(bottom=False,
                labelbottom=False)
ax1[0].title.set_text("Top 15 Azimuth Dan (Hit Error & Density)")

ax2 = ax1[0].twinx()
ax2.plot(df_map_roll[0], label='Density', linewidth=3, alpha=0.5, c='cyan')
ax2.set_ylabel('Density', c='cyan')
ax2.tick_params(axis='y', labelcolor='cyan')

df = df_error_roll['mean'] - df_map_roll['std']
ax1[1].plot(df, label='Difference', linewidth=3, c='white', alpha=0.6)
ax1[1].axhline(y=0, color='gray', linestyle='-')
ax1[1].set_xlabel('Time')
ax1[1].set_ylabel('Difference')
ax1[1].tick_params(axis='y')
ax1[1].tick_params(bottom=False,
                labelbottom=False)
ax1[1].fill_between(df.index, df.min(), df.max(), where=df > 0,
                    facecolor='red', alpha=0.5)
ax1[1].fill_between(df.index, df.min(), df.max(), where=df <= 0,
                    facecolor='green', alpha=0.5)
ax1[1].title.set_text("Relative Difficulty\n"
                      "Green: Relatively Easier than Density\n"
                      "Red: Relatively Harder than Density")


fig.tight_layout()

plt.show()
#%%
#%%
#%%



plt.figure(figsize=(2,160))
for e, h in enumerate(errors.hit_rep):
    plt.scatter([e] * len(h), h, c='r', marker='x')
for e, h in enumerate(errors.hit_map):
    plt.scatter([e] * len(h), h, c='b', marker='_')
plt.show()
