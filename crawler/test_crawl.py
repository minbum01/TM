"""
해커스 공무원 합격수기 크롤러 - 테스트 (1페이지, 1게시글)
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

# Chrome 설정
options = Options()
# options.add_argument('--headless')  # 테스트 시에는 브라우저 보이게
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

try:
    # 1단계: 목록 페이지 접근
    list_url = "https://gosi.hackers.com/html/mmove.htm?id=exam_passnote_new&m=&cate=&cate2=&cate3=&cate4=&cate5=&cate6=&idx=&user_id=&search_opt=&search_txt=&hb_year=&page=1"
    driver.get(list_url)
    time.sleep(5)  # 동적 로딩 대기

    # 페이지 소스 일부 확인
    print("=== 페이지 타이틀 ===")
    print(driver.title)

    # 1페이지: tr[10] ~ tr[24]
    print("\n=== 목록에서 게시글 링크 추출 (tr10~tr24) ===")
    links = []
    for i in range(10, 25):
        try:
            xpath = f'//*[@id="wrapper"]/div[4]/div[2]/div[8]/div[1]/div/div/table/tbody/tr[{i}]/td[1]/a'
            elem = driver.find_element(By.XPATH, xpath)
            href = elem.get_attribute('href')
            title = elem.text.strip()
            print(f"  tr[{i}]: {title[:50]}... -> {href[:80] if href else 'NO HREF'}...")
            links.append({'tr': i, 'title': title, 'href': href})
        except Exception as e:
            print(f"  tr[{i}]: NOT FOUND - {e}")

    print(f"\n총 {len(links)}개 링크 발견")

    # 2단계: 첫 번째 게시글 접근
    if links:
        first_link = links[0]['href']
        print(f"\n=== 첫 번째 게시글 접근: {first_link} ===")
        driver.get(first_link)
        time.sleep(5)

        # 요약 정보
        print("\n=== 요약 정보 (div[1]) ===")
        try:
            summary_xpath = '//*[@id="wrapper"]/div[4]/div[2]/div/div/div[1]/div/div/div[1]'
            summary_elem = driver.find_element(By.XPATH, summary_xpath)
            print(summary_elem.text)
        except Exception as e:
            print(f"요약 정보 못 찾음: {e}")
            # 대안: 더 넓은 범위로 시도
            try:
                alt_xpath = '//*[@id="wrapper"]/div[4]/div[2]/div/div/div[1]'
                alt_elem = driver.find_element(By.XPATH, alt_xpath)
                print("(대안 xpath)")
                print(alt_elem.text[:500])
            except:
                print("대안도 실패")

        # 본문 내용
        print("\n=== 본문 내용 (div[2]) ===")
        try:
            content_xpath = '//*[@id="wrapper"]/div[4]/div[2]/div/div/div[2]'
            content_elem = driver.find_element(By.XPATH, content_xpath)
            print(content_elem.text[:500])
            print("...")
        except Exception as e:
            print(f"본문 못 찾음: {e}")

    # 3단계: 페이지 수 확인 (마지막 페이지 버튼)
    print("\n=== 페이징 구조 확인 ===")
    driver.get(list_url)
    time.sleep(5)
    try:
        # 페이징 영역 텍스트 확인
        paging_area = driver.find_element(By.XPATH, '//*[@id="wrapper"]/div[4]/div[2]/div[8]/div[1]/div/div')
        # 페이지 번호 링크들 찾기
        page_links = paging_area.find_elements(By.TAG_NAME, 'a')
        page_nums = []
        for pl in page_links:
            href = pl.get_attribute('href') or ''
            text = pl.text.strip()
            if 'page=' in href and text.isdigit():
                page_nums.append(int(text))
        if page_nums:
            print(f"  보이는 페이지 번호: {page_nums}")
            print(f"  최대 페이지: {max(page_nums)}")

        # '맨끝' 또는 '>' 버튼 찾기
        all_links = driver.find_elements(By.TAG_NAME, 'a')
        for link in all_links:
            href = link.get_attribute('href') or ''
            if 'page=' in href and ('exam_passnote_new' in href):
                import re
                match = re.search(r'page=(\d+)', href)
                if match:
                    page_nums.append(int(match.group(1)))
        if page_nums:
            print(f"  발견된 최대 페이지: {max(page_nums)}")
    except Exception as e:
        print(f"  페이징 확인 실패: {e}")

finally:
    driver.quit()
    print("\n=== 테스트 완료 ===")
