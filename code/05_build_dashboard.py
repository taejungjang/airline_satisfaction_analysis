"""5단계: 대시보드 HTML(airline_dashboard.html) 만들기

dashboard/dashboard_template.html 의 /*__DATA__*/ 자리에 분석 결과(output/tableau/*.csv)를 끼워 넣습니다.
04_tableau_data.py 를 먼저 실행해야 합니다.
"""
import json

import pandas as pd

from config import DASHBOARD_FILE, DASHBOARD_TEMPLATE, OUTPUT

TABLEAU_DIR = OUTPUT / "tableau"

lift_table = pd.read_csv(TABLEAU_DIR / "lift_table.csv")
lift_ranking = pd.read_csv(TABLEAU_DIR / "service_lift_all.csv")
score_summary = pd.read_csv(TABLEAU_DIR / "service_score_summary.csv")

# 시뮬레이터용: 승객군(g) / 서비스(s) / 현재 만족률(base) / 예측 변화량(lift)
lift_list = []
for _, row in lift_table.iterrows():
    lift_list.append(
        {
            "g": row["승객군"],
            "s": row["서비스"],
            "base": float(row["기준 만족률(%)"]),
            "lift": float(row["전원 개선 시 상승폭(%p)"]),
        }
    )

# 핵심 결과 화면용: 서비스별 변화량 순위
ranking_list = []
for _, row in lift_ranking.iterrows():
    ranking_list.append({"s": row["서비스"], "lift": float(row["전원 개선 시 상승폭(%p)"])})

# 데이터 탐색 화면용: [여행 목적, 고객 유형, 좌석 등급, 서비스, 점수, 승객 수, 만족 승객 수]
summary_list = []
for _, row in score_summary.iterrows():
    summary_list.append(
        [
            row["여행 목적"], row["고객 유형"], row["좌석 등급"], row["서비스"],
            int(row["점수"]), int(row["승객 수"]), int(row["만족 승객 수"]),
        ]
    )

# 템플릿 안에서 쓰는 자바스크립트 변수(LIFT, ALL, SUM)로 만들어 끼워 넣는다
data_script = "var LIFT=%s;\nvar ALL=%s;\nvar SUM=%s;" % (
    json.dumps(lift_list, ensure_ascii=False),
    json.dumps(ranking_list, ensure_ascii=False),
    json.dumps(summary_list, ensure_ascii=False, separators=(",", ":")),
)

template_text = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
html = template_text.replace("/*__DATA__*/", data_script)
DASHBOARD_FILE.write_text(html, encoding="utf-8")
print("저장:", DASHBOARD_FILE, f"({len(html) // 1024} KB)")
