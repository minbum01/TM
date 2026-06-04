import json, re, openpyxl
from collections import Counter
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── 데이터 로드 ──────────────────────────────────────────────
with open('/Users/kimtaeyeon/Desktop/hackers/합격수기/TM/all_reviews.json') as f:
    data = json.load(f)

# 전체 데이터에서 선생님 이름 화이트리스트 구축 (5회 이상 등장)
# 리뷰 수 기준 화이트리스트: 3개 이상 다른 리뷰에서 언급된 이름만 포함
_review_sets = {}  # name -> set of review indices
for _idx, _item in enumerate(data):
    for _line in (_item.get('content', '') or '').split('\n'):
        for _m in re.finditer(r'(?:^|[ \t,.\(\[])([가-힣a-zA-Z·]{2,5})[ \t]*선생님', _line):
            _n = _m.group(1)
            _review_sets.setdefault(_n, set()).add(_idx)

# 3개 이상 리뷰에서 언급 + 명백한 비-이름 제거
_stopwords = {
    '다른', '해커스', '그리고', '또한', '여러', '모든', '각', '특히',
    '수강한', '수강', '인강', '강의에서', '과목별', '교재는', '한국사',
    '행정법', '공무원', '국어', '영어', '법학은', '문법은', '행정학',
    '좋아하는', '싶은', '보니', '많은', '추천', '최대한', '그래도',
    '선택한', '때는', '부분은', '다양한', '들으며', '들었던',
    '있는', '있어서', '해주신', '감사합니다', '주신', '그냥', '중간에',
    '그래서', '우선', '같은', '맞았던', '하지만', '때문에', '없어서',
    '좋은', '것은', '정말', '맞는', '처음', '듣고', '새로운', '의사',
    '점은', '어떤', '아니라', '원하는', '생각으로',
    '과목별로', '이중섭',
}
# 조사/어미로 끝나는 단어 자동 제외
_bad_endings = ('은', '는', '이', '을', '를', '에서', '으로', '에', '의', '도',
                '하는', '하면서', '했던', '없는', '하신', '시켜줄', '하고',
                '으로는', '이나', '로는', '면서', '으며', '비문학')

def _is_valid_name(name):
    for end in _bad_endings:
        if name.endswith(end):
            return False
    return name not in _stopwords

TEACHER_WHITELIST = {
    name for name, reviews in _review_sets.items()
    if len(reviews) >= 3 and _is_valid_name(name)
}

# 접두어 제거 후 매핑
stripped_map = {}
for item in data:
    stripped = re.sub(r'^\[.*?\]\s*', '', item['title']).strip()
    stripped_map[stripped] = item

# ── txt 파싱 ─────────────────────────────────────────────────
txt = open('/Users/kimtaeyeon/Desktop/hackers/합격수기/TM/selected_reviews_txt/PART1_100인_사람키워드.txt').read()

current_keyword = None
entries = []
for line in txt.split('\n'):
    line = line.strip()
    kw_match = re.match(r'#(.+?)\s+\(\d+명\)', line)
    if kw_match:
        current_keyword = '#' + kw_match.group(1).strip()
    title_match = re.match(r'제목\s*:\s*(.+)', line)
    if title_match:
        entries.append({'keyword': current_keyword, 'title': title_match.group(1).strip()})

# ── 선생님 추출 함수 ─────────────────────────────────────────
def extract_teachers(content):
    if not content:
        return ''
    seen = []
    for line in content.split('\n'):
        for m in re.finditer(r'(?:^|[ \t,.\(\[])([가-힣a-zA-Z·]{2,5})[ \t]*선생님', line):
            name = m.group(1).strip()
            if name in TEACHER_WHITELIST and name not in seen:
                seen.append(name)
    return ', '.join(seen)

