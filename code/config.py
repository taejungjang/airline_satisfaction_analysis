"""공통 설정: 경로와 한글 폰트. 모든 스크립트가 불러다 씀."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Kaggle 'Airline Passenger Satisfaction' 의 train.csv (저장소에는 포함하지 않음)
TRAIN_CSV = Path(os.environ.get('AIRLINE_TRAIN_CSV', ROOT / 'data' / 'train.csv'))
CHARTS = ROOT / 'charts'                              # 이미지 (저장소에 포함)
OUTPUT = ROOT / 'output'                              # 생성물: 수치 JSON/CSV, Tableau 데이터, 대시보드, PPT (저장소 제외)
DASH_TEMPLATE = ROOT / 'dashboard' / 'dashboard_template.html'

for _d in (CHARTS, OUTPUT, OUTPUT / 'tableau'):
    _d.mkdir(parents=True, exist_ok=True)

if not TRAIN_CSV.exists():
    raise SystemExit(f'데이터가 없음: {TRAIN_CSV}\nKaggle에서 train.csv를 받아 data/train.csv에 두거나 환경변수 AIRLINE_TRAIN_CSV로 경로를 지정할 것')


def setup_font():
    """설치된 한글 폰트 중 첫 번째를 matplotlib에 지정 (Windows: 맑은 고딕, macOS: AppleGothic, Linux: 나눔/노토)."""
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    installed = {f.name for f in fm.fontManager.ttflist}
    for name in ('Malgun Gothic', 'AppleGothic', 'NanumGothic', 'Noto Sans CJK KR'):
        if name in installed:
            plt.rcParams['font.family'] = name
            break
    plt.rcParams['axes.unicode_minus'] = False
