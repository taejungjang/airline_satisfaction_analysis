# 코드 설명서 (항공 승객 만족도 분석)

이 문서는 **어떤 파일이 무엇을 하는지, 어떤 순서로 실행되는지, 숫자가 어느 코드에서 나오는지** 정리한 문서입니다.

## 1. 한눈에 보는 실행 흐름

```
data/train.csv  (Kaggle 항공 승객 설문 103,904명 x 24항목)
      │
      │  [공통] code/common.py : 읽기 -> 전처리 -> 모델 학습 -> 만족률 변화량 계산 (01, 02, 04가 함께 사용)
      ▼
01_analysis.py ──> output/res.json (모델 성능), output/or_table.csv (오즈비)
02_service_lift.py ──> output/lift.json (서비스별, 구분별 예측 만족률 변화량)
03_charts.py ──> charts/*.png (README 그래프 3개)   <- or_table.csv, lift.json, train.csv 사용
04_tableau_data.py ──> output/tableau/*.csv (대시보드, Tableau용 표 4개)
05_build_dashboard.py ──> airline_dashboard.html (대시보드)  <- output/tableau/*.csv 사용
```

## 2. 실행 방법 (이 순서로)

| 순서 | 명령어 | 하는 일 |
|---|---|---|
| 0 | `pip install -r requirements.txt` | 필요한 라이브러리 설치. Kaggle에서 `train.csv`를 받아 `data/train.csv`에 저장 |
| 1 | `python code/01_analysis.py` | 전처리, 로지스틱 회귀, 성능과 오즈비 저장 |
| 2 | `python code/02_service_lift.py` | 서비스별, 구분별 예측 만족률 변화량 계산 |
| 3 | `python code/03_charts.py` | README 그래프 3개 (1, 2번 실행 후) |
| 4 | `python code/04_tableau_data.py` | 대시보드, Tableau용 CSV |
| 5 | `python code/05_build_dashboard.py` | 대시보드 HTML (4번 실행 후) |

## 3. 파일별 역할

| 파일 | 역할 | 입력 | 출력 |
|---|---|---|---|
| `code/config.py` | 파일 경로, 그래프 한글 글꼴 설정 | | |
| `code/common.py` | 공통 기능: 데이터 읽기, 전처리, 모델 학습, 변화량 계산, 구분별 모델 | `data/train.csv` | (다른 코드에서 불러다 씀) |
| `code/01_analysis.py` | 모델 학습 결과 정리 | common.py | `res.json`, `or_table.csv` |
| `code/02_service_lift.py` | 서비스를 4점 이상으로 올렸을 때 예측 만족률 변화량 | common.py | `lift.json` |
| `code/03_charts.py` | README 그래프 3개 | `train.csv`, `or_table.csv`, `lift.json` | `charts/score_vs_satisfaction.png`, `service_odds_ratio.png`, `segment_effect.png` |
| `code/04_tableau_data.py` | 대시보드, Tableau용 표 4개 | common.py, `train.csv` | `output/tableau/passengers.csv`, `service_score_summary.csv`, `lift_table.csv`, `service_lift_all.csv` |
| `code/05_build_dashboard.py` | 표 3개를 대시보드 HTML에 끼워 넣기 | `output/tableau/*.csv`, `dashboard/dashboard_template.html` | `airline_dashboard.html` |
| `dashboard/dashboard_template.html` | 대시보드 화면 틀. 데이터 자리에 `/*__DATA__*/` | | |

## 4. common.py 안에서 일어나는 일 (모델이 만들어지는 순서)

1. `load_raw_data` : `train.csv` 읽기 (id 열 제거)
2. `fill_missing_arrival_delay` : 도착 지연 빈칸 310건을 출발 지연으로 예측해 채우기 (단순회귀)
3. `clip_flight_distance` : 비행 거리 이상치를 IQR 기준으로 자르기
4. 학습 80% / 검증 20%로 나누기 (`random_state=42`, 만족 비율을 같게 유지)
5. 기본 모델: 서비스 점수를 숫자 그대로 넣은 로지스틱 회귀 (비교용)
6. 최종 모델: 도착 지연 변수를 빼고(출발 지연과 정보가 겹침), 서비스 점수를 단계로 바꿔서 로지스틱 회귀
   - 4개 서비스(음식, 다리 공간, 체크인, 청결도): 0–1점 나쁨 / 2–3점 보통 / 4–5점 좋음
   - 9개 서비스(와이파이 등): 4점 미만 / 4점 이상
   - 게이트 위치: 점수 그대로
7. `satisfaction_lift` : "모든 승객의 해당 서비스를 4점 이상으로 설정했을 때, 모델이 예측한 전체 만족률이 얼마나 오르는가"를 계산 (실제 개선 결과가 아닌 예측값)
8. 구분별(여행 목적, 고객 유형, 좌석 등급) 모델: 구분마다 모델을 따로 학습해서 같은 변화량 계산 (`prepare_segment_data`, `fit_segment_model`)

## 5. README의 주요 숫자는 어디서 나오나

| 숫자 | 의미 | 나오는 곳 |
|---|---|---|
| 103,904명, 43.3% | 승객 수, 전체 비행 만족률 | `res.json` (n, sat_rate) |
| 정확도 89.3%, AUC 0.943 | 최종 모델 성능 (검증 데이터) | `res.json` (fe) |
| 정확도 87.7%, AUC 0.928 | 기본 모델 성능 (4점 기준 적용 전) | `res.json` (base) |
| 오즈비 5.7배, 4.9배 | 와이파이, 온라인 탑승이 4점 이상일 때 만족 오즈 배수 | `or_table.csv` |
| +11.8%p, +8.2%p | 와이파이, 온라인 탑승의 예측 만족률 변화량 | `lift.json` overall, `service_lift_all.csv` |
| 3점 -> 4점 +22–49%p | 점수별 만족률 그래프 | `03_charts.py` (train.csv에서 직접 계산), `service_score_summary.csv` |
| 구분별 변화량 (이코노미 와이파이 +29.6 등) | 여행 목적, 고객 유형, 좌석 등급별 | `lift.json` seg, `lift_table.csv` |
| 비즈니스석의 96%가 출장 | 좌석 등급과 여행 목적의 관계 | `train.csv`에서 직접 확인한 값 (README, 포트폴리오 설명) |

## 6. 읽는 순서 추천

1. `code/config.py` (경로 설정, 짧음)
2. `code/common.py` (모델이 만들어지는 과정. 맨 위 상수 -> 함수 순서로)
3. `code/01_analysis.py` -> `02_service_lift.py` (common.py의 함수를 어떻게 부르는지)
4. `code/03_charts.py` -> `04_tableau_data.py` -> `05_build_dashboard.py`
