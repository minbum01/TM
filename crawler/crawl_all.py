"""
해커스 공무원 합격수기 전체 크롤러
- 목록에서: 제목, 조회수, 링크
- 개별 글에서: 요약정보(7개 필드), 본문
- 결과: all_reviews.json
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
import sys

# === 설정 ===
BASE_URL = "https://gosi.hackers.com/html/mmove.htm?id=exam_passnote_new&m=&cate=&cate2=&cate3=&cate4=&cate5=&cate6=&idx=&user_id=&search_opt=&search_txt=&hb_year=&page={page}"
OUTPUT_FILE = "all_reviews.json"
PROGRESS_FILE = "crawl_progress.json"
PAGE_LOAD_WAIT = 5
POST_LOAD_WAIT = 4
MAX_PAGES = 350  # 여유있게
BATCH_SIZE = 5   # 5페이지마다 확인

# === 진행 상황 저장/복원 ===
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_page": 0, "total_posts": 0}

def save_progress(page, total):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"last_page": page, "total_posts": total}, f)

def load_existing_results():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_results(results):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

# === 크롤링 함수 ===
def get_posts_from_list(driver, page):
    """목록 페이지에서 게시글 정보 추출"""
    url = BASE_URL.format(page=page)
    driver.get(url)
    time.sleep(PAGE_LOAD_WAIT)

    posts = []
    # page 1: tr[10]~tr[24], page 2+: tr[2]~tr[16]
    if page == 1:
        tr_start, tr_end = 10, 25
    else:
        tr_start, tr_end = 2, 17

    for i in range(tr_start, tr_end):
        try:
            base_xpath = f'//*[@id="wrapper"]/div[4]/div[2]/div[8]/div[1]/div/div/table/tbody/tr[{i}]'

            # 제목 + 링크
            title_elem = driver.find_element(By.XPATH, f'{base_xpath}/td[1]/a')
            title = title_elem.text.strip()
            href = title_elem.get_attribute('href')

            # 조회수
            view_elem = driver.find_element(By.XPATH, f'{base_xpath}/td[3]')
            views = view_elem.text.strip()

            if title and href:
                posts.append({
                    'title': title,
                    'views': views,
                    'href': href
                })
        except:
            continue

    return posts

def get_post_detail(driver, href):
    """개별 게시글에서 요약정보 + 본문 추출"""
    driver.get(href)
    time.sleep(POST_LOAD_WAIT)

    # 요약정보
    summary = {}
    try:
        summary_xpath = '//*[@id="wrapper"]/div[4]/div[2]/div/div/div[1]/div/div/div[1]'
        summary_elem = driver.find_element(By.XPATH, summary_xpath)
        summary_text = summary_elem.text.strip()
        for line in summary_text.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                summary[key.strip()] = val.strip()
    except:
        pass

    # 본문
    content = ""
    try:
        content_xpath = '//*[@id="wrapper"]/div[4]/div[2]/div/div/div[2]'
        content_elem = driver.find_element(By.XPATH, content_xpath)
        content = content_elem.text.strip()
    except:
        pass

    return summary, content

# === 메인 ===
def main():
    progress = load_progress()
    results = load_existing_results()
    start_page = progress["last_page"] + 1

    if start_page > 1:
        print(f"이전 진행 상황 복원: {progress['last_page']}페이지까지 완료, {progress['total_posts']}개 수집됨")
        print(f"{start_page}페이지부터 재개합니다.\n")

    # Chrome 설정
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(options=options)

    try:
        empty_page_count = 0
        batch_start = start_page

        for page in range(start_page, MAX_PAGES + 1):
            print(f"\n{'='*50}")
            print(f"[페이지 {page}] 목록 크롤링 중...")

            posts = get_posts_from_list(driver, page)

            if not posts:
                empty_page_count += 1
                print(f"  게시글 없음 (연속 빈 페이지: {empty_page_count})")
                if empty_page_count >= 3:
                    print("\n3회 연속 빈 페이지 → 크롤링 종료")
                    break
                continue
            else:
                empty_page_count = 0

            print(f"  {len(posts)}개 게시글 발견")

            for idx, post in enumerate(posts):
                safe_title = post['title'][:50].encode('cp949', errors='replace').decode('cp949')
                print(f"  [{idx+1}/{len(posts)}] {safe_title}...", end=" ")

                try:
                    summary, content = get_post_detail(driver, post['href'])

                    result = {
                        'title': post['title'],
                        'views': post['views'],
                        'url': post['href'],
                        'summary': summary,
                        'content': content
                    }
                    results.append(result)
                    print(f"OK ({len(content)}자)")

                except Exception as e:
                    print(f"ERROR: {e}")
                    results.append({
                        'title': post['title'],
                        'views': post['views'],
                        'url': post['href'],
                        'summary': {},
                        'content': '',
                        'error': str(e)
                    })

            # 페이지 완료 시마다 저장
            save_results(results)
            save_progress(page, len(results))
            print(f"  → 저장 완료 (누적 {len(results)}개)")

            # 5페이지마다 진행상황 출력
            if (page - batch_start + 1) % BATCH_SIZE == 0:
                print(f"\n{'='*50}")
                print(f"[진행] {batch_start}~{page}페이지 완료 | 누적 수기: {len(results)}개")
                print(f"{'='*50}\n")
                batch_start = page + 1

    except KeyboardInterrupt:
        print("\n\n사용자 중단 (Ctrl+C)")
        save_results(results)
        save_progress(page, len(results))
        print(f"현재까지 {len(results)}개 저장 완료. 다시 실행하면 이어서 진행됩니다.")

    except Exception as e:
        print(f"\n\n예상치 못한 오류: {e}")
        save_results(results)
        save_progress(page, len(results))
        print(f"현재까지 {len(results)}개 저장 완료. 다시 실행하면 이어서 진행됩니다.")

    finally:
        driver.quit()
        print(f"\n{'='*50}")
        print(f"크롤링 완료!")
        print(f"총 {len(results)}개 합격수기 수집")
        print(f"저장 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
