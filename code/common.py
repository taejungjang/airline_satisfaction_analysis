"""공통 기능: 데이터 읽기 -> 전처리 -> 로지스틱 회귀 학습 -> 만족률 변화량 계산

01_analysis.py, 02_service_lift.py, 04_tableau_data.py 가 같은 방식으로 모델을 만들기 때문에
이 파일에 모아 두었습니다. (직접 실행하는 파일이 아니라 다른 코드에서 불러다 씁니다.)
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

from config import TRAIN_CSV

# ------------------------------------------------------------------
# 서비스 평가 항목 (각 항목은 0~5점, 0은 '해당 없음')
# ------------------------------------------------------------------
SERVICE_COLUMNS = [
    "Inflight wifi service", "Ease of Online booking", "Online boarding", "Seat comfort",
    "Inflight entertainment", "On-board service", "Leg room service", "Baggage handling",
    "Checkin service", "Inflight service", "Cleanliness", "Food and drink",
    "Gate location", "Departure/Arrival time convenient",
]

# 점수를 3단계(나쁨 / 보통 / 좋음)로 바꾸는 서비스: 0~1점 나쁨, 2~3점 보통, 4~5점 좋음
THREE_LEVEL_SERVICES = ["Food and drink", "Leg room service", "Checkin service", "Cleanliness"]

# 점수를 2단계(4점 미만 / 4점 이상)로 바꾸는 서비스: 0~3점 4점 미만, 4~5점 4점 이상
TWO_LEVEL_SERVICES = [
    "Inflight wifi service", "Ease of Online booking", "Online boarding", "Seat comfort",
    "Inflight entertainment", "On-board service", "Baggage handling", "Inflight service",
    "Departure/Arrival time convenient",
]
# (Gate location 은 점수를 그대로 사용)

# 서비스를 '4점 이상으로 개선'했을 때 모델 입력값을 어떻게 바꿀지
#   good  : 값을 1로 만들 열 (4점 이상 여부)
#   reset : 값을 0으로 되돌릴 열 (3단계 서비스는 '보통' 열도 0으로 만들어 '좋음'만 남김)
SERVICE_IMPROVEMENT = {
    "기내 와이파이": {"good": ["Inflight wifi service_good"], "reset": []},
    "온라인 탑승": {"good": ["Online boarding_good"], "reset": []},
    "체크인": {"good": ["Checkin service_good"], "reset": ["Checkin service_normal"]},
    "다리 공간": {"good": ["Leg room service_good"], "reset": ["Leg room service_normal"]},
    "탑승 서비스": {"good": ["On-board service_good"], "reset": []},
    "좌석 편안함": {"good": ["Seat comfort_good"], "reset": []},
    "기내 서비스": {"good": ["Inflight service_good"], "reset": []},
    "수하물 처리": {"good": ["Baggage handling_good"], "reset": []},
    "청결도": {"good": ["Cleanliness_good"], "reset": ["Cleanliness_normal"]},
}


# ------------------------------------------------------------------
# 점수 -> 단계 변환
# ------------------------------------------------------------------
def to_three_level(score):
    """0~1점 -> bad, 2~3점 -> normal, 4~5점 -> good"""
    if score <= 1:
        return "bad"
    if score <= 3:
        return "normal"
    return "good"


def to_two_level(score):
    """0~3점 -> bad_or_normal(4점 미만), 4~5점 -> good(4점 이상)"""
    if score <= 3:
        return "bad_or_normal"
    return "good"


def convert_service_scores(features):
    """서비스 점수 열을 3단계 / 2단계 글자로 바꾼 복사본을 돌려준다"""
    converted = features.copy()
    for column in THREE_LEVEL_SERVICES:
        converted[column] = converted[column].apply(to_three_level)
    for column in TWO_LEVEL_SERVICES:
        converted[column] = converted[column].apply(to_two_level)
    return converted


# ------------------------------------------------------------------
# 데이터 읽기와 전처리
# ------------------------------------------------------------------
def load_raw_data():
    """train.csv 를 읽는다 (첫 열은 번호, id 열은 필요 없어 제거)"""
    data = pd.read_csv(TRAIN_CSV, index_col=0)
    return data.drop(columns="id")


def fill_missing_arrival_delay(data):
    """도착 지연 시간 빈칸을 '출발 지연 시간으로 예측한 값'으로 채운다 (단순회귀)

    돌려주는 값: (채운 데이터, 채운 개수)
    """
    data = data.copy()
    has_value = data.dropna(subset=["Arrival Delay in Minutes"])
    regression = sm.OLS(
        has_value["Arrival Delay in Minutes"],
        sm.add_constant(has_value[["Departure Delay in Minutes"]]),
    ).fit()

    is_missing = data["Arrival Delay in Minutes"].isna()
    missing_rows = sm.add_constant(data.loc[is_missing, ["Departure Delay in Minutes"]], has_constant="add")
    data.loc[is_missing, "Arrival Delay in Minutes"] = regression.predict(missing_rows)
    return data, int(is_missing.sum())


def clip_flight_distance(data):
    """비행 거리의 이상치를 IQR 기준(1사분위 - 1.5 x IQR ~ 3사분위 + 1.5 x IQR)으로 잘라낸다"""
    data = data.copy()
    q1 = data["Flight Distance"].quantile(0.25)
    q3 = data["Flight Distance"].quantile(0.75)
    iqr = q3 - q1
    data["Flight Distance"] = data["Flight Distance"].clip(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    return data


def make_model_matrix(train_features, valid_features):
    """글자 열을 0/1 열로 바꾸고(더미 변수), 상수항을 붙여 모델에 넣을 표를 만든다.

    학습 데이터에 없는 열은 검증 데이터에서도 맞추고, 빈 곳은 0으로 채운다.
    """
    train_dummies = pd.get_dummies(train_features, drop_first=True)
    valid_dummies = pd.get_dummies(valid_features, drop_first=True)
    train_dummies, valid_dummies = train_dummies.align(valid_dummies, join="left", axis=1, fill_value=0)
    train_matrix = sm.add_constant(train_dummies).astype(float)
    valid_matrix = sm.add_constant(valid_dummies).astype(float)
    return train_matrix, valid_matrix


# ------------------------------------------------------------------
# 모델 학습 (학습 80% / 검증 20%)
# ------------------------------------------------------------------
def train_models():
    """기본 모델과 최종 모델(서비스 점수를 단계로 바꾼 모델)을 학습하고 결과를 사전으로 돌려준다"""
    data = load_raw_data()
    n_passengers = len(data)
    satisfaction_rate = float((data.satisfaction == "satisfied").mean())

    data, n_filled = fill_missing_arrival_delay(data)
    data = clip_flight_distance(data)

    features = data.drop(columns="satisfaction")
    target = (data.satisfaction == "satisfied").astype(int)   # 만족 = 1, 중립·불만 = 0
    train_x, valid_x, train_y, valid_y = train_test_split(
        features, target, test_size=0.2, random_state=42, stratify=target
    )

    # (1) 기본 모델: 서비스 점수를 숫자 그대로 사용
    train_matrix, valid_matrix = make_model_matrix(train_x, valid_x)
    base_model = sm.Logit(train_y, train_matrix).fit(disp=0)
    base_probability = base_model.predict(valid_matrix)
    base_accuracy = accuracy_score(valid_y, base_probability >= 0.5)
    base_auc = roc_auc_score(valid_y, base_probability)

    # (2) 최종 모델: 도착 지연 변수를 빼고(출발 지연과 정보가 겹침), 서비스 점수를 단계로 바꿔서 사용
    train_x = train_x.drop(columns="Arrival Delay in Minutes")
    valid_x = valid_x.drop(columns="Arrival Delay in Minutes")
    train_x = convert_service_scores(train_x)
    valid_x = convert_service_scores(valid_x)
    train_matrix, valid_matrix = make_model_matrix(train_x, valid_x)
    final_model = sm.Logit(train_y, train_matrix).fit(disp=0)
    final_probability = final_model.predict(valid_matrix)
    final_accuracy = accuracy_score(valid_y, final_probability >= 0.5)
    final_auc = roc_auc_score(valid_y, final_probability)

    return {
        "n_passengers": n_passengers,
        "satisfaction_rate": satisfaction_rate,
        "n_filled_arrival_delay": n_filled,
        "base_performance": (base_accuracy, base_auc),
        "final_performance": (final_accuracy, final_auc),
        "final_model": final_model,
        "valid_matrix": valid_matrix,                          # 검증 데이터를 모델 입력 형태로 바꾼 표
        "predicted_satisfaction_rate": float(final_probability.mean()),
    }


# ------------------------------------------------------------------
# 만족률 변화량 계산
# ------------------------------------------------------------------
def satisfaction_lift(model, matrix, good_columns, reset_columns=()):
    """서비스를 '모든 승객 4점 이상'으로 설정했을 때, 모델이 예측한 전체 만족률 변화량 (0~1 비율)

    좋음 열을 1로, 되돌릴 열을 0으로 바꾼 표로 예측한 평균 만족률에서
    원래 표로 예측한 평균 만족률을 뺀다. (실제 개선 결과가 아니라 모델 예측값)
    """
    improved = matrix.copy()
    for column in good_columns:
        improved[column] = 1.0
    for column in reset_columns:
        improved[column] = 0.0
    return float(model.predict(improved).mean() - model.predict(matrix).mean())


# ------------------------------------------------------------------
# 구분별(여행 목적, 고객 유형, 좌석 등급) 모델
# ------------------------------------------------------------------
def segment_masks(data):
    """구분별로 해당 승객이면 True 인 표시 열(마스크)을 만든다"""
    return {
        "출장": data["Type of Travel"] == "Business travel",
        "개인 여행": data["Type of Travel"] != "Business travel",
        "충성": data["Customer Type"] == "Loyal Customer",
        "비충성": data["Customer Type"] != "Loyal Customer",
        "이코노미": data["Class"] == "Eco",
        "이코노미 플러스": data["Class"] == "Eco Plus",
        "비즈니스석": data["Class"] == "Business",
    }


def prepare_segment_data():
    """구분별 모델용 데이터를 준비한다.

    전체 데이터로 구분별 모델을 따로 학습하므로 학습/검증으로 나누지 않고,
    최종 모델과 같은 방식으로 서비스 점수를 단계로 바꾼다. (비행 거리 이상치 보정은 하지 않음)
    돌려주는 값: (원본 데이터, 모델 입력 변수 표, 만족 여부 0/1)
    """
    data = load_raw_data()
    satisfied = (data.satisfaction == "satisfied").astype(int)
    features = data.drop(columns=["satisfaction", "Arrival Delay in Minutes"])
    features = convert_service_scores(features)
    return data, features, satisfied


def fit_segment_model(features, satisfied, mask):
    """mask 에 해당하는 승객만으로 로지스틱 회귀를 학습한다. 돌려주는 값: (모델, 모델 입력 표)"""
    matrix = pd.get_dummies(features[mask], drop_first=True).astype(float)
    matrix = matrix.loc[:, matrix.std() > 0].copy()     # 값이 모두 같은 열은 뺀다
    matrix.insert(0, "const", 1.0)                      # 상수항을 맨 앞에 붙인다
    model = sm.Logit(satisfied[mask], matrix).fit(disp=0, maxiter=200)
    return model, matrix


def keep_existing_columns(column_names, matrix):
    """구분별 모델에는 없는 열이 있을 수 있어서, 표에 있는 열만 남긴다"""
    existing = []
    for column in column_names:
        if column in matrix:
            existing.append(column)
    return existing
