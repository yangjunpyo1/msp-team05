import websocket
import httpx
import json
import time
import threading
import random
import string

BASE_URL = "https://kkybot.net"
EMAIL    = input("이메일 입력: ")
PASSWD   = input("비밀번호 입력: ")

token      = None
game_id    = None
lock_times = []

session = httpx.Client(http2=True, timeout=20.0)


def check_waf_block(res, step_name: str) -> bool:
    status = res.status_code
    content_type = res.headers.get("content-type", "")

    if status == 202:
        print(f"[WAF] 챌린지/CAPTCHA 차단! {step_name} 단계 (202)")
        return True
    if status in (403, 405, 429):
        print(f"[WAF] Block 차단! {step_name} 단계, 상태코드={status}")
        return True
    if "application/json" not in content_type:
        print(f"[WAF] 비정상 라우팅 감지! {step_name} 단계 (content-type={content_type})")
        return True
    return False


def login():
    global token
    res = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": EMAIL, "passwd": PASSWD}
    )
    if check_waf_block(res, "로그인"):
        print("\n[WAF 결과] 차단됨 - WebSocket 연결 시도조차 못함")
        exit(0)

    if res.status_code == 200:
        token = res.json()["data"]["accessToken"]
        print(f"[로그인 성공] 토큰: {token[:30]}...")
    else:
        print(f"[로그인 실패] {res.status_code}: {res.text}")
        exit(1)


def get_game_id():
    global game_id
    res = session.get(
        f"{BASE_URL}/api/games",
        headers={"Authorization": f"Bearer {token}"}
    )
    if check_waf_block(res, "경기조회"):
        print("\n[WAF 결과] 차단됨")
        exit(0)

    if res.status_code == 200:
        games = res.json()["data"]["content"]

        on_sale = [
            g for g in games
            if g.get("status") == "ON_SALE"
        ]
        if not on_sale:
            print("[경기 없음] ON_SALE 경기 없음")
            exit(1)
        print("\n[경기 목록]")
        for i, g in enumerate(games):
            home    = g["homeTeam"]["name"]
            away    = g["awayTeam"]["name"]
            stadium = g["stadium"]["name"]
            start   = g.get("startTime", "")
            print(f"  {i+1}. gameId={g['gameId']} "
                  f"| {home} vs {away} "
                  f"| {stadium} | {start}")
        choice  = int(input("\n테스트할 경기 번호 입력: ")) - 1
        game_id = games[choice]["gameId"]
        print(f"[선택] gameId={game_id}")
    else:
        print(f"[경기 조회 실패] {res.status_code}: {res.text}")
        exit(1)


def get_sockjs_url():
    server_id  = str(random.randint(0, 999)).zfill(3)
    session_id = "".join(
        random.choices(string.ascii_lowercase + string.digits, k=8)
    )
    url = f"wss://kkybot.net/ws/seats/{server_id}/{session_id}/websocket"
    print(f"[SockJS URL] {url}")
    return url


def lock_seat(seat_id):
    start = time.time()
    res = session.post(
        f"{BASE_URL}/api/games/{game_id}/seats/lock",
        json={"seatIds": [seat_id]},
        headers={"Authorization": f"Bearer {token}"}
    )
    elapsed = time.time() - start
    lock_times.append(elapsed)
    if check_waf_block(res, "좌석선점"):
        print(f"[선점 시도] seatId={seat_id} → WAF 차단됨 (응답={res.status_code})")
        return
    print(f"[선점 시도] seatId={seat_id} "
          f"응답={res.status_code} "
          f"소요={elapsed:.3f}초")


def handle_stomp(ws, message):
    if message.startswith("CONNECTED"):
        print("[STOMP] 연결 완료 → 좌석 구독 시작")
        subscribe_frame = (
            f"SUBSCRIBE\n"
            f"id:sub-0\n"
            f"destination:/topic/seats/{game_id}\n\n\x00"
        )
        ws.send(json.dumps([subscribe_frame]))
        print(f"[구독] /topic/seats/{game_id}")

    elif message.startswith("MESSAGE"):
        body = message.split("\n\n")[1].rstrip("\x00")
        try:
            data = json.loads(body)
            print(f"[좌석 변경 감지] {data}")
            if data.get("status") == "AVAILABLE":
                seat_id = data.get("seatId")
                print(f"[오픈 감지] 즉시 선점! seatId={seat_id}")
                threading.Thread(
                    target=lock_seat,
                    args=(seat_id,)
                ).start()
        except Exception as e:
            print(f"[파싱 오류] {e}")


def on_open(ws):
    print("[WebSocket] 연결 성공")


def on_message(ws, message):
    if not message or message == "\n":
        return

    msg_type = message[0]

    if msg_type == "o":
        print("[SockJS] 오픈 프레임 수신")
        connect_frame = (
            "CONNECT\n"
            "accept-version:1.1,1.0\n"
            f"Authorization:Bearer {token}\n"
            "heart-beat:10000,10000\n\n\x00"
        )
        ws.send(json.dumps([connect_frame]))

    elif msg_type == "h":
        return

    elif msg_type == "a":
        messages = json.loads(message[1:])
        for msg in messages:
            handle_stomp(ws, msg)

    elif msg_type == "c":
        print("[SockJS] 서버에서 닫음")


def on_error(ws, error):
    print(f"[에러] {error}")
    print("[WAF] WebSocket 핸드셰이크 단계에서 차단되었을 가능성 있음")


def on_close(ws, code, msg):
    print(f"[WebSocket 종료] code={code}")
    if code != 1000:
        print(f"[WAF] WebSocket 연결이 비정상 종료됨 (code={code}) - WAF 차단 가능성")
    if lock_times:
        avg = sum(lock_times) / len(lock_times)
        print(f"\n[결과 요약]")
        print(f"  선점 시도: {len(lock_times)}회")
        print(f"  평균 응답: {avg:.3f}초")
        print(f"  최소 응답: {min(lock_times):.3f}초")
        print(f"  최대 응답: {max(lock_times):.3f}초")


if __name__ == "__main__":
    login()
    get_game_id()

    WS_URL = get_sockjs_url()
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    print(f"\n[대기 중] 좌석 오픈 이벤트 감지 시 자동 선점...")
    ws.run_forever()