"""
3단계 봇 - Python Playwright + 프록시 IP 로테이션 봇 (하이브리드)
Playwright로 실제 브라우저를 띄워 로그인 후 토큰을 획득하고,
이후 API는 브라우저 컨텍스트를 통해 직접 호출한다.
TLS fingerprint가 실제 Chrome과 동일하여 WAF Bot Control 탐지가 어렵다.
프록시 목록을 로테이션하여 IP 기반 차단도 우회 가능.
"""
import argparse
import asyncio
import csv
import os
from datetime import datetime

from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

BASE_URL     = "https://kkybot.net"
FRONTEND_URL = "http://localhost:5173"
LOG_FILE     = "bot_v3_results.csv"


class WAFBlockedException(Exception):
    def __init__(self, status_code, reason):
        self.status_code = status_code
        self.reason = reason
        super().__init__(f"WAF blocked: {status_code} - {reason}")


class PlaywrightTicketingBot:
    def __init__(
        self,
        email: str,
        password: str,
        headless: bool = True,
        proxies: list[str] | None = None,
    ):
        self.email = email
        self.password = password
        self.headless = headless
        self.proxies = proxies or []
        self.results = []

    def _log(self, msg: str):
        print(f"[Playwright Bot] {msg}")

    def _record(self, endpoint: str, status_code: int, proxy: str = "", note: str = ""):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "status_code": status_code,
            "proxy": proxy,
            "note": note,
        }
        self.results.append(entry)
        self._log(f"{endpoint} → {status_code} proxy={proxy} {note}")

    def _save_results(self):
        if not self.results:
            return
        file_exists = os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["timestamp", "endpoint", "status_code", "proxy", "note"]
            )
            if not file_exists:
                writer.writeheader()
            writer.writerows(self.results)
        self._log(f"결과 저장 완료: {LOG_FILE} ({len(self.results)}건)")

    def _get_proxy(self, index: int) -> str | None:
        if not self.proxies:
            return None
        proxy = self.proxies[index % len(self.proxies)]
        self._log(f"프록시 선택: {proxy} (index={index})")
        return proxy

    def _check_waf_block(self, response, step_name: str):
        status = response.status
        content_type = response.headers.get("content-type", "")
        if status == 202:
            self._log(f"[WAF] CAPTCHA 차단! {step_name} 단계에서 차단됨 (202)")
            raise WAFBlockedException(202, f"{step_name} 단계 CAPTCHA")
        if status in (403, 405, 429):
            self._log(f"[WAF] Block 차단! {step_name} 단계, 상태코드={status}")
            raise WAFBlockedException(status, f"{step_name} 단계 Block")
        if "application/json" not in content_type:
            self._log(f"[경고] 비정상 응답 ({step_name}, content-type={content_type})")
            raise WAFBlockedException(status, f"{step_name} 단계 비정상 라우팅")

    async def run_once(self, index: int = 0, num_seats: int = 1):
        proxy = self._get_proxy(index)
        launch_kwargs = {"headless": self.headless}
        if proxy:
            launch_kwargs["proxy"] = {"server": proxy}

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="ko-KR",
                timezone_id="Asia/Seoul",
            )
            page = await context.new_page()
            await stealth_async(page)
            self._log("Stealth 모드 적용 완료")

            try:
                # 로그인 → 토큰 획득
                login_res = await context.request.fetch(
                    f"{BASE_URL}/api/auth/login",
                    method="POST",
                    headers={"Content-Type": "application/json"},
                    data={"email": self.email, "passwd": self.password},
                )
                self._record("/api/auth/login", login_res.status, proxy=proxy or "")
                self._check_waf_block(login_res, "로그인")
                login_data = await login_res.json()
                token = login_data["data"]["accessToken"]
                self._log(f"로그인 성공: {self.email}")

                # 경기 조회
                games_res = await context.request.fetch(
                    f"{BASE_URL}/api/games",
                    method="GET",
                    headers={"Authorization": f"Bearer {token}"},
                )
                self._record("/api/games", games_res.status, proxy=proxy or "")
                self._check_waf_block(games_res, "경기조회")
                games_data = await games_res.json()
                games = games_data["data"]["content"]
                on_sale = [g for g in games if g.get("status") == "ON_SALE"]
                if not on_sale:
                    self._log("예매 가능한 경기 없음")
                    return
                game = on_sale[0]
                game_id = game["gameId"]
                self._log(f"경기 선택: (id={game_id})")

                # 좌석 조회
                seats_res = await context.request.fetch(
                    f"{BASE_URL}/api/games/{game_id}/seats",
                    method="GET",
                    headers={"Authorization": f"Bearer {token}"},
                )
                self._record(f"/api/games/{game_id}/seats", seats_res.status, proxy=proxy or "")
                self._check_waf_block(seats_res, "좌석조회")
                seats_data = await seats_res.json()
                zones = seats_data["data"]["zones"]
                all_seats = []
                for zone in zones:
                    for seat in zone.get("seats", []):
                        seat["zoneId"] = zone["zoneId"]
                        all_seats.append(seat)

                available_seats = [s for s in all_seats if s.get("status") == "AVAILABLE"]
                if len(available_seats) < num_seats:
                    self._log(f"잔여 좌석 부족: {len(available_seats)}개")
                    return
                target_ids = [s["seatId"] for s in available_seats[:num_seats]]
                self._log(f"좌석 점유 시도: {target_ids}")

                # 좌석 선점
                lock_res = await context.request.fetch(
                    f"{BASE_URL}/api/games/{game_id}/seats/lock",
                    method="POST",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    data={"seatIds": target_ids},
                )
                self._record(f"/api/games/{game_id}/seats/lock", lock_res.status, proxy=proxy or "")
                self._check_waf_block(lock_res, "좌석선점")
                lock_data = await lock_res.json()
                lock_token = lock_data["data"]["lockToken"]
                self._log(f"좌석 점유 완료 (lockToken={lock_token})")

                # 예매
                reserve_res = await context.request.fetch(
                    f"{BASE_URL}/api/reservations",
                    method="POST",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    data={"gameId": game_id, "lockToken": lock_token},
                )
                self._record("/api/reservations", reserve_res.status, proxy=proxy or "")
                self._check_waf_block(reserve_res, "예매확정")
                reserve_data = await reserve_res.json()
                self._log(f"예매 성공: reservationId={reserve_data['data'].get('reservationId')}")

            except WAFBlockedException:
                raise
            except Exception as e:
                self._log(f"오류 발생: {e}")
                raise
            finally:
                await browser.close()

    async def run(self, num_seats: int = 1, repeat: int = 1, interval: float = 1.0):
        self._log(f"반복 실행 시작: {repeat}회, 간격 {interval}초, 프록시 {len(self.proxies)}개")
        success = 0
        captcha = 0
        blocked = 0
        error = 0

        for i in range(repeat):
            self._log(f"--- 시도 {i + 1}/{repeat} ---")
            try:
                await self.run_once(index=i, num_seats=num_seats)
                success += 1
            except WAFBlockedException as e:
                if e.status_code == 202:
                    captcha += 1
                else:
                    blocked += 1
                self._log(f"[WAF 차단] {e.reason}")
            except Exception as e:
                error += 1
                self._log(f"오류: {e}")

            if i < repeat - 1:
                await asyncio.sleep(interval)

        self._log(f"완료 — 성공: {success}, CAPTCHA: {captcha}, Block: {blocked}, 오류: {error}, 전체: {repeat}")
        if captcha > 0 or blocked > 0:
            self._log(f"[WAF 결과] 차단됨 (CAPTCHA={captcha}, Block={blocked})")
        else:
            self._log("[WAF 결과] 차단 없음 - 전부 통과")
        self._save_results()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="3단계 Playwright + 프록시 로테이션 봇")
    parser.add_argument("--email", default="bot@test.com")
    parser.add_argument("--password", default="test1234!!")
    parser.add_argument("--seats", type=int, default=1, help="예매 좌석 수")
    parser.add_argument("--repeat", type=int, default=1, help="반복 횟수")
    parser.add_argument("--interval", type=float, default=1.0, help="요청 간격 (초)")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--url", default=BASE_URL, help="대상 서버 URL")
    parser.add_argument(
        "--proxies",
        nargs="*",
        default=[],
        help="프록시 목록 (예: http://host1:port1 http://host2:port2)",
    )
    args = parser.parse_args()

    BASE_URL = args.url

    bot = PlaywrightTicketingBot(
        email=args.email,
        password=args.password,
        headless=args.headless,
        proxies=args.proxies,
    )
    asyncio.run(bot.run(num_seats=args.seats, repeat=args.repeat, interval=args.interval))