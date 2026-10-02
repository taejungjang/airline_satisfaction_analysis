import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from config import *
from pathlib import Path
import json, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
setup_font()
OUT = str(CHARTS) + '/'; NUM = str(OUTPUT) + '/'
r = json.load(open(NUM + 'lift.json', encoding='utf-8'))['seg']
names = ['기내 와이파이', '온라인 탑승', '체크인']
a = [max(r['출장'][n], 0) for n in names]; b = [max(r['개인 여행'][n], 0) for n in names]
x = np.arange(3); w = .36
fig, ax = plt.subplots(figsize=(8.4, 4.8))
ax.bar(x - w / 2, a, w, color='#1F3A5F', label='출장 고객'); ax.bar(x + w / 2, b, w, color='#E07B39', label='개인 여행 고객')
for i in range(3):
    ax.text(i - w / 2, a[i] + .8, f'+{a[i]:.0f}%p', ha='center', fontweight='bold', fontsize=14)
    ax.text(i + w / 2, b[i] + .8, f'+{b[i]:.0f}%p' if b[i] >= 0.5 else '0%p', ha='center', fontweight='bold', fontsize=14)
ax.set_xticks(x); ax.set_xticklabels(names, fontsize=14); ax.set_ylim(0, 36); ax.set_ylabel('전체 비행 만족률 상승폭 (%p)')
ax.legend(frameon=False, fontsize=13, loc='upper right')
for s in ['top', 'right']: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(OUT + 'seg_effect.png', dpi=200)
