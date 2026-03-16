"""
CLI 진입점 — JSON 입력 파일을 받아 6단계 파이프라인을 실행한다.

Usage:
    python -m core.cli --input data/sample_input/sample_asset.json
    python -m core.cli --input data/sample_input/sample_asset.json --output output/my_proposal
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import Settings
from core.orchestrator import ProposalOrchestrator


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="상업용 부동산 매각 자문 제안서 자동 생성 파이프라인"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="입력 JSON 파일 경로",
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="출력 디렉터리 (기본: output/)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Anthropic 모델 ID (기본: claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="디버그 로그 활성화",
    )
    return parser.parse_args()


async def run_pipeline(args: argparse.Namespace) -> None:
    # 입력 파일 로드
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"오류: 입력 파일을 찾을 수 없습니다 — {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    # 설정
    settings = Settings.from_env()
    if args.model:
        settings.model = args.model

    # 오케스트레이터 실행
    orchestrator = ProposalOrchestrator(settings)
    result = await orchestrator.run(input_data)

    # 저장
    out_dir = orchestrator.save_output(args.output)

    # 요약 출력
    print("\n" + "=" * 60)
    print("제안서 자동 생성 완료")
    print("=" * 60)
    print(f"  최종 슬라이드 수: {len(result.final_slide_blocks)}")

    if result.qa_result:
        print(f"  QA 점수: {result.qa_result.overall_score}/100")
        print(f"  QA 판정: {result.qa_result.final_recommendation}")
        if result.qa_result.critical_issues:
            print(f"  주요 이슈: {len(result.qa_result.critical_issues)}건")

    human_items = result.project_understanding.get("human_review_items", [])
    if human_items:
        print(f"\n  ⚠ 수동 검토 필요 항목:")
        for item in human_items:
            print(f"    - {item}")

    print(f"\n  출력 디렉터리: {out_dir.resolve()}")
    print(f"  - proposal_output.json  (전체 결과)")
    print(f"  - final_slides.json     (최종 슬라이드 블록)")
    print("=" * 60)


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
