from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

BASE_URL = "https://kkybot.click"
EMAIL    = input("이메일 입력: ")
PASSWD   = input("비밀번호 입력: ")
HEADLESS = input("Headless 모드? (y/n): ").strip().lower() == "y"

response_times = []
waf_result = {"blocked": False, "reason": ""}

def run_bot():
    options = Options()
    if HEADLESS:
        options.add_argument("--headless")
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
    wait = WebDriverWait(driver, 15)

    try:
        print(f"[접속] {BASE_URL}/login")
        driver.get(f"{BASE_URL}/login")
        time.sleep(3)

        page_source = driver.page_source
        if "challenge" in page_source.lower() or "awswaf" in page_source.lower():
            waf_result["blocked"] = True
            waf_result["reason"] = "WAF JS SDK 챌린지 차단"
            print("[WAF] JS SDK 챌린지 감지 - 봇 차단됨")
            return

        try:
            email_input = wait.until(EC.presence_of_element_located(
                (By.NAME, "email")
            ))
            email_input.send_keys(EMAIL)
        except Exception:
            waf_result["blocked"] = True
            waf_result["reason"] = "로그인 폼 접근 불가 - WAF 차단"
            print("[WAF] 로그인 페이지 로딩 실패 - WAF JS SDK 챌린지로 차단됨")
            return

        driver.find_element(By.NAME, "passwd").send_keys(PASSWD)

        start = time.time()
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        elapsed = time.time() - start
        response_times.append(elapsed)
        print(f"[로그인 시도] 소요={elapsed:.3f}초")

        wait.until(EC.url_changes(f"{BASE_URL}/login"))
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
        wait_seats = WebDriverWait(driver, 60)
        wait_seats.until(EC.url_contains("/seats"))
        print(f"[좌석 페이지] {driver.current_url}")

        try:
            WebDriverWait(driver, 120).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "div.animate-spin")
                )
            )
            print("[구역] 로딩 완료")
        except:
            print("[구역] 로딩 타임아웃 (계속 진행)")

        time.sleep(1)

        zone_items = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'cursor-pointer') and contains(@class,'border-b')]"
        )
        print(f"[구역] 발견된 구역 수: {len(zone_items)}")

        if zone_items:
            driver.execute_script("arguments[0].click()", zone_items[0])
            print("[구역 선택] 첫 번째 구역 클릭")
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "button.bg-white.border.border-gray-300")
                    )
                )
                print("[좌석] 로딩 완료")
            except:
                print("[좌석] 로딩 타임아웃")
            time.sleep(1)
        else:
            print("[구역] 선택 가능한 구역 없음")

        seats = driver.find_elements(By.CSS_SELECTOR, "button.bg-white.border.border-gray-300")
        print(f"[좌석] 발견된 좌석 수: {len(seats)}")

        if seats:
            start = time.time()
            driver.execute_script("arguments[0].click()", seats[0])
            elapsed = time.time() - start
            response_times.append(elapsed)
            print(f"[좌석 선택] 소요={elapsed:.3f}초")
            time.sleep(1)
        else:
            print("[좌석] 선택 가능한 좌석 없음")

        try:
            lock_btn = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(),'선택 완료')]")
                )
            )
            start = time.time()
            driver.execute_script("arguments[0].click()", lock_btn)
            elapsed = time.time() - start
            response_times.append(elapsed)
            print(f"[선점 시도] 소요={elapsed:.3f}초")
            time.sleep(2)
            try:
                alert = driver.switch_to.alert
                print(f"[Alert] {alert.text}")
                alert.accept()
            except:
                pass
            time.sleep(1)
        except Exception as e:
            print(f"[선점 에러] {e}")

        try:
            WebDriverWait(driver, 15).until(EC.url_contains("/checkout"))
            print(f"[결제 페이지] {driver.current_url}")
            time.sleep(1)

            pay_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'결제하기')]")
            ))
            start = time.time()
            pay_btn.click()
            elapsed = time.time() - start
            response_times.append(elapsed)
            print(f"[결제 시도] 소요={elapsed:.3f}초")
            time.sleep(3)

            try:
                alert = driver.switch_to.alert
                print(f"[Alert] {alert.text}")
                alert.accept()
                print("[결제 완료]")
            except:
                pass

            print(f"[최종 URL] {driver.current_url}")

        except Exception as e:
            print(f"[결제 에러] {e}")

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