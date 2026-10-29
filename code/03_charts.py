"""3단계: README에 들어가는 그래프 3개 만들기

  score_vs_satisfaction.png : 서비스 점수별로 전체 비행에 만족한 승객 비율 (3점 -> 4점에서 크게 뜀)
  service_odds_ratio.png    : 서비스별 오즈비와 모델이 예측한 만족률 변화량 (우선순위)
  segment_effect.png        : 구분별(여행 목적, 고객 유형, 좌석 등급) 만족률 변화량

01_analysis.py, 02_service_lift.py 를 먼저 실행해서 output/ 폴더에 or_table.csv, lift.json 이 있어야 합니다.
저장 위치: charts/
"""
import json

import matplotlib
matplotlib.use("Agg")                      # 화면 없이 파일로만 저장
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from common import SERVICE_IMPROVEMENT, load_raw_data
from config import CHARTS, OUTPUT, setup_korean_font

setup_korean_font()

TEAL = "#14B8A6"     # 강조하는 막대
GRAY = "#C5CDD6"     # 나머지 막대
NAVY = "#0E2A47"
RED = "#D9534F"      # 강조 테두리


def draw_red_box(ax, left, bottom, width, height):
    """그래프에서 중요한 부분을 빨간 테두리로 강조"""
    box = Rectangle((left, bottom), width, height, fill=False, edgecolor=RED, linewidth=2.5, clip_on=False, zorder=5)
    ax.add_patch(box)


def save_chart(figure, file_name):
    figure.savefig(CHARTS / file_name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    print("저장:", CHARTS / file_name)


# ------------------------------------------------------------------
# 1. 서비스 점수별 만족 비율 (9개 서비스)
#    "4점 이상을 개선 기준으로 삼는" 근거: 대부분의 서비스에서 3점 -> 4점일 때 만족률이 크게 오른다
# ------------------------------------------------------------------
data = load_raw_data()
is_satisfied = data.satisfaction == "satisfied"

services_to_draw = {
    "온라인 탑승": "Online boarding",
    "기내 와이파이": "Inflight wifi service",
    "좌석 편안함": "Seat comfort",
    "기내 엔터테인먼트": "Inflight entertainment",
    "다리 공간": "Leg room service",
    "수하물 처리": "Baggage handling",
    "기내 서비스": "Inflight service",
    "온라인 예약": "Ease of Online booking",
    "탑승 서비스": "On-board service",
}

figure, axes = plt.subplots(3, 3, figsize=(7.6, 5.0), sharey=True)
for ax, (korean_name, column) in zip(axes.flat, services_to_draw.items()):
    satisfied_rate_by_score = is_satisfied.groupby(data[column]).mean() * 100
    rates = []
    for score in [1, 2, 3, 4, 5]:                       # 0점(해당 없음)은 제외
        rates.append(satisfied_rate_by_score[score])

    ax.bar(range(5), rates, color=[GRAY, GRAY, GRAY, TEAL, TEAL], width=0.7)
    ax.set_xticks(range(5))
    ax.set_xticklabels([1, 2, 3, 4, 5], fontsize=8)
    ax.tick_params(axis="y", labelsize=7)
    ax.set_ylim(0, 118)
    ax.set_title(korean_name, fontsize=9.5, fontweight="bold", pad=3)

    jump = rates[3] - rates[2]                          # 3점 -> 4점 상승폭(%p)
    draw_red_box(ax, 1.55, 0, 1.9, max(rates[2], rates[3]) + 8)
    ax.annotate("", xy=(3, rates[3] + 3), xytext=(2, rates[2] + 3),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.8))
    ax.text(0.0, 98, f"3→4점 +{jump:.0f}%p", fontsize=8.5, color=RED, fontweight="bold")

figure.supxlabel("서비스 평가 점수 (1~5점)", fontsize=9.5, y=0.0)
figure.supylabel("전체 비행 만족 승객 비율 (%)", fontsize=9.5, x=0.0)
figure.tight_layout()
save_chart(figure, "score_vs_satisfaction.png")

# ------------------------------------------------------------------
# 2. 서비스별 오즈비와 만족률 변화량 (우선순위: 변화량이 큰 순서)
# ------------------------------------------------------------------
odds_table = pd.read_csv(OUTPUT / "or_table.csv", index_col=0)
with open(OUTPUT / "lift.json", encoding="utf-8") as file:
    lift_result = json.load(file)

