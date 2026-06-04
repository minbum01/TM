"""
140p tr[3]부터 + 141p 목표 글까지 수집
목표: [2023 국가직 9급 공업직] 2023 국가직 9급 화공직 필기합격 후기글
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time, json

STOP_TITLE_KEYWORD = "화공직 필기합격"
OUTPUT_FILE = "all_reviews.json"
BASE_URL = "https://gosi.hackers.com/html/mmove.htm?id=exam_passnote_new&m=&cate=&cate2=&cate3=&cate4=&cate5=&cate6=&idx=&user_id=&search_opt=&search_txt=&hb_year=&page={page}"

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options=options)

def get_links_from_page(page, tr_start, tr_end):
    """목록 페이지에서 링크 먼저 전부 수집"""
    driver.get(BASE_URL.format(page=page))
    time.sleep(5)
    posts = []
    for i in range(tr_start, tr_end + 1):
        try:
            base = f'//*[@id="wrapper"]/div[4]/div[2]/div[8]/div[1]/div/div/table/tbody/tr[{i}]'
            title_elem = driver.find_element(By.XPATH, f'{base}/td[1]/a')
            title = title_elem.text.strip()
            href = title_elem.get_attribute('href')
            views = driver.find_element(By.XPATH, f'{base}/td[3]').text.strip()
            posts.append({'title': title, 'views': views, 'href': href})
        except:
            continue
    return posts

def get_post_detail(href):
    driver.get(href)
    time.sleep(4)
    summary = {}
    try:
        elem = driver.find_element(By.XPATH, '//*[@id="wrapper"]/div[4]/div[2]/div/div/div[1]/div/div/div[1]')
        for line in elem.text.strip().split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                summary[k.strip()] = v.strip()
    except: pass
    content = ""
    try:
        elem = driver.find_element(By.XPATH, '//*[@id="wrapper"]/div[4]/div[2]/div/div/div[2]')
        content = elem.text.strip()
    except: pass
    return summary, content

with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
    results = json.load(f)

print(f"기존 데이터: {len(results)}개")

try:
    done = False

    # 140p: tr[3]부터 tr[16]까지 (tr[2]는 이미 수집됨)
    # 141p: tr[2]부터 목표글까지
    pages = [
        (140, 3, 16),
        (141, 2, 16),
    ]

    for page, tr_start, tr_end in pages:
        print(f"\n=== {page}페이지 링크 수집 중 ===")
        posts = get_links_from_page(page, tr_start, tr_end)
        print(f"  {len(posts)}개 링크 수집됨")

        for idx, post in enumerate(posts):
            safe = post['title'][:50].encode('cp949', errors='replace').decode('cp949')
            print(f"  [{idx+1}/{len(posts)}] {safe}...", end=" ")

            summary, content = get_post_detail(post['href'])
            results.append({
                'title': post['title'],
                'views': post['views'],
                'url': post['href'],
                'summary': summary,
                'content': content
            })
            print(f"OK ({len(content)}자)")

            if STOP_TITLE_KEYWORD in post['title']:
                print(f"\n목표 글 도달! 수집 종료.")
                done = True
                break

        if done:
            break

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n완료! 총 {len(results)}개 저장")

finally:
    driver.quit()
