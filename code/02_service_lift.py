import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from config import *
from pathlib import Path
import runpy, json
import pandas as pd, numpy as np, statsmodels.api as sm
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
g = runpy.run_path(str(Path(__file__).resolve().parent / '01_analysis.py'))
mf, b2, pf = g['mf'], g['b2'], g['pf']
OUT = g['OUT']; NUM = g['NUM']
BL = '#1F3A5F'; OR = '#E07B39'; GR = '#9AA5B1'

def lift(model, B, flag_cols, zero_cols=()):
    X = B.copy()
    for c in flag_cols: X[c] = 1.0
    for c in zero_cols: X[c] = 0.0
    return float(model.predict(X).mean() - model.predict(B).mean())

items = {
 '기내 와이파이': (['Inflight wifi service_good'], []),
 '온라인 탑승': (['Online boarding_good'], []),
 '체크인': (['Checkin service_good'], ['Checkin service_normal']),
 '다리 공간': (['Leg room service_good'], ['Leg room service_normal']),
 '탑승 서비스': (['On-board service_good'], []),
 '좌석 편안함': (['Seat comfort_good'], []),
 '기내 서비스': (['Inflight service_good'], []),
 '수하물 처리': (['Baggage handling_good'], []),
 '청결도': (['Cleanliness_good'], ['Cleanliness_normal']),
}
res = {k: lift(mf, b2, f, z) * 100 for k, (f, z) in items.items()}
print({k: round(v, 1) for k, v in res.items()})
print('baseline', pf.mean())
ser = pd.Series(res).sort_values()
fig, ax = plt.subplots(figsize=(8.6, 5))
ax.barh(ser.index, ser.values, color=[OR if v >= 4 else GR for v in ser.values], height=.62)
for i, v in enumerate(ser.values): ax.text(v + .2, i, f'+{v:.1f}%p', va='center', fontsize=12, fontweight='bold')
ax.set_xlim(0, ser.max() + 3); ax.set_xlabel('전체 비행 만족률 상승폭 (%p)'); ax.tick_params(axis='y', labelsize=12)
for s in ['top', 'right']: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(OUT + 'lift.png', dpi=200); plt.close()

# segment models (same feature engineering, fit per segment on full data)
df = pd.read_csv(TRAIN_CSV, index_col=0).drop(columns='id')
df['Arrival Delay in Minutes'] = df['Arrival Delay in Minutes'].fillna(df['Departure Delay in Minutes'])
y = (df.satisfaction == 'satisfied').astype(int)
X = df.drop(columns=['satisfaction', 'Arrival Delay in Minutes'])
c1 = lambda x: 'bad' if x <= 1 else 'normal' if x <= 3 else 'good'
c2 = lambda x: 'bad_or_normal' if x <= 3 else 'good'
for c in ["Food and drink", "Leg room service", "Checkin service", "Cleanliness"]: X[c] = X[c].apply(c1)
for c in ["Inflight wifi service", "Ease of Online booking", "Online boarding", "Seat comfort", "Inflight entertainment", "On-board service", "Baggage handling", "Inflight service", "Departure/Arrival time convenient"]: X[c] = X[c].apply(c2)
seg = {'출장': df['Type of Travel'] == 'Business travel', '개인 여행': df['Type of Travel'] != 'Business travel',
       '충성': df['Customer Type'] == 'Loyal Customer', '비충성': df['Customer Type'] != 'Loyal Customer'}
out = {}
for n, m in seg.items():
    Xs = pd.get_dummies(X[m], drop_first=True); Xs = sm.add_constant(Xs).astype(float)
    Xs = Xs.loc[:, Xs.std() > 0].copy(); Xs.insert(0, 'const', 1.0)
    mod = sm.Logit(y[m], Xs).fit(disp=0, maxiter=200)
    out[n] = {k: lift(mod, Xs, [c for c in f if c in Xs], [c for c in z if c in Xs]) * 100 for k, (f, z) in list(items.items())[:3]}
    out[n]['base'] = float(y[m].mean() * 100)
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump({'overall': res, 'seg': out, 'base': float(pf.mean() * 100)}, open(NUM + 'lift.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
