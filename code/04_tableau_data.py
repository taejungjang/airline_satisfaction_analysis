import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from config import *
from pathlib import Path
import runpy, itertools
import pandas as pd, numpy as np, statsmodels.api as sm
g = runpy.run_path(str(Path(__file__).resolve().parent / '01_analysis.py'))
mf, b2, pf = g['mf'], g['b2'], g['pf']
OUT = str(OUTPUT / 'tableau') + '/'

raw = pd.read_csv(TRAIN_CSV, index_col=0).drop(columns='id')
raw['sat'] = (raw.satisfaction == 'satisfied').astype(int)
KO = {'Type of Travel': {'Business travel': '출장', 'Personal Travel': '개인 여행'},
      'Customer Type': {'Loyal Customer': '충성', 'disloyal Customer': '비충성'},
      'Class': {'Business': '비즈니스', 'Eco Plus': '이코노미 플러스', 'Eco': '이코노미'},
      'Gender': {'Male': '남성', 'Female': '여성'}}
SV = {'Inflight wifi service': '기내 와이파이', 'Online boarding': '온라인 탑승', 'Checkin service': '체크인',
      'Leg room service': '다리 공간', 'On-board service': '탑승 서비스', 'Seat comfort': '좌석 편안함',
      'Inflight service': '기내 서비스', 'Baggage handling': '수하물 처리', 'Cleanliness': '청결도',
      'Ease of Online booking': '온라인 예약', 'Food and drink': '음식·음료', 'Gate location': '게이트 위치',
      'Inflight entertainment': '기내 엔터테인먼트', 'Departure/Arrival time convenient': '출·도착 시간 편리'}

# 1) 승객 단위 (한글 라벨)
p = raw.copy()
for c, m in KO.items(): p[c] = p[c].map(m)
p['전체 비행 만족'] = np.where(p.sat == 1, '만족', '중립·불만')
p = p.rename(columns={'Type of Travel': '여행 목적', 'Customer Type': '고객 유형', 'Class': '좌석 등급', 'Gender': '성별',
                      'Age': '나이', 'Flight Distance': '비행 거리', 'Departure Delay in Minutes': '출발 지연(분)',
                      'Arrival Delay in Minutes': '도착 지연(분)', **SV}).drop(columns=['satisfaction', 'sat'])
p.insert(0, '승객ID', range(1, len(p) + 1))
p.to_csv(OUT + 'passengers.csv', index=False, encoding='utf-8-sig')

# 2) 서비스 점수 요약 (EDA용): 여행목적 x 고객유형 x 좌석등급 x 서비스 x 점수
rows = []
for c, k in SV.items():
    t = raw.assign(dim_t=raw['Type of Travel'].map(KO['Type of Travel']), dim_c=raw['Customer Type'].map(KO['Customer Type']),
                   dim_k=raw['Class'].map(KO['Class'])).groupby(['dim_t', 'dim_c', 'dim_k', c]).sat.agg(['count', 'sum']).reset_index()
    t.columns = ['여행 목적', '고객 유형', '좌석 등급', '점수', '승객 수', '만족 승객 수']; t.insert(3, '서비스', k); rows.append(t)
pd.concat(rows).to_csv(OUT + 'service_score_summary.csv', index=False, encoding='utf-8-sig')

# 3) 시뮬레이터용: 서비스 세트별 '전원 4점 이상' 시 만족률 상승폭(%p)
def lift(model, B, flags, zeros=()):
    X = B.copy()
    for c in flags: X[c] = 1.0
    for c in zeros: X[c] = 0.0
    return float(model.predict(X).mean() - model.predict(B).mean()) * 100
F = {'기내 와이파이': (['Inflight wifi service_good'], []), '온라인 탑승': (['Online boarding_good'], []),
     '체크인': (['Checkin service_good'], ['Checkin service_normal']), '다리 공간': (['Leg room service_good'], ['Leg room service_normal'])}
SETS = dict(F)
SETS['와이파이 + 온라인 탑승'] = (F['기내 와이파이'][0] + F['온라인 탑승'][0], [])
SETS['상위 4개 전체'] = tuple(sum((F[k][i] for k in F), []) for i in (0, 1))
out = []
for n, (f, z) in SETS.items():
    out.append({'승객군': '전체', '서비스': n, '기준 만족률(%)': round(raw.sat.mean() * 100, 1), '전원 개선 시 상승폭(%p)': round(lift(mf, b2, f, z), 1)})

# 승객군별 모델 (PPT 10~11번과 동일 방식)
df = raw.drop(columns=['satisfaction']).copy()
df['Arrival Delay in Minutes'] = df['Arrival Delay in Minutes'].fillna(df['Departure Delay in Minutes'])
y = df.pop('sat'); X = df.drop(columns='Arrival Delay in Minutes')
c1 = lambda x: 'bad' if x <= 1 else 'normal' if x <= 3 else 'good'
c2 = lambda x: 'bad_or_normal' if x <= 3 else 'good'
for c in ["Food and drink", "Leg room service", "Checkin service", "Cleanliness"]: X[c] = X[c].apply(c1)
for c in ["Inflight wifi service", "Ease of Online booking", "Online boarding", "Seat comfort", "Inflight entertainment", "On-board service", "Baggage handling", "Inflight service", "Departure/Arrival time convenient"]: X[c] = X[c].apply(c2)
seg = {'출장': df['Type of Travel'] == 'Business travel', '개인 여행': df['Type of Travel'] != 'Business travel',
       '충성': df['Customer Type'] == 'Loyal Customer', '비충성': df['Customer Type'] != 'Loyal Customer'}
for sn, m in seg.items():
    Xs = pd.get_dummies(X[m], drop_first=True).astype(float); Xs = Xs.loc[:, Xs.std() > 0].copy(); Xs.insert(0, 'const', 1.0)
    mod = sm.Logit(y[m], Xs).fit(disp=0, maxiter=200)
    for n, (f, z) in SETS.items():
        out.append({'승객군': sn, '서비스': n, '기준 만족률(%)': round(y[m].mean() * 100, 1),
                    '전원 개선 시 상승폭(%p)': round(max(lift(mod, Xs, [c for c in f if c in Xs], [c for c in z if c in Xs]), 0), 1)})
lt = pd.DataFrame(out); lt.to_csv(OUT + 'lift_table.csv', index=False, encoding='utf-8-sig')
print(lt.to_string()); print(len(p), 'rows passengers')

# 4) 서비스 9개 전체 순위 (전원 개선 가정)
ALL9 = {'기내 와이파이': (['Inflight wifi service_good'], []), '온라인 탑승': (['Online boarding_good'], []),
        '체크인': (['Checkin service_good'], ['Checkin service_normal']), '다리 공간': (['Leg room service_good'], ['Leg room service_normal']),
        '탑승 서비스': (['On-board service_good'], []), '좌석 편안함': (['Seat comfort_good'], []),
        '기내 서비스': (['Inflight service_good'], []), '수하물 처리': (['Baggage handling_good'], []),
        '청결도': (['Cleanliness_good'], ['Cleanliness_normal'])}
al = pd.DataFrame({'서비스': list(ALL9), '전원 개선 시 상승폭(%p)': [round(lift(mf, b2, f, z), 1) for f, z in ALL9.values()]})
al = al.sort_values('전원 개선 시 상승폭(%p)', ascending=False)
al.insert(0, '순위', range(1, len(al) + 1))
al.to_csv(OUT + 'service_lift_all.csv', index=False, encoding='utf-8-sig')
