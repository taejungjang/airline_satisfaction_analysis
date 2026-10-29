"""4단계: 대시보드와 Tableau에 쓸 데이터 파일 만들기

저장하는 파일 (output/tableau/ 폴더)
  passengers.csv            : 승객 한 명당 한 줄 (한글 열 이름) - Tableau 에서 바로 사용
  service_score_summary.csv : 서비스 점수별 만족 승객 수 (데이터 탐색 화면용)
  lift_table.csv            : 승객군별, 서비스(조합)별 예측 만족률 변화량 (시뮬레이터용)
  service_lift_all.csv      : 서비스 9개의 예측 만족률 변화량 순위 (핵심 결과 화면용)
"""
import numpy as np
import pandas as pd

from common import (
    SERVICE_IMPROVEMENT,
    fit_segment_model,
    keep_existing_columns,
    load_raw_data,
    prepare_segment_data,
    satisfaction_lift,
    segment_masks,
    train_models,
)
from config import OUTPUT

TABLEAU_DIR = OUTPUT / "tableau"

# 영어 값 -> 한글 값
KOREAN_VALUES = {
    "Type of Travel": {"Business travel": "출장", "Personal Travel": "개인 여행"},
    "Customer Type": {"Loyal Customer": "충성", "disloyal Customer": "비충성"},
    "Class": {"Business": "비즈니스", "Eco Plus": "이코노미 플러스", "Eco": "이코노미"},
    "Gender": {"Male": "남성", "Female": "여성"},
}

# 서비스 열 이름 영어 -> 한글
KOREAN_SERVICE_NAMES = {
    "Inflight wifi service": "기내 와이파이",
    "Online boarding": "온라인 탑승",
    "Checkin service": "체크인",
    "Leg room service": "다리 공간",
    "On-board service": "탑승 서비스",
    "Seat comfort": "좌석 편안함",
    "Inflight service": "기내 서비스",
    "Baggage handling": "수하물 처리",
    "Cleanliness": "청결도",
    "Ease of Online booking": "온라인 예약",
    "Food and drink": "음식·음료",
    "Gate location": "게이트 위치",
    "Inflight entertainment": "기내 엔터테인먼트",
    "Departure/Arrival time convenient": "출·도착 시간 편리",
}

raw = load_raw_data()
raw["sat"] = (raw.satisfaction == "satisfied").astype(int)    # 만족 = 1

# ------------------------------------------------------------------
# 1. 승객 단위 파일 (한글 열 이름과 값)
# ------------------------------------------------------------------
passengers = raw.copy()
for column, translation in KOREAN_VALUES.items():
    passengers[column] = passengers[column].map(translation)
passengers["전체 비행 만족"] = np.where(passengers.sat == 1, "만족", "중립·불만")

