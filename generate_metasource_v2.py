#!/usr/bin/env python3
"""
수기 metasource 태그 자동 생성 v2
====================================

[상태 구분]
  null  → 아직 미처리 (처리 대상)
  ""    → 처리 완료, 특징 없음
  "..."  → 처리 완료, 태그 있음
  ※ 배치 실패 시 null 유지 → 다음 실행 때 이어서 처리

[사용 전 준비]
1. python3 generate_metasource_v2.py --reset
   → 모든 metasource를 null로 초기화

2. all_reviews.json 파일에서 원하는 스타일로 20개 이상 직접 입력
   예: "metasource": "'노베이스', '단기합격'"
   예: "metasource": ""  ← 특징 없으면 빈 문자열

3. python3 generate_metasource_v2.py
   → 직접 입력한 예시를 few-shot으로 삼아 null 항목만 자동 처리
   → 중단 후 재실행하면 null 항목부터 이어서 진행

[옵션]
  --reset         모든 metasource를 null로 초기화 (수동 입력분 포함)
  --dry-run       실제 저장 없이 처음 배치만 미리보기
  --batch N       배치 크기 (기본: 20)
  --examples N    few-shot 예시 사용 개수 (기본: 10)
  --status        현재 처리 진행 현황만 출력
"""

import json
import subprocess
import sys
import re
import random
import argparse

INPUT_FILE = "/Users/kimtaeyeon/Desktop/hackers/합격수기/TM/all_reviews.json"


