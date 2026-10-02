import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from config import *
from pathlib import Path
import pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
setup_font()
OUT = str(CHARTS) + '/'; NUM = str(OUTPUT) + '/'
BL = '#1F3A5F'; OR = '#E07B39'; GR = '#9AA5B1'
df = pd.read_csv(TRAIN_CSV, index_col=0)
sat = df.satisfaction == 'satisfied'

# 승객 유형별
spec = [('Type of Travel', '여행 목적', {'Personal Travel': '개인 여행', 'Business travel': '출장'}, ['개인 여행', '출장']),
        ('Customer Type', '고객 유형', {'disloyal Customer': '비충성', 'Loyal Customer': '충성'}, ['비충성', '충성']),
        ('Class', '좌석 등급', {'Eco': '이코노미', 'Eco Plus': '이코노미 플러스', 'Business': '비즈니스'}, ['이코노미', '이코노미 플러스', '비즈니스'])]
fig, axs = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True, gridspec_kw={'width_ratios': [2, 2, 3]})
for ax, (col, title, mp, order) in zip(axs, spec):
    g = (sat.groupby(df[col].map(mp)).mean() * 100).reindex(order)
    ax.bar(order, g.values, color=BL, width=.62)
    for i, v in enumerate(g.values): ax.text(i, v + 1.5, f'{v:.0f}%', ha='center', fontweight='bold', fontsize=14)
    ax.set_title(title, fontsize=15, fontweight='bold'); ax.set_ylim(0, 100); ax.tick_params(axis='x', labelsize=12)
    for s in ['top', 'right']: ax.spines[s].set_visible(False)
axs[0].set_ylabel('전체 비행 만족률 (%)', fontsize=12)
plt.tight_layout(); plt.savefig(OUT + 'segments.png', dpi=200); plt.close()

# 와이파이 점수별
g = sat[df['Inflight wifi service'] > 0].groupby(df['Inflight wifi service']).mean() * 100
fig, ax = plt.subplots(figsize=(6.2, 3.9))
ax.bar(g.index.astype(str), g.values, color=[GR] * 3 + [OR] * 2)
for i, v in enumerate(g.values): ax.text(i, v + 1.5, f'{v:.0f}%', ha='center', fontweight='bold', fontsize=13)
ax.set_xlabel('와이파이 평가 점수 (개별 서비스)', fontsize=12); ax.set_ylabel('전체 비행에 만족한 승객 비율 (%)', fontsize=11); ax.set_ylim(0, 105)
for s in ['top', 'right']: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(OUT + 'wifi.png', dpi=200); plt.close()