column_names = {
    "Type of Travel": "여행 목적",
    "Customer Type": "고객 유형",
    "Class": "좌석 등급",
    "Gender": "성별",
    "Age": "나이",
    "Flight Distance": "비행 거리",
    "Departure Delay in Minutes": "출발 지연(분)",
    "Arrival Delay in Minutes": "도착 지연(분)",
}
column_names.update(KOREAN_SERVICE_NAMES)
passengers = passengers.rename(columns=column_names)
passengers = passengers.drop(columns=["satisfaction", "sat"])
passengers.insert(0, "승객ID", range(1, len(passengers) + 1))
passengers.to_csv(TABLEAU_DIR / "passengers.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------
# 2. 서비스 점수 요약: 여행 목적 x 고객 유형 x 좌석 등급 x 서비스 x 점수별 승객 수와 만족 승객 수
# ------------------------------------------------------------------
raw["travel_ko"] = raw["Type of Travel"].map(KOREAN_VALUES["Type of Travel"])
raw["customer_ko"] = raw["Customer Type"].map(KOREAN_VALUES["Customer Type"])
raw["class_ko"] = raw["Class"].map(KOREAN_VALUES["Class"])

summary_tables = []
for english_name, korean_name in KOREAN_SERVICE_NAMES.items():
    counts = raw.groupby(["travel_ko", "customer_ko", "class_ko", english_name]).sat.agg(["count", "sum"]).reset_index()
    counts.columns = ["여행 목적", "고객 유형", "좌석 등급", "점수", "승객 수", "만족 승객 수"]
    counts.insert(3, "서비스", korean_name)
    summary_tables.append(counts)
pd.concat(summary_tables).to_csv(TABLEAU_DIR / "service_score_summary.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------
# 3. 시뮬레이터용 표: '서비스(조합)를 모든 승객 4점 이상으로 설정'했을 때 예측 만족률 변화량(%p)
# ------------------------------------------------------------------
# 서비스 4개와, 그 조합 2개를 비교한다
simulation_sets = {}
for service_name in ["기내 와이파이", "온라인 탑승", "체크인", "다리 공간"]:
    simulation_sets[service_name] = SERVICE_IMPROVEMENT[service_name]

wifi = SERVICE_IMPROVEMENT["기내 와이파이"]
boarding = SERVICE_IMPROVEMENT["온라인 탑승"]
simulation_sets["와이파이 + 온라인 탑승"] = {"good": wifi["good"] + boarding["good"], "reset": []}

top4_good = []
top4_reset = []
for service_name in ["기내 와이파이", "온라인 탑승", "체크인", "다리 공간"]:
    top4_good = top4_good + SERVICE_IMPROVEMENT[service_name]["good"]
    top4_reset = top4_reset + SERVICE_IMPROVEMENT[service_name]["reset"]
simulation_sets["상위 4개 전체"] = {"good": top4_good, "reset": top4_reset}

lift_rows = []

# (1) 전체 승객: 최종 모델 + 검증 데이터
results = train_models()
final_model = results["final_model"]
valid_matrix = results["valid_matrix"]
overall_satisfaction_pct = round(raw.sat.mean() * 100, 1)

for set_name, setting in simulation_sets.items():
    lift = satisfaction_lift(final_model, valid_matrix, setting["good"], setting["reset"]) * 100
    lift_rows.append(
        {
            "승객군": "전체",
            "서비스": set_name,
            "기준 만족률(%)": overall_satisfaction_pct,
            "전원 개선 시 상승폭(%p)": round(lift, 1),
        }
    )

# (2) 승객군별: 승객군마다 모델을 따로 학습 (여행 목적, 고객 유형)
segment_data, features, satisfied = prepare_segment_data()
all_masks = segment_masks(segment_data)

for segment_name in ["출장", "개인 여행", "충성", "비충성"]:
    mask = all_masks[segment_name]
    model, matrix = fit_segment_model(features, satisfied, mask)
    segment_satisfaction_pct = round(satisfied[mask].mean() * 100, 1)

    for set_name, setting in simulation_sets.items():
        good_columns = keep_existing_columns(setting["good"], matrix)
        reset_columns = keep_existing_columns(setting["reset"], matrix)
        lift = satisfaction_lift(model, matrix, good_columns, reset_columns) * 100
        lift = max(lift, 0)                       # 음수로 나오면 0으로 표시 ('변화 없음')
        lift_rows.append(
            {
                "승객군": segment_name,
                "서비스": set_name,
                "기준 만족률(%)": segment_satisfaction_pct,
                "전원 개선 시 상승폭(%p)": round(lift, 1),
            }
        )

lift_table = pd.DataFrame(lift_rows)
lift_table.to_csv(TABLEAU_DIR / "lift_table.csv", index=False, encoding="utf-8-sig")
print(lift_table.to_string())

# ------------------------------------------------------------------
# 4. 서비스 9개의 예측 만족률 변화량 순위 (전체 승객 기준)
# ------------------------------------------------------------------
service_names = []
service_lifts = []
for service_name, setting in SERVICE_IMPROVEMENT.items():
    lift = satisfaction_lift(final_model, valid_matrix, setting["good"], setting["reset"]) * 100
    service_names.append(service_name)
    service_lifts.append(round(lift, 1))

lift_ranking = pd.DataFrame({"서비스": service_names, "전원 개선 시 상승폭(%p)": service_lifts})
lift_ranking = lift_ranking.sort_values("전원 개선 시 상승폭(%p)", ascending=False, kind="stable")
lift_ranking.insert(0, "순위", range(1, len(lift_ranking) + 1))
lift_ranking.to_csv(TABLEAU_DIR / "service_lift_all.csv", index=False, encoding="utf-8-sig")
