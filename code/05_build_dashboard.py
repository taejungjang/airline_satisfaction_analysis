import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from config import *
from pathlib import Path
import pandas as pd, json
T = str(OUTPUT / 'tableau') + '/'
lt = pd.read_csv(T + 'lift_table.csv'); al = pd.read_csv(T + 'service_lift_all.csv'); sm = pd.read_csv(T + 'service_score_summary.csv')
LIFT = [{'g': r['승객군'], 's': r['서비스'], 'base': float(r['기준 만족률(%)']), 'lift': float(r['전원 개선 시 상승폭(%p)'])} for _, r in lt.iterrows()]
ALL = [{'s': r['서비스'], 'lift': float(r['전원 개선 시 상승폭(%p)'])} for _, r in al.iterrows()]
SUM = [[r['여행 목적'], r['고객 유형'], r['좌석 등급'], r['서비스'], int(r['점수']), int(r['승객 수']), int(r['만족 승객 수'])] for _, r in sm.iterrows()]
data = 'var LIFT=%s;\nvar ALL=%s;\nvar SUM=%s;' % (json.dumps(LIFT, ensure_ascii=False), json.dumps(ALL, ensure_ascii=False), json.dumps(SUM, ensure_ascii=False, separators=(',', ':')))
html = open(DASH_TEMPLATE, encoding='utf-8').read().replace('/*__DATA__*/', data)
open(OUTPUT / 'airline_dashboard.html', 'w', encoding='utf-8').write(html)
print(len(html) // 1024, 'KB')
