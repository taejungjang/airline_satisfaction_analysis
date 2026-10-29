"""1단계: 전처리 -> 로지스틱 회귀 학습 -> 모델 성능과 오즈비 저장

처리 순서 (자세한 내용은 common.py 의 train_models 참고)
  1. 도착 지연 시간 빈칸을 출발 지연 시간으로 예측해 채우기
  2. 비행 거리 이상치를 IQR 기준으로 자르기
  3. 학습 80% / 검증 20%로 나누기
  4. 기본 모델과 최종 모델(서비스 점수를 4점 이상 여부 등으로 바꾼 모델) 학습
  5. 모델 성능(정확도, AUC)과 오즈비 저장

저장하는 파일 (output/ 폴더)
  res.json      : 승객 수, 만족률, 모델 성능
  or_table.csv  : 변수별 오즈비와 95% 신뢰구간, p값
"""
import json

import numpy as np
import pandas as pd

from common import train_models
from config import OUTPUT

# ------------------------------------------------------------------
# 1. 모델 학습
# ------------------------------------------------------------------
results = train_models()
final_model = results["final_model"]

# ------------------------------------------------------------------
# 2. 오즈비 표 만들기
#    오즈비 = 다른 조건이 같을 때, 해당 변수가 1 증가(또는 해당 조건이 참)하면 만족할 오즈가 몇 배가 되는지
#    1이면 영향 없음, 1보다 크면 만족 쪽, 작으면 불만 쪽
# ------------------------------------------------------------------
confidence_interval = final_model.conf_int()           # 계수의 95% 신뢰구간
odds_table = pd.DataFrame(
    {
        "OR": np.exp(final_model.params),               # 오즈비
        "lo": np.exp(confidence_interval[0]),           # 신뢰구간 아래쪽
        "hi": np.exp(confidence_interval[1]),           # 신뢰구간 위쪽
        "p": final_model.pvalues,                       # p값
    }
)
odds_table = odds_table.drop(index="const")             # 상수항은 오즈비로 해석하지 않는다
odds_table.to_csv(OUTPUT / "or_table.csv", encoding="utf-8-sig")
print(odds_table.sort_values("OR", ascending=False).round(2).to_string())

# ------------------------------------------------------------------
# 3. 모델 성능 저장
# ------------------------------------------------------------------
summary = {
    "n": results["n_passengers"],
    "sat_rate": results["satisfaction_rate"],
    "na_n": results["n_filled_arrival_delay"],
    "base": results["base_performance"],        # 기본 모델 (정확도, AUC)
    "fe": results["final_performance"],         # 최종 모델 (정확도, AUC)
    "pred_base": results["predicted_satisfaction_rate"],
}
print(summary)
with open(OUTPUT / "res.json", "w", encoding="utf-8") as file:
    json.dump(summary, file, ensure_ascii=False, indent=1, default=float)
