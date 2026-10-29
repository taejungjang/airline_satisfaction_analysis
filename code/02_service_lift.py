"""2단계: 서비스를 '모든 승객 4점 이상'으로 설정했을 때 모델이 예측한 만족률 변화량 계산

  A. 전체 승객: 서비스 9개 각각의 변화량(%p)  -> 우선순위를 정하는 기준
  B. 구분별(여행 목적, 고객 유형, 좌석 등급): 와이파이, 온라인 탑승, 체크인의 변화량

저장하는 파일 (output/ 폴더)
  lift.json : {"overall": 서비스별 변화량, "seg": 구분별 변화량과 현재 만족률, "base": 모델이 예측한 현재 만족률}
"""
import json

from common import (
    SERVICE_IMPROVEMENT,
    fit_segment_model,
    keep_existing_columns,
    prepare_segment_data,
    satisfaction_lift,
    segment_masks,
    train_models,
)
from config import OUTPUT

# ------------------------------------------------------------------
# A. 전체 승객 기준 서비스별 변화량 (최종 모델 + 검증 데이터)
# ------------------------------------------------------------------
results = train_models()
final_model = results["final_model"]
valid_matrix = results["valid_matrix"]

overall_lift = {}
for service_name, setting in SERVICE_IMPROVEMENT.items():
    lift = satisfaction_lift(final_model, valid_matrix, setting["good"], setting["reset"])
    overall_lift[service_name] = lift * 100          # 비율을 %p 로 바꾼다
print({name: round(value, 1) for name, value in overall_lift.items()})

# ------------------------------------------------------------------
# B. 구분별 변화량: 구분마다 모델을 따로 학습해서 계산
#    (구분별 모델은 전체 데이터로 학습하고, 비행 거리 이상치 보정은 하지 않는다)
# ------------------------------------------------------------------
data, features, satisfied = prepare_segment_data()
masks = segment_masks(data)

services_to_check = ["기내 와이파이", "온라인 탑승", "체크인"]
segment_lift = {}
for segment_name, mask in masks.items():
    model, matrix = fit_segment_model(features, satisfied, mask)

    segment_lift[segment_name] = {}
    for service_name in services_to_check:
        setting = SERVICE_IMPROVEMENT[service_name]
        good_columns = keep_existing_columns(setting["good"], matrix)
        reset_columns = keep_existing_columns(setting["reset"], matrix)
        lift = satisfaction_lift(model, matrix, good_columns, reset_columns)
        segment_lift[segment_name][service_name] = lift * 100

    segment_lift[segment_name]["base"] = float(satisfied[mask].mean() * 100)   # 이 구분의 현재 만족률
print(json.dumps(segment_lift, ensure_ascii=False, indent=1))

# ------------------------------------------------------------------
# 저장
# ------------------------------------------------------------------
output = {
    "overall": overall_lift,
    "seg": segment_lift,
    "base": results["predicted_satisfaction_rate"] * 100,
}
with open(OUTPUT / "lift.json", "w", encoding="utf-8") as file:
    json.dump(output, file, ensure_ascii=False, indent=1)
