import sys, importlib

from matplotlib import pyplot as plt

from osrparse import parse_replay_file, ReplayEvent
from osrparse.mania import ManiaHitError
from reamber.osu.OsuMap import OsuMap
import numpy as np
import pandas as pd
#%%
rep = parse_replay_file("rsc/luminal0.osr")
map = OsuMap.readFile("rsc/luminal.osu")

er = ManiaHitError(rep, map)
errors = er.errors()
hit_error = errors.hit_error
rel_error = errors.rel_error

all_error = [*[e for k in errors.hit_error for e in k],
             *[e for k in errors.rel_error for e in k]]
all_map = [*[e for k in errors.hit_map for e in k],
           *[e for k in errors.rel_map for e in k]]
#%%
INTERVAL = 4
#%%
ar_map = np.asarray(all_map)

df_map = pd.DataFrame(np.ones_like(ar_map), index=ar_map)
df_map = df_map.sort_index()
df_map.index = pd.to_datetime(df_map.index, unit='ms')

df_map_roll = df_map.groupby(pd.Grouper(freq=f'{INTERVAL}s')).sum() / INTERVAL
#%%
ar_error = np.asarray([all_error, all_map], dtype=int)

df_error = pd.DataFrame(np.abs(ar_error[0]), index=ar_error[1])
df_error = df_error.sort_index()
df_error.index = pd.to_datetime(df_error.index, unit='ms')

df_error_roll = df_error.groupby(pd.Grouper(freq=f'{INTERVAL}s')).sum() / INTERVAL
#%%
plt.style.use('dark_background')
fig, ax1 = plt.subplots(figsize=(10,3))

ax1.plot(df_error_roll, c='red', label='Sum(Error) / s', linewidth=1.2)
ax1.set_xlabel('Time', c='red')
ax1.set_ylabel('Sum(Error) / s')
ax1.tick_params(axis='y', labelcolor='red')
ax1.grid(False)
ax2 = ax1.twinx()
ax2.plot(df_map_roll, label='Density / s', linewidth=1)
ax2.set_ylabel('Density / s')
ax2.tick_params(axis='y')
ax2.grid(False)
fig.legend(loc='lower right')

ax1.tick_params(bottom=False,
                labelbottom=False)
ax1.title.set_text("Evening - Luminal Dan (Hit Error & Density)")
fig.tight_layout()

plt.show()


#%%
errors.hit_map


#%%



plt.figure(figsize=(2,160))
for e, h in enumerate(errors.hit_rep):
    plt.scatter([e] * len(h), h, c='r', marker='x')
for e, h in enumerate(errors.hit_map):
    plt.scatter([e] * len(h), h, c='b', marker='_')
plt.show()
