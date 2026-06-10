import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import mss
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")

CAPTURE_DIR = Path("captures")
REPORT_DIR = Path("reports")

CAPTURE_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)


def require_api_key() -> None:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY가 없습니다. .env 파일을 만들고 API 키를 넣어주세요.\n"
            "예: OPENAI_API_KEY=sk-your-api-key-here"
        )


def get_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def capture_screen(monitor_index: int = 1) -> Path:
    """
    현재 모니터 화면을 캡처해서 JPEG로 저장합니다.

    monitor_index:
    - 1: 기본 메인 모니터
    - 2 이상: 보조 모니터
    """
    timestamp = get_timestamp()
    output_path = CAPTURE_DIR / f"chart_{timestamp}.jpg"

    with mss.mss() as sct:
        monitors = sct.monitors

        if monitor_index >= len(monitors):
            print(f"[경고] monitor_index={monitor_index} 모니터가 없습니다. 메인 모니터(1)를 사용합니다.")
            monitor_index = 1

        monitor = monitors[monitor_index]
        shot = sct.grab(monitor)

        img = Image.frombytes("RGB", shot.size, shot.rgb)
        img.save(output_path, "JPEG", quality=92)

    return output_path


def encode_image_to_data_url(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    suffix = image_path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


def save_report(text: str, image_path: Path) -> Path:
    timestamp = get_timestamp()
    report_path = REPORT_DIR / f"report_{timestamp}.txt"

    content = f"""Chart Screen Reader Report
Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Image file: {image_path}

{text}
"""

    report_path.write_text(content, encoding="utf-8")
    return report_path


def build_prompt(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    user_note: Optional[str] = None,
) -> str:
    symbol_text = symbol.strip() if symbol else "화면에 보이는 종목"
    timeframe_text = timeframe.strip() if timeframe else "화면에 보이는 타임프레임"
    note_text = user_note.strip() if user_note else "없음"

    return f"""
너는 개인용 차트 관찰 보조 도구다.
사용자가 제공한 화면 캡처 이미지만 보고 차트를 해석한다.

대상:
- 종목: {symbol_text}
- 타임프레임: {timeframe_text}
- 사용자 메모: {note_text}

중요 원칙:
- 절대 매수/매도 지시를 하지 마라.
- 확정적으로 예측하지 마라.
- 보이는 화면 기준이라고 명시해라.
- 가격 숫자가 작거나 흐릿하면 억지로 단정하지 마라.
- 차트에 그려진 박스, 추세선, 피보나치, 지표, 가격대가 보이면 관찰 대상으로 삼아라.
- 사용자는 과장된 트레이딩 말투를 싫어한다.
- 차분한 기록형, 관찰형, 리스크 관리형 문체로 써라.
- 한국어로 답해라.

출력 형식은 반드시 아래 구조를 지켜라.

[화면 기준 한줄 요약]
- 

[현재 구조]
- 추세:
- 변동성:
- 박스/채널/되돌림:
- 매수세/매도세 인상:
- 눈에 띄는 지지 후보:
- 눈에 띄는 저항 후보:

[관찰 포인트]
1.
2.
3.

[상방 시나리오]
- 

[하방 시나리오]
- 

[중립/대기 시나리오]
- 

[무효화/주의]
- 이미지 기반 분석이라 실제 OHLC 데이터와 오차 가능
- 화면상 보이는 구조만 해석한 것이며 매매 지시가 아님
- 중요한 이벤트/뉴스/상위 프레임은 별도 확인 필요

[X / 매매일지용 짧은 요약]
- 3~5줄로 짧게 정리
"""


def analyze_chart_image(
    image_path: Path,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    user_note: Optional[str] = None,
) -> str:
    require_api_key()

    client = OpenAI(api_key=OPENAI_API_KEY)

    image_data_url = encode_image_to_data_url(image_path)
    prompt = build_prompt(symbol=symbol, timeframe=timeframe, user_note=user_note)

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                    {
                        "type": "input_image",
                        "image_url": image_data_url,
                    },
                ],
            }
        ],
    )

    return response.output_text


def ask_optional(label: str) -> Optional[str]:
    value = input(f"{label} (엔터로 생략): ").strip()
    return value if value else None


def main() -> None:
    print("")
    print("============================================")
    print(" Chart Screen Reader")
    print(" 화면상의 차트를 캡처해서 관찰형 리포트를 생성합니다.")
    print("============================================")
    print("")

    print("트레이딩뷰/차트 화면을 띄워둔 뒤 엔터를 누르세요.")
    input("준비되면 Enter... ")

    symbol = ask_optional("종목명 예: BTCUSDT, ETHUSDT, NQ1!, SPY")
    timeframe = ask_optional("타임프레임 예: 1m, 5m, 1h, 1D")
    user_note = ask_optional("추가 메모 예: 피보 박스 위주로 봐줘")

    monitor_input = input("캡처할 모니터 번호 기본 1, 보조 2... (엔터=1): ").strip()
    try:
        monitor_index = int(monitor_input) if monitor_input else 1
    except ValueError:
        monitor_index = 1

    print("")
    print("[1/3] 화면 캡처 중...")
    image_path = capture_screen(monitor_index=monitor_index)
    print(f"캡처 완료: {image_path}")

    print("")
    print("[2/3] AI 분석 중... 잠시 기다려주세요.")
    result = analyze_chart_image(
        image_path=image_path,
        symbol=symbol,
        timeframe=timeframe,
        user_note=user_note,
    )

    print("")
    print("[3/3] 분석 완료")
    print("")
    print("=" * 80)
    print(result)
    print("=" * 80)

    report_path = save_report(result, image_path)
    print("")
    print(f"리포트 저장 완료: {report_path}")
    print("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n사용자가 종료했습니다.")
    except Exception as e:
        print("")
        print("[오류 발생]")
        print(e)
        print("")
        print("체크할 것:")
        print("1. .env 파일에 OPENAI_API_KEY가 들어갔는지")
        print("2. OPENAI_MODEL 값이 계정에서 사용 가능한 모델인지")
        print("3. pip install -r requirements.txt 를 실행했는지")
