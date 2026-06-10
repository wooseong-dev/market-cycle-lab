# Chart Screen Reader

트레이딩뷰 등 화면에 띄워둔 차트를 캡처해서, 이미지 기반으로 관찰형 차트 리포트를 생성하는 개인용 도구입니다.

## 1. 설치

```bash
pip install -r requirements.txt
```

## 2. API 키 설정

`.env.example` 파일을 복사해서 `.env`로 이름을 바꾼 뒤, 본인의 OpenAI API 키를 넣습니다.

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4.1
```

## 3. 실행

트레이딩뷰 차트를 화면에 띄운 상태에서:

```bash
python app.py
```

실행하면 현재 메인 모니터 화면을 캡처하고, AI가 화면 기준으로 차트 구조를 요약합니다.

## 4. 저장 위치

- 캡처 이미지: `captures/`
- 분석 결과 텍스트: `reports/`

## 5. 주의

이 도구는 화면 이미지 기반 분석입니다. 실제 OHLC 데이터와 오차가 있을 수 있습니다.  
매매 지시용이 아니라 개인 기록/관찰 보조용입니다.