rows = []
for service_name, setting in SERVICE_IMPROVEMENT.items():
    odds_ratio = float(odds_table.loc[setting["good"][0], "OR"])
    lift = lift_result["overall"][service_name]
    rows.append({"service": service_name, "odds_ratio": odds_ratio, "lift": lift})
rank_table = pd.DataFrame(rows).sort_values("lift", ascending=False)

figure, ax = plt.subplots(figsize=(6.6, 4.2))
positions = np.arange(len(rank_table))
colors = [TEAL, TEAL] + [GRAY] * (len(rank_table) - 2)          # 상위 2개만 강조
ax.barh(positions, rank_table.odds_ratio, color=colors, height=0.62)

for position, row in zip(positions, rank_table.itertuples()):
    label = f"{row.odds_ratio:.1f}배  →  +{row.lift:.1f}%p"
    ax.text(row.odds_ratio + 0.12, position, label, va="center", fontsize=10.5, fontweight="bold" if position < 2 else "normal")

ax.axvline(1, color="#6B7785", lw=1, ls="--")                   # 오즈비 1 = 영향 없음
ax.text(1.05, len(rank_table) - 0.4, "1배 = 영향 없음", fontsize=8.5, color="#6B7785", va="bottom")
ax.set_yticks(positions)
ax.set_yticklabels(rank_table.service, fontsize=11)
ax.invert_yaxis()
ax.set_xlim(0, 9.2)
ax.tick_params(axis="x", labelsize=9)
draw_red_box(ax, -2.55, -0.5, 9.2 + 2.55, 2.0)                  # 상위 2개 행 강조
ax.set_xlabel("오즈비: 4점 이상일 때 만족 오즈가 몇 배가 되나\n(→ 뒤는 모델이 예측한 전체 만족률 변화량, 이 순서가 우선순위)", fontsize=9.5)
ax.set_title("로지스틱 회귀 결과: 서비스별 오즈비", fontsize=11, loc="left")
save_chart(figure, "service_odds_ratio.png")

# ------------------------------------------------------------------
# 3. 구분별 만족률 변화량 (와이파이 / 온라인 탑승 / 체크인)
# ------------------------------------------------------------------
segment_groups = [
    ("여행 목적", ["출장", "개인 여행"]),
    ("고객 유형", ["충성", "비충성"]),
    ("좌석 등급", ["이코노미", "이코노미 플러스", "비즈니스석"]),
]
service_names = ["기내 와이파이", "온라인 탑승", "체크인"]
service_colors = [TEAL, NAVY, GRAY]
bar_width = 0.26

figure, axes = plt.subplots(1, 3, figsize=(7.6, 4.5), sharey=True, gridspec_kw={"width_ratios": [2, 2, 3]})
for ax, (group_title, segment_names) in zip(axes, segment_groups):
    x_positions = np.arange(len(segment_names))

    for service_index, service_name in enumerate(service_names):
        values = []
        for segment_name in segment_names:
            values.append(lift_result["seg"][segment_name][service_name])

        offset = (service_index - 1) * bar_width              # 서비스 3개 막대를 나란히 놓기
        legend_label = service_name if group_title == "여행 목적" else None
        ax.bar(x_positions + offset, values, bar_width, color=service_colors[service_index], label=legend_label)

        for x_position, value in zip(x_positions, values):
            text = "약 0" if value < 0.5 else f"{value:.0f}"
            ax.text(x_position + offset, value + 0.7, text, ha="center", fontsize=8)

    labels = []
    for segment_name in segment_names:
        labels.append(segment_name.replace(" 플러스", "\n플러스"))
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_title(group_title, fontsize=11, fontweight="bold")
    ax.set_ylim(0, 38)
    ax.tick_params(axis="y", labelsize=8)

# 강조: 이코노미의 와이파이, 비즈니스석의 온라인 탑승 (좌석 등급 그래프)
seat_ax = axes[2]
draw_red_box(seat_ax, -0.42, 0, 0.32, 33.5)
draw_red_box(seat_ax, 1.84, 0, 0.32, 12.5)
seat_ax.text(-0.26, 35.5, "이코노미: 와이파이", ha="left", fontsize=8.5, color=RED, fontweight="bold")
seat_ax.text(2.0, 14.5, "비즈니스석:\n온라인 탑승", ha="center", fontsize=8.5, color=RED, fontweight="bold")

axes[0].set_ylabel("예측 만족률 변화량 (%p)", fontsize=10)
axes[0].legend(frameon=False, fontsize=9, loc="upper right")
figure.tight_layout()
save_chart(figure, "segment_effect.png")
