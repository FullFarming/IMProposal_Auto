"""
CLI 진입점 — 3가지 모드로 실행 가능:

  1. generate  : 입력 JSON → 8단계 파이프라인 → 슬라이드 JSON 생성
  2. export    : 기존 슬라이드 JSON → .pptx 또는 .html 내보내기
  3. run       : generate + export 한번에 (기본)

Usage:
  # 전체 파이프라인 + PPTX 내보내기 (기본)
  python -m core.cli --input data/sample_input/sample_asset.json

  # PPTX만 내보내기
  python -m core.cli export --assembled output/test_run/assembled_proposal.json --format pptx

  # HTML만 내보내기
  python -m core.cli export --assembled output/test_run/assembled_proposal.json --format html

  # 파이프라인 실행 후 두 형식 모두 내보내기
  python -m core.cli --input data/sample_input/sample_asset.json --export pptx html
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import Settings
from core.orchestrator import ProposalOrchestrator
from core.slide_exporter import SlideExporter
from core.html_exporter import HTMLExporter


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


# ── export 서브커맨드 ──────────────────────────────────────────

def cmd_export(args: argparse.Namespace) -> None:
    """기존 assembled_proposal.json 또는 final_slides.json → 슬라이드 파일."""
    assembled = Path(args.assembled) if getattr(args, "assembled", None) else None
    slides = Path(args.slides) if getattr(args, "slides", None) else None
    fmt = args.format.lower()
    out_dir = Path(getattr(args, "output", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    if assembled and not assembled.exists():
        print(f"오류: 파일 없음 — {assembled}")
        sys.exit(1)
    if slides and not slides.exists():
        print(f"오류: 파일 없음 — {slides}")
        sys.exit(1)

    source = assembled or slides
    use_assembled = bool(assembled)

    if fmt in ("pptx", "both", "all"):
        pptx_path = out_dir / "proposal.pptx"
        exporter = SlideExporter()
        if use_assembled:
            exporter.export_from_assembled(source, pptx_path)
        else:
            exporter.export_from_slides(source, pptx_path)
        print(f"PPTX 생성 완료: {pptx_path.resolve()}")

    if fmt in ("html", "both", "all"):
        html_path = out_dir / "proposal.html"
        exporter = HTMLExporter()
        if use_assembled:
            exporter.export_from_assembled(source, html_path)
        else:
            exporter.export_from_slides(source, html_path)
        print(f"HTML 생성 완료: {html_path.resolve()}")
        print("  → 브라우저에서 열고 Ctrl+P → PDF 저장")


# ── generate 서브커맨드 ────────────────────────────────────────

async def cmd_generate(args: argparse.Namespace) -> None:
    """입력 JSON → 파이프라인 실행 → 슬라이드 JSON 저장."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"오류: 입력 파일 없음 — {input_path}")
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        input_data = json.load(f)

    settings = Settings.from_env()
    if getattr(args, "model", None):
        settings.model = args.model

    orchestrator = ProposalOrchestrator(settings)
    result = await orchestrator.run(input_data)
    out_dir = orchestrator.save_output(getattr(args, "output", "output"))

    _print_pipeline_summary(result, out_dir)
    return result, out_dir


# ── run (generate + export) ────────────────────────────────────

async def cmd_run(args: argparse.Namespace) -> None:
    """전체 파이프라인 실행 후 슬라이드 파일 내보내기."""
    result, out_dir = await cmd_generate(args)

    export_formats = getattr(args, "export", ["pptx"])
    if not export_formats:
        export_formats = ["pptx"]

    assembled_path = out_dir / "assembled_proposal.json"

    print("\n내보내기 시작...")

    if "pptx" in export_formats:
        pptx_path = out_dir / "proposal.pptx"
        SlideExporter().export_from_assembled(assembled_path, pptx_path)
        print(f"  PPTX: {pptx_path.resolve()}")

    if "html" in export_formats:
        html_path = out_dir / "proposal.html"
        HTMLExporter().export_from_assembled(assembled_path, html_path)
        print(f"  HTML: {html_path.resolve()}")
        print("         (브라우저에서 열고 Ctrl+P → PDF 저장)")

    print("\n완료.")


# ── 요약 출력 ─────────────────────────────────────────────────

def _print_pipeline_summary(result, out_dir: Path) -> None:
    print("\n" + "=" * 60)
    print("PROPOSAL GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Total slides: {len(result.final_slide_blocks)}")

    if result.assembled_proposal:
        print("\n  Section breakdown:")
        for section in result.section_order:
            sid = section["section_id"]
            count = len(result.assembled_proposal.get(sid, []))
            marker = "  " if count > 0 else "!!"
            print(f"  {marker} {section['section_name']}: {count} slides")

    if result.qa_result:
        print(f"\n  QA score:           {result.qa_result.overall_score}/100")
        print(f"  Narrative coherence:{result.qa_result.narrative_coherence_score}/100")
        print(f"  Recommendation:     {result.qa_result.final_recommendation}")
        if result.qa_result.critical_issues:
            print(f"  Critical issues:    {len(result.qa_result.critical_issues)}")

    if result.all_human_validation:
        print(f"\n  Human validation required:")
        for item in result.all_human_validation[:8]:
            print(f"    - {item}")
        if len(result.all_human_validation) > 8:
            print(f"    ... and {len(result.all_human_validation) - 8} more")

    print(f"\n  Output: {out_dir.resolve()}")
    print(f"    proposal_output.json      full pipeline result")
    print(f"    final_slides.json         ordered slide blocks")
    print(f"    assembled_proposal.json   section-grouped slides")
    print(f"    human_review_items.json   items needing review")
    print("=" * 60)


# ── 인수 파서 ─────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="상업용 부동산 매각 자문 제안서 자동 생성 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 전체 실행 (파이프라인 + PPTX 생성)
  python -m core.cli --input data/sample_input/sample_asset.json

  # 전체 실행 + HTML도 함께
  python -m core.cli --input data/sample_input/sample_asset.json --export pptx html

  # 기존 결과에서 PPTX만 내보내기
  python -m core.cli export --assembled output/test_run/assembled_proposal.json --format pptx

  # 기존 결과에서 HTML만 내보내기
  python -m core.cli export --assembled output/test_run/assembled_proposal.json --format html
        """,
    )

    subparsers = parser.add_subparsers(dest="command")

    # ── export 서브커맨드
    ep = subparsers.add_parser("export", help="기존 JSON 결과를 PPTX/HTML로 내보내기")
    src = ep.add_mutually_exclusive_group(required=True)
    src.add_argument("--assembled", help="assembled_proposal.json 경로 (섹션 그룹)")
    src.add_argument("--slides", help="final_slides.json 경로 (평탄 리스트)")
    ep.add_argument("--format", choices=["pptx", "html", "both"], default="pptx")
    ep.add_argument("--output", "-o", default="output", help="출력 디렉터리")

    # ── 기본 (run) 인수
    parser.add_argument("--input", "-i", help="입력 JSON 파일 경로")
    parser.add_argument("--output", "-o", default="output", help="출력 디렉터리")
    parser.add_argument("--model", default=None, help="Anthropic 모델 ID")
    parser.add_argument(
        "--export",
        nargs="+",
        choices=["pptx", "html"],
        default=["pptx"],
        help="내보낼 형식 (기본: pptx). 여러 개 가능: --export pptx html",
    )
    parser.add_argument("--verbose", "-v", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(getattr(args, "verbose", False))

    if args.command == "export":
        cmd_export(args)
    elif getattr(args, "input", None):
        asyncio.run(cmd_run(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