# ── 특징 조합 함수 ────────────────────────────────────────────
def build_feature(summary):
    parts = []
    year = summary.get('합격년도', '')
    exam = summary.get('응시시험', '')
    grade = summary.get('급수', '')
    serial = summary.get('응시직렬', '')
    period = summary.get('수험기간', '')
    meta = summary.get('metasource', '')

    if year:   parts.append(year)
    if exam:   parts.append(exam)
    if grade:  parts.append(grade)
    if serial: parts.append(serial)
    if period: parts.append(f'수험기간: {period}')
    if meta:   parts.append(f'특이사항: {meta}')
    return ' | '.join(parts)

# ── 행 데이터 구성 ────────────────────────────────────────────
rows = []
for i, e in enumerate(entries, 1):
    item = stripped_map[e['title']]
    summary = item.get('summary', {})
    teachers = extract_teachers(item.get('content', ''))
    feature = build_feature(summary)
    rows.append({
        'no': i,
        'keyword': e['keyword'],
        'title': e['title'],
        'feature': feature,
        'teachers': teachers,
        'url': item.get('url', ''),
    })

# ── Excel 생성 ────────────────────────────────────────────────
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'PART1_100인_사람키워드'

# 헤더
headers = ['번호', '유형', '제목', '특징', '수강 선생님', 'URL']
col_widths = [6, 18, 42, 60, 40, 80]

header_fill = PatternFill(start_color='1F3864', end_color='1F3864', fill_type='solid')
header_font = Font(bold=True, color='FFFFFF', size=11)
center = Alignment(horizontal='center', vertical='center', wrap_text=True)
left_wrap = Alignment(horizontal='left', vertical='center', wrap_text=True)

thin = Side(style='thin', color='CCCCCC')
border = Border(left=thin, right=thin, top=thin, bottom=thin)

# 키워드별 색상 (교번)
keyword_colors = [
    'EBF5FB', 'E8F8F5', 'FEF9E7', 'FDEDEC', 'F4ECF7',
    'EAF4FB', 'E9F7EF', 'FDF2E9', 'F2F3F4', 'EAFAF1',
    'FEF5E7', 'F9EBEA', 'EBF5FB', 'E8F8F5', 'FEF9E7',
]
keyword_list = []
keyword_color_map = {}

for row in rows:
    kw = row['keyword']
    if kw not in keyword_list:
        keyword_list.append(kw)
        idx = len(keyword_list) - 1
        keyword_color_map[kw] = keyword_colors[idx % len(keyword_colors)]

# 헤더 행
ws.row_dimensions[1].height = 28
for ci, (h, w) in enumerate(zip(headers, col_widths), 1):
    cell = ws.cell(row=1, column=ci, value=h)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = center
    cell.border = border
    ws.column_dimensions[get_column_letter(ci)].width = w

# 데이터 행
for ri, row in enumerate(rows, 2):
    ws.row_dimensions[ri].height = 48
    color = keyword_color_map[row['keyword']]
    fill = PatternFill(start_color=color, end_color=color, fill_type='solid')

    values = [row['no'], row['keyword'], row['title'], row['feature'], row['teachers'], row['url']]
    for ci, val in enumerate(values, 1):
        cell = ws.cell(row=ri, column=ci, value=val)
        cell.fill = fill
        cell.border = border
        if ci == 1:
            cell.alignment = center
            cell.font = Font(bold=True, size=10)
        elif ci == 6:
            if val:
                cell.value = val
                cell.hyperlink = val
                cell.font = Font(color='0563C1', underline='single', size=10)
            cell.alignment = left_wrap
        else:
            cell.alignment = left_wrap
            cell.font = Font(size=10)

# 틀 고정
ws.freeze_panes = 'A2'

# 저장
out = '/Users/kimtaeyeon/Desktop/hackers/합격수기/TM/PART1_100인_사람키워드_매칭결과.xlsx'
wb.save(out)
print(f'저장 완료: {out}')
print(f'총 {len(rows)}행 생성')
