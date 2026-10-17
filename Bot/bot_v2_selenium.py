from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

BASE_URL = "https://kkybot.net"
EMAIL    = input("이메일 입력: ")
PASSWD   = input("비밀번호 입력: ")
HEADLESS = input("Headless 모드? (y/n): ").strip().lower() == "y"

response_times = []
waf_result = {"blocked": False, "reason": ""}

def run_bot():
    options = Options()
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'performance': 'ALL'})
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        print("[모드] Headless - WAF JS SDK 챌린지 통과 불가 (봇 감지 대상)")
    else:
        print("[모드] Non-headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    wait = WebDriverWait(driver, 15)

    try:
        print(f"[접속] {BASE_URL}/login")
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)

        try:
            email_input = wait.until(EC.presence_of_element_located(
                (By.NAME, "email")
            ))
            email_input.click()
            email_input.send_keys(EMAIL)
            time.sleep(0.5)
        except Exception:
            waf_result["blocked"] = True
            waf_result["reason"] = "로그인 폼 접근 불가 - WAF JS SDK 챌린지로 차단됨"
            print("[WAF] 로그인 페이지 로딩 실패 - 차단됨")
            return

        passwd_input = driver.find_element(By.NAME, "passwd")
        passwd_input.click()
        passwd_input.send_keys(PASSWD)
        time.sleep(0.5)

        pw_value = driver.find_element(By.NAME, "passwd").get_attribute("value")
        print(f"[디버그] 입력된 비밀번호 길이: {len(pw_value)} / 원본 길이: {len(PASSWD)}")

        time.sleep(0.5)
        start = time.time()
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        elapsed = time.time() - start
        response_times.append(elapsed)
        print(f"[로그인 시도] 소요={elapsed:.3f}초")

        time.sleep(2)

        try:
            perf_logs = driver.get_log('performance')
            for entry in perf_logs:
                msg = json.loads(entry['message'])['message']
                if msg.get('method') == 'Network.responseReceived':
                    url = msg['params']['response']['url']
                    status = msg['params']['response']['status']
                    if 'login' in url:
                        print(f"[네트워크] {url} -> status={status}")
        except Exception as e:
            print(f"[성능 로그 가져오기 실패] {e}")

        page_source_check = driver.page_source
        if "올바르지" in page_source_check or "일치하지" in page_source_check:
            print("[로그인 실패] 에러 메시지 감지됨 - 계정 정보 확인 필요")
            try:
                driver.save_screenshot("bot_v2_login_fail.png")
                print("[스크린샷] bot_v2_login_fail.png 저장")
            except:
                pass
            waf_result["blocked"] = False
            return

        try:
            wait.until(EC.url_changes(f"{BASE_URL}/login"))
        except Exception:
            print(f"[로그인 실패] 현재 URL: {driver.current_url}")
            waf_result["blocked"] = True
            waf_result["reason"] = "로그인 후 URL 변경 없음 - 로그인 차단 가능성"
            return

        print(f"[현재 URL] {driver.current_url}")
        time.sleep(2)

        buy_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'예매하기')]")
        ))
        buy_btn.click()
        print("[경기 선택] 예매하기 버튼 클릭")
        time.sleep(2)
        print(f"[경기 URL] {driver.current_url}")

        seat_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'좌석 선택')]")
        ))
        start = time.time()
        seat_btn.click()
        elapsed = time.time() - start
        response_times.append(elapsed)
        print(f"[좌석 선택] 버튼 클릭 소요={elapsed:.3f}초")
        time.sleep(2)
        print(f"[대기열 URL] {driver.current_url}")

        print("[대기열] ALLOWED 상태 대기 중... (최대 60초)")
        try:
            WebDriverWait(driver, 60).until(
                lambda d: "/verify" in d.current_url or "/seats" in d.current_url
            )
        except Exception:
            print("[대기열] 타임아웃 - 진행 중단")
            return

        print(f"[이동된 URL] {driver.current_url}")

        if "/verify" in driver.current_url:
            print("[CAPTCHA] 보안 확인 페이지 도달!")
            time.sleep(3)

            if not HEADLESS:
                input("화면에서 CAPTCHA를 확인하세요. 계속하려면 Enter를 누르세요...")

            page_source = driver.page_source
            if "보안 확인" in page_source or "captcha" in page_source.lower():
                print("[CAPTCHA] 보안 확인 화면 감지됨")

            try:
                WebDriverWait(driver, 30).until(EC.url_contains("/seats"))
                print(f"[CAPTCHA] 통과됨 - {driver.current_url}")
            except Exception:
                waf_result["blocked"] = True
                waf_result["reason"] = "WAF CAPTCHA 단계에서 차단됨 (자동화 봇은 퍼즐을 풀 수 없음)"
                print("[WAF] CAPTCHA 차단! 30초 대기 후에도 좌석 페이지로 이동하지 못함")
                try:
                    driver.save_screenshot("bot_v2_captcha_blocked.png")
                    print("[스크린샷] bot_v2_captcha_blocked.png 저장")
                except:
                    pass
                return

        print(f"[좌석 페이지] {driver.current_url}")

        try:
            driver.save_screenshot("bot_v2_result.png")
            print("[스크린샷] bot_v2_result.png 저장")
        except:
            pass

    except Exception as e:
        if "invalid session id" in str(e) or "disconnected" in str(e):
            waf_result["blocked"] = True
            waf_result["reason"] = "WAF JS SDK 챌린지로 브라우저 세션 강제 종료"
            print("[WAF] 브라우저 세션 강제 종료 - WAF JS SDK 챌린지 차단됨")
        else:
            print(f"[에러] {e}")
        try:
            driver.save_screenshot("bot_v2_error.png")
        except:
            pass

    finally:
        try:
            driver.quit()
        except:
            pass

        print("\n" + "=" * 50)
        if waf_result["blocked"]:
            print(f"[WAF 결과] 차단됨 - {waf_result['reason']}")
        else:
            print("[WAF 결과] 차단 없음 - 통과")

        if response_times:
            avg = sum(response_times) / len(response_times)
            print(f"\n[결과 요약]")
            print(f"  요청 횟수: {len(response_times)}회")
            print(f"  평균 응답: {avg:.3f}초")
            print(f"  최소 응답: {min(response_times):.3f}초")
            print(f"  최대 응답: {max(response_times):.3f}초")

if __name__ == "__main__":
    run_bot()