def load_data():
    with open(INPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def print_status(data):
    """처리 현황 출력"""
    total = len(data)
    done = sum(1 for item in data if item.get("summary", {}).get("metasource") is not None)
    has_tag = sum(1 for item in data if item.get("summary", {}).get("metasource"))
    remaining = sum(1 for item in data if item.get("summary", {}).get("metasource") is None)
    print(f"전체:    {total}개")
    print(f"처리완료: {done}개  (태그 있음: {has_tag}개 / 태그 없음: {done - has_tag}개)")
    print(f"미처리:  {remaining}개 (null)")


def reset_all(data):
    """모든 metasource를 null로 초기화"""
    count = 0
    for item in data:
        if "summary" in item:
            item["summary"]["metasource"] = None
            count += 1
    print(f"{count}개 수기의 metasource를 null로 초기화했습니다.")
    return data


def get_seed_examples(data, max_examples=10):
    """
    수동으로 입력된(non-null, 문자열) 항목을 few-shot 예시로 수집.
    null이 아닌 항목 = 사용자가 직접 입력했거나 이전에 처리된 항목.
    다양성을 위해 랜덤 샘플링.
    """
    filled = [
        item for item in data
        if item.get("summary", {}).get("metasource") is not None  # null 제외
    ]
    if len(filled) > max_examples:
        filled = random.sample(filled, max_examples)
    return filled


def build_prompt(examples: list, batch: list) -> str:
    """few-shot 예시 + 처리 대상 배치로 프롬프트 구성"""

    examples_text = ""
    for ex in examples:
        title = ex.get("title", "")
        content = ex.get("content", "")[:400]
        metasource = ex["summary"].get("metasource", "")
        examples_text += f"제목: {title}\n내용: {content}\n→ metasource: {metasource}\n\n"

    batch_text = ""
    for i, item in enumerate(batch):
        title = item.get("title", "")
        content = item.get("content", "")[:400]
        batch_text += f"[{i}] 제목: {title}\n내용: {content}\n\n"

    prompt = f"""공무원 합격 수기에서 수험생의 특수한 상황/배경을 짧은 키워드로 추출합니다.

[규칙]
- 수기에서 명확히 드러나는 특수한 상황, 배경, 연령, 고충만 추출
- 일반적인 내용(열심히 공부, 기출 반복 등)은 태그 제외
- 특별한 특징이 없으면 빈 문자열 ""
- 아래 예시와 동일한 포맷 사용

[예시]
{examples_text}
[처리 대상 {len(batch)}개]
{batch_text}
위 {len(batch)}개 수기의 metasource를 추출하여 JSON 배열로만 응답하세요.
반드시 배열 길이가 {len(batch)}개여야 합니다.
예: ["'태그1', '태그2'", "", "'태그1'", ...]

JSON 배열만 출력:"""

    return prompt


def extract_batch(examples: list, batch: list):
    """
    claude CLI로 배치 처리 후 태그 리스트 반환.
    실패 시 None 반환 → 호출부에서 null 유지 처리.
    """
    prompt = build_prompt(examples, batch)

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
        raw = result.stdout.strip()

        # ```json ... ``` 래퍼 제거 후 배열 파싱
        raw_clean = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
        match = re.search(r"\[.*?\]", raw_clean, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            if len(parsed) == len(batch):
                return parsed
            else:
                print(f"  [경고] 응답 길이 불일치: 기대 {len(batch)}, 실제 {len(parsed)}", file=sys.stderr)
                # 길이가 맞지 않으면 None 반환 → null 유지
                return None

        print(f"  [경고] JSON 파싱 실패. 원본:\n{raw[:300]}", file=sys.stderr)
        return None

    except subprocess.TimeoutExpired:
        print("  [경고] 타임아웃 — 해당 배치는 null 유지, 다음 실행 시 재처리됩니다.", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"  [경고] JSON 디코딩 오류: {e} — null 유지", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="수기 metasource 자동 생성")
    parser.add_argument("--reset", action="store_true", help="모든 metasource를 null로 초기화")
    parser.add_argument("--dry-run", action="store_true", help="첫 배치만 미리보기 (저장 안 함)")
    parser.add_argument("--batch", type=int, default=20, help="배치 크기 (기본: 20)")
    parser.add_argument("--examples", type=int, default=10, help="few-shot 예시 수 (기본: 10)")
    parser.add_argument("--status", action="store_true", help="현재 처리 현황만 출력")
    args = parser.parse_args()

    data = load_data()

    if args.status:
        print_status(data)
        return

    if args.reset:
        data = reset_all(data)
        save_data(data)
        print("초기화 완료. JSON 파일에서 20개 이상 metasource를 직접 입력 후 실행하세요.")
        return

    # 현황 출력
    print_status(data)
    print()

    # few-shot 예시 수집 (null이 아닌 항목)
    examples = get_seed_examples(data, max_examples=args.examples)
    if len(examples) < 5:
        print(f"[오류] few-shot 예시가 너무 적습니다 ({len(examples)}개).")
        print("먼저 all_reviews.json에서 metasource를 20개 이상 직접 입력해주세요.")
        return

    print(f"Few-shot 예시 {len(examples)}개:")
    for ex in examples:
        print(f"  no.{ex.get('no','?'):4d} | {ex['title'][:40]} => {ex['summary']['metasource']}")
    print()

    # 처리 대상: metasource가 null인 항목만
    to_process = [
        i for i, item in enumerate(data)
        if item.get("summary", {}).get("metasource") is None
    ]
    total = len(to_process)
    if total == 0:
        print("처리할 항목이 없습니다. 모든 수기가 처리되었습니다.")
        return

    print(f"처리 시작: {total}개 (null 항목)\n")

    processed = 0
    skipped = 0
    for batch_start in range(0, total, args.batch):
        batch_indices = to_process[batch_start: batch_start + args.batch]
        batch_items = [data[i] for i in batch_indices]

        batch_num = batch_start // args.batch + 1
        total_batches = (total + args.batch - 1) // args.batch
        nos = [data[i].get('no', i+1) for i in batch_indices]
        print(f"배치 {batch_num}/{total_batches}  no.{nos[0]}~{nos[-1]} ({len(batch_items)}개)...", end=" ", flush=True)

        tags = extract_batch(examples, batch_items)

        if tags is None:
            # 실패 → null 유지, 저장 안 함
            skipped += len(batch_items)
            print(f"실패 — null 유지. (누적 실패: {skipped}개)")
            continue

        # 성공 → 결과 저장
        for idx, tag in zip(batch_indices, tags):
            data[idx]["summary"]["metasource"] = tag
            processed += 1

        print(f"완료. 처리: {processed}/{total}")

        if not args.dry_run:
            save_data(data)

        if args.dry_run:
            print("\n[dry-run 결과]")
            for idx, tag in zip(batch_indices, tags):
                print(f"  no.{data[idx].get('no','?'):4d} | {data[idx]['title'][:45]}")
                print(f"         → {tag}")
            print("\nOK면 --dry-run 없이 다시 실행하세요.")
            return

    print(f"\n완료! 처리: {processed}개 / 실패(null 유지): {skipped}개")
    if skipped > 0:
        print("재실행하면 실패한 항목부터 이어서 처리됩니다.")


if __name__ == "__main__":
    main()
