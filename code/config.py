"""공통 설정: 파일 경로와 그래프 한글 글꼴. 다른 코드에서 불러다 씁니다."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Kaggle 'Airline Passenger Satisfaction' 의 train.csv (저장소에는 포함하지 않음)
# 다른 위치에 두었다면 환경변수 AIRLINE_TRAIN_CSV 로 경로를 알려 주면 됨
TRAIN_CSV = Path(os.environ.get("AIRLINE_TRAIN_CSV", ROOT / "data" / "train.csv"))

CHARTS = ROOT / "charts"                                  # 그래프 이미지 (저장소에 포함)
OUTPUT = ROOT / "output"                                  # 분석 결과 파일 (저장소 제외)
DASHBOARD_TEMPLATE = ROOT / "dashboard" / "dashboard_template.html"
DASHBOARD_FILE = ROOT / "airline_dashboard.html"          # 완성된 대시보드

# 결과를 저장할 폴더가 없으면 만든다
CHARTS.mkdir(parents=True, exist_ok=True)
(OUTPUT / "tableau").mkdir(parents=True, exist_ok=True)

if not TRAIN_CSV.exists():
    raise SystemExit(
        f"데이터가 없음: {TRAIN_CSV}\n"
        "Kaggle에서 train.csv를 받아 data/train.csv에 두거나, 환경변수 AIRLINE_TRAIN_CSV로 경로를 지정하세요."
    )


def setup_korean_font():
    """설치된 한글 글꼴 중 첫 번째를 matplotlib에 지정 (Windows: 맑은 고딕, macOS: AppleGothic, Linux: 나눔/노토)"""
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    installed_fonts = set()
    for font in font_manager.fontManager.ttflist:
        installed_fonts.add(font.name)

    for font_name in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"]:
        if font_name in installed_fonts:
            plt.rcParams["font.family"] = font_name
            break
    plt.rcParams["axes.unicode_minus"] = False   # 마이너스 기호가 깨지지 않게
