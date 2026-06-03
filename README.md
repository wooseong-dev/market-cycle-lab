# Market Cycle Lab

코인/증시를 예쁜 테마로 보여주는 시장 사이클 대시보드 MVP입니다.

## 기능
- 작년 이맘때 가격
- 현재가 대비 1년 변화율
- ATH 대비 하락률
- 현재 조정 기간
- 평균 조정 기간
- 최장 조정 기간
- 20% 이상 하락 구간 횟수
- 코인/증시/금/유가/달러 비교

## 로컬 실행
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=. uvicorn app.main:app --reload
```

접속: http://127.0.0.1:8000

## Render 환경변수
```env
SITE_NAME=Market Cycle Lab
SITE_URL=https://market-cycle-lab.onrender.com
```

## 데이터 주의
이 MVP는 yfinance로 공개 시장 데이터를 가져옵니다. yfinance는 Yahoo와 공식 제휴된 도구가 아니며 연구/교육 목적 사용을 권장합니다. 실제 상업 운영 시 데이터 라이선스와 약관 확인이 필요합니다.
