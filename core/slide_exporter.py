"""
SlideExporter — final_slides.json → .pptx (PowerPoint) 변환기.

회사 제안서 템플릿 스타일을 코드로 재현:
- 다크 네이비 섹션 헤더
- 결론형 제목 (대형 + 굵게)
- 핵심 메시지 1줄 헤드라인
- 불릿 본문 (최대 5개)
- 근거 박스 (Evidence points)
- 시각화 제안 배너
- 발표자 메모

섹션별 레이아웃 자동 선택:
- asset_understanding  → factsheet 스타일 (2-column)
- market_context       → chart-ready 스타일 (wide headline)
- pricing_logic        → valuation bridge 스타일 (table hint)
- buyer_strategy       → matrix 스타일
- sale_strategy        → framework 스타일
- execution_plan       → timeline 스타일
- default             → standard headline + bullets
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt, Emu

# ── 브랜드 컬러 ──────────────────────────────────────────────
NAVY    = RGBColor(0x1B, 0x2A, 0x4A)   # 다크 네이비 (주 색상)
BLUE    = RGBColor(0x1F, 0x5C, 0x99)   # 미디엄 블루
LIGHT   = RGBColor(0xE8, 0xF0, 0xF8)   # 연한 배경
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
GRAY    = RGBColor(0x66, 0x66, 0x66)
LGRAY   = RGBColor(0xCC, 0xCC, 0xCC)
ACCENT  = RGBColor(0xE8, 0x6B, 0x1A)   # 강조 오렌지

# ── 슬라이드 크기 (16:9 와이드) ──────────────────────────────
SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

# ── 섹션 이름 한글 매핑 ──────────────────────────────────────
SECTION_KO = {
    "cover":              "표지",
    "credentials":        "Why Us",
    "asset_understanding":"자산 이해",
    "market_context":     "시장 분석",
    "pricing_logic":      "가치평가",
    "buyer_strategy":     "매수자 전략",
    "sale_strategy":      "매각 전략",
    "execution_plan":     "실행 계획",
    "track_record":       "실적 / 팀 / 수수료",
    "unassigned":         "기타",
}


# ── 헬퍼 ─────────────────────────────────────────────────────

def _add_rect(slide, left, top, width, height, fill_rgb, border_rgb=None):
    from pptx.util import Emu
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        int(left), int(top), int(width), int(height),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_rgb
    shape.line.fill.background() if border_rgb is None else None
    if border_rgb:
        shape.line.color.rgb = border_rgb
        shape.line.width = Pt(0.5)
    return shape


def _add_textbox(slide, left, top, width, height, text, font_size,
                 bold=False, color=None, align=PP_ALIGN.LEFT, wrap=True):
    txBox = slide.shapes.add_textbox(
        int(left), int(top), int(width), int(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    return txBox


def _add_bullet_para(tf, text, level=0, font_size=11, color=None, bold=False):
    """텍스트프레임에 불릿 단락 추가."""
    from pptx.util import Pt
    p = tf.add_paragraph()
    p.level = level
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    return p


# ── 레이아웃별 슬라이드 렌더러 ────────────────────────────────

class _SlideRenderer:
    """단일 슬라이드 블록 → pptx slide."""

    def __init__(self, prs: Presentation):
        self.prs = prs
        self.blank_layout = prs.slide_layouts[6]  # blank

    def render(self, block: dict[str, Any], slide_number: int, total: int) -> None:
        section = block.get("proposal_section", "")
        layout_fn = {
            "asset_understanding": self._render_factsheet,
            "pricing_logic":       self._render_valuation,
            "execution_plan":      self._render_timeline,
            "cover":               self._render_cover,
        }.get(section, self._render_standard)

        layout_fn(block, slide_number, total)

    # ── 표준 레이아웃 ─────────────────────────────────────────
    def _render_standard(self, block: dict, num: int, total: int) -> None:
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._draw_common_frame(slide, block, num, total)
        self._draw_bullets_body(slide, block)
        self._draw_evidence_box(slide, block)
        self._draw_visual_banner(slide, block)
        self._set_speaker_note(slide, block)

    # ── factsheet 레이아웃 (2-column) ─────────────────────────
    def _render_factsheet(self, block: dict, num: int, total: int) -> None:
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._draw_common_frame(slide, block, num, total, header_height=Inches(1.5))

        # 왼쪽 컬럼 — 불릿
        bullets = block.get("body_bullets", [])
        left_col = slide.shapes.add_textbox(
            Inches(0.4), Inches(1.8), Inches(6.5), Inches(4.5)
        )
        tf = left_col.text_frame
        tf.word_wrap = True
        for i, b in enumerate(bullets[:5]):
            _add_bullet_para(tf, f"• {b}", font_size=11,
                              color=NAVY if i == 0 else GRAY, bold=(i == 0))

        # 오른쪽 컬럼 — evidence + visual
        _add_rect(slide, Inches(7.2), Inches(1.8), Inches(5.9), Inches(4.5), LIGHT)
        ev_box = slide.shapes.add_textbox(
            Inches(7.4), Inches(1.9), Inches(5.6), Inches(2.5)
        )
        ev_tf = ev_box.text_frame
        ev_tf.word_wrap = True
        ev_first = ev_tf.paragraphs[0]
        ev_first.runs[0].text if ev_first.runs else None
        ev_run = ev_first.add_run() if not ev_first.runs else ev_first.runs[0]
        ev_run.text = "KEY EVIDENCE"
        ev_run.font.size = Pt(9)
        ev_run.font.bold = True
        ev_run.font.color.rgb = NAVY

        for ev in block.get("evidence_points", [])[:4]:
            _add_bullet_para(ev_tf, f"  — {ev}", font_size=9.5, color=GRAY)

        visual_text = block.get("recommended_visual", "")
        if visual_text:
            _add_textbox(
                slide, Inches(7.4), Inches(4.5), Inches(5.6), Inches(0.6),
                f"[VISUAL] {visual_text}",
                font_size=9, color=ACCENT, bold=True,
            )

        self._set_speaker_note(slide, block)

    # ── 가치평가 레이아웃 ─────────────────────────────────────
    def _render_valuation(self, block: dict, num: int, total: int) -> None:
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._draw_common_frame(slide, block, num, total)

        bullets = block.get("body_bullets", [])
        ev = block.get("evidence_points", [])

        # 불릿 좌측
        body_box = slide.shapes.add_textbox(
            Inches(0.4), Inches(1.8), Inches(7.5), Inches(4.0)
        )
        tf = body_box.text_frame
        tf.word_wrap = True
        for i, b in enumerate(bullets[:5]):
            _add_bullet_para(tf, f"• {b}", font_size=11.5,
                              color=NAVY if i == 0 else GRAY, bold=(i == 0))

        # 우측 가격 박스
        _add_rect(slide, Inches(8.2), Inches(1.9), Inches(4.9), Inches(3.8), NAVY)
        price_box = slide.shapes.add_textbox(
            Inches(8.4), Inches(2.0), Inches(4.6), Inches(3.5)
        )
        ptf = price_box.text_frame
        ptf.word_wrap = True
        p0 = ptf.paragraphs[0]
        r0 = p0.add_run()
        r0.text = "VALUATION REFERENCE"
        r0.font.size = Pt(9)
        r0.font.bold = True
        r0.font.color.rgb = LIGHT

        for e in ev[:5]:
            _add_bullet_para(ptf, f"  {e}", font_size=10, color=WHITE)

        visual_text = block.get("recommended_visual", "")
        if visual_text:
            _add_textbox(
                slide, Inches(0.4), Inches(6.2), Inches(12.5), Inches(0.6),
                f"[CHART RECOMMENDATION] {visual_text}",
                font_size=9, color=ACCENT, bold=True,
            )

        self._set_speaker_note(slide, block)

    # ── 타임라인/실행 레이아웃 ────────────────────────────────
    def _render_timeline(self, block: dict, num: int, total: int) -> None:
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._draw_common_frame(slide, block, num, total)

        bullets = block.get("body_bullets", [])
        phases = bullets[:5]

        # 타임라인 레일
        n = len(phases)
        if n == 0:
            self._set_speaker_note(slide, block)
            return

        rail_top = Inches(3.5)
        rail_left = Inches(0.5)
        rail_width = Inches(12.3)
        rail_h = Inches(0.08)

        _add_rect(slide, rail_left, rail_top, rail_width, rail_h, BLUE)

        step_w = rail_width / max(n, 1)
        for i, phase in enumerate(phases):
            cx = rail_left + step_w * i + step_w / 2

            # 노드 원
            r = Inches(0.18)
            node = slide.shapes.add_shape(
                9,  # oval
                int(cx - r), int(rail_top - r + rail_h / 2),
                int(r * 2), int(r * 2),
            )
            node.fill.solid()
            node.fill.fore_color.rgb = NAVY
            node.line.fill.background()

            # 단계 레이블 (위/아래 교차)
            label_top = (rail_top - Inches(1.2)) if i % 2 == 0 else (rail_top + Inches(0.3))
            _add_textbox(
                slide,
                cx - step_w / 2 + Inches(0.05),
                label_top,
                step_w - Inches(0.1),
                Inches(0.9),
                phase,
                font_size=9.5,
                color=NAVY,
                align=PP_ALIGN.CENTER,
            )

        # 근거 박스
        ev = block.get("evidence_points", [])
        if ev:
            _add_rect(slide, Inches(0.4), Inches(4.8), Inches(12.5), Inches(1.8), LIGHT)
            ev_box = slide.shapes.add_textbox(
                Inches(0.6), Inches(4.9), Inches(12.0), Inches(1.5)
            )
            etf = ev_box.text_frame
            etf.word_wrap = True
            for e in ev[:3]:
                _add_bullet_para(etf, f"• {e}", font_size=10, color=GRAY)

        self._set_speaker_note(slide, block)

    # ── 표지 레이아웃 ─────────────────────────────────────────
    def _render_cover(self, block: dict, num: int, total: int) -> None:
        slide = self.prs.slides.add_slide(self.blank_layout)

        # 전체 네이비 배경
        _add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, NAVY)

        # 파란 액센트 바
        _add_rect(slide, 0, Inches(4.8), SLIDE_W, Inches(0.08), ACCENT)

        # 제목
        _add_textbox(
            slide, Inches(0.8), Inches(1.5), Inches(11.5), Inches(2.0),
            block.get("slide_title", "Sell-Side Advisory Proposal"),
            font_size=36, bold=True, color=WHITE, align=PP_ALIGN.LEFT,
        )

        # 서브타이틀 (헤드라인)
        _add_textbox(
            slide, Inches(0.8), Inches(3.6), Inches(11.5), Inches(0.9),
            block.get("headline", ""),
            font_size=16, bold=False, color=LIGHT, align=PP_ALIGN.LEFT,
        )

        # 불릿 (커버 하단)
        bullets = block.get("body_bullets", [])
        if bullets:
            bl_box = slide.shapes.add_textbox(
                Inches(0.8), Inches(5.0), Inches(11.5), Inches(2.0)
            )
            bltf = bl_box.text_frame
            bltf.word_wrap = True
            for b in bullets[:4]:
                _add_bullet_para(bltf, f"  {b}", font_size=12, color=LIGHT)

        # 슬라이드 번호
        _add_textbox(
            slide, Inches(12.7), Inches(7.1), Inches(0.5), Inches(0.3),
            f"{num}",
            font_size=9, color=LGRAY, align=PP_ALIGN.RIGHT,
        )

        self._set_speaker_note(slide, block)

    # ── 공통 프레임 (헤더바 + 제목 + 헤드라인 + 슬라이드 번호) ──
    def _draw_common_frame(
        self, slide, block: dict, num: int, total: int,
        header_height: Emu = None,
    ) -> None:
        if header_height is None:
            header_height = Inches(0.55)

        # 상단 네이비 헤더바
        _add_rect(slide, 0, 0, SLIDE_W, header_height, NAVY)

        section = block.get("proposal_section", "")
        section_label = SECTION_KO.get(section, section.replace("_", " ").title())
        _add_textbox(
            slide, Inches(0.3), Inches(0.07), Inches(10), Inches(0.4),
            section_label.upper(),
            font_size=9, bold=True, color=WHITE,
        )

        # 슬라이드 번호
        _add_textbox(
            slide, Inches(12.5), Inches(0.07), Inches(0.7), Inches(0.4),
            f"{num} / {total}",
            font_size=9, color=LGRAY, align=PP_ALIGN.RIGHT,
        )

        # 슬라이드 제목 (결론형)
        title_text = block.get("slide_title", "")
        _add_textbox(
            slide, Inches(0.4), Inches(0.65), Inches(12.5), Inches(0.75),
            title_text,
            font_size=20, bold=True, color=NAVY,
        )

        # 헤드라인 (핵심 메시지 1줄)
        headline_text = block.get("headline", "")
        if headline_text:
            # 헤드라인 배경 라인
            _add_rect(slide, Inches(0.4), Inches(1.45), Inches(12.5), Inches(0.04), BLUE)
            _add_textbox(
                slide, Inches(0.4), Inches(1.5), Inches(12.5), Inches(0.5),
                headline_text,
                font_size=12, bold=False, color=BLUE,
            )

    # ── 본문 불릿 ─────────────────────────────────────────────
    def _draw_bullets_body(self, slide, block: dict) -> None:
        bullets = block.get("body_bullets", [])
        if not bullets:
            return

        body_box = slide.shapes.add_textbox(
            Inches(0.4), Inches(2.15), Inches(12.5), Inches(4.2)
        )
        tf = body_box.text_frame
        tf.word_wrap = True
        for i, b in enumerate(bullets[:5]):
            _add_bullet_para(
                tf, f"• {b}",
                font_size=12,
                color=NAVY if i == 0 else GRAY,
                bold=(i == 0),
            )

    # ── 근거 박스 (Evidence) ──────────────────────────────────
    def _draw_evidence_box(self, slide, block: dict) -> None:
        ev = block.get("evidence_points", [])
        if not ev:
            return

        _add_rect(slide, Inches(0.4), Inches(5.95), Inches(12.5), Inches(1.25), LIGHT)

        ev_label = slide.shapes.add_textbox(
            Inches(0.55), Inches(6.0), Inches(1.5), Inches(0.3)
        )
        ev_label_tf = ev_label.text_frame
        p = ev_label_tf.paragraphs[0]
        r = p.add_run()
        r.text = "EVIDENCE"
        r.font.size = Pt(8)
        r.font.bold = True
        r.font.color.rgb = NAVY

        ev_box = slide.shapes.add_textbox(
            Inches(0.55), Inches(6.3), Inches(12.2), Inches(0.8)
        )
        etf = ev_box.text_frame
        etf.word_wrap = True
        ev_line = " │ ".join(ev[:4])
        _add_bullet_para(etf, ev_line, font_size=9, color=GRAY)

    # ── 시각화 제안 배너 ─────────────────────────────────────
    def _draw_visual_banner(self, slide, block: dict) -> None:
        visual_text = block.get("recommended_visual", "")
        layout_text = block.get("layout_guidance", "")
        if not visual_text:
            return

        note = f"[VISUAL] {visual_text}"
        if layout_text:
            note += f"  |  {layout_text}"

        _add_textbox(
            slide, Inches(0.4), Inches(5.5), Inches(12.5), Inches(0.4),
            note,
            font_size=8.5, color=ACCENT, bold=True,
        )

    # ── 발표자 메모 ───────────────────────────────────────────
    def _set_speaker_note(self, slide, block: dict) -> None:
        note_text = block.get("speaker_note", "")
        template_notes = block.get("template_notes", "")
        full_note = note_text
        if template_notes:
            full_note += f"\n\n[Template notes] {template_notes}"
        if full_note.strip():
            slide.notes_slide.notes_text_frame.text = full_note


# ── 섹션 구분 슬라이드 ─────────────────────────────────────

def _add_section_divider(prs: Presentation, section_id: str, section_name: str) -> None:
    blank = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank)

    _add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, NAVY)
    _add_rect(slide, 0, Inches(3.55), SLIDE_W, Inches(0.08), ACCENT)

    section_num = {
        "cover": "01", "credentials": "02", "asset_understanding": "03",
        "market_context": "04", "pricing_logic": "05", "buyer_strategy": "06",
        "sale_strategy": "07", "execution_plan": "08", "track_record": "09",
    }.get(section_id, "--")

    _add_textbox(
        slide, Inches(0.8), Inches(2.2), Inches(11.5), Inches(1.1),
        section_num,
        font_size=60, bold=True, color=BLUE, align=PP_ALIGN.LEFT,
    )
    _add_textbox(
        slide, Inches(0.8), Inches(3.7), Inches(11.5), Inches(1.2),
        section_name,
        font_size=32, bold=True, color=WHITE, align=PP_ALIGN.LEFT,
    )
    ko = SECTION_KO.get(section_id, "")
    if ko:
        _add_textbox(
            slide, Inches(0.8), Inches(4.9), Inches(11.5), Inches(0.6),
            ko,
            font_size=16, bold=False, color=LIGHT, align=PP_ALIGN.LEFT,
        )


# ── 공개 API ─────────────────────────────────────────────────

class SlideExporter:
    """
    assembled_proposal.json 또는 final_slides.json → .pptx 변환.

    사용법:
        exporter = SlideExporter()
        exporter.export_from_assembled("output/test_run/assembled_proposal.json",
                                        "output/test_run/proposal.pptx")
    """

    SECTION_ORDER = [
        "cover", "credentials", "asset_understanding", "market_context",
        "pricing_logic", "buyer_strategy", "sale_strategy",
        "execution_plan", "track_record",
    ]

    def __init__(self):
        pass

    # ── 조립된 제안서에서 내보내기 ────────────────────────────
    def export_from_assembled(
        self,
        assembled_json_path: str | Path,
        output_path: str | Path,
        add_section_dividers: bool = True,
    ) -> Path:
        """섹션별 grouped JSON → .pptx"""
        with open(assembled_json_path, encoding="utf-8") as f:
            assembled: dict[str, list[dict]] = json.load(f)

        # 전체 슬라이드 수 미리 계산
        total_content_slides = sum(len(v) for v in assembled.values())
        if add_section_dividers:
            non_empty_sections = sum(
                1 for sid in self.SECTION_ORDER
                if assembled.get(sid)
            )
            total_slides = total_content_slides + non_empty_sections
        else:
            total_slides = total_content_slides

        prs = self._create_presentation()
        renderer = _SlideRenderer(prs)
        slide_num = 1

        for section_id in self.SECTION_ORDER:
            blocks = assembled.get(section_id, [])
            if not blocks:
                continue

            section_name = {
                "cover":              "Cover / Mandate Understanding",
                "credentials":        "Why Us / Credentials",
                "asset_understanding":"Asset Understanding",
                "market_context":     "Market Context",
                "pricing_logic":      "Pricing Logic",
                "buyer_strategy":     "Buyer Strategy",
                "sale_strategy":      "Recommended Sale Strategy",
                "execution_plan":     "Execution Plan",
                "track_record":       "Track Record / Team / Fees",
            }.get(section_id, section_id)

            if add_section_dividers:
                _add_section_divider(prs, section_id, section_name)

            for block in blocks:
                block["proposal_section"] = section_id
                renderer.render(block, slide_num, total_slides)
                slide_num += 1

        # "unassigned" 처리
        unassigned = assembled.get("unassigned", [])
        if unassigned:
            if add_section_dividers:
                _add_section_divider(prs, "unassigned", "Additional Slides")
            for block in unassigned:
                renderer.render(block, slide_num, total_slides)
                slide_num += 1

        out_path = Path(output_path)
        prs.save(str(out_path))
        return out_path

    # ── 평탄화된 슬라이드 리스트에서 내보내기 ────────────────
    def export_from_slides(
        self,
        slides_json_path: str | Path,
        output_path: str | Path,
        add_section_dividers: bool = True,
    ) -> Path:
        """final_slides.json (flat list) → .pptx"""
        with open(slides_json_path, encoding="utf-8") as f:
            slides: list[dict] = json.load(f)

        # 섹션별 그룹화
        from collections import defaultdict
        grouped: dict[str, list[dict]] = defaultdict(list)
        for s in slides:
            sec = s.get("proposal_section") or "unassigned"
            grouped[sec].append(s)

        # 임시 파일 경로로 assembled 형식으로 저장 후 재사용
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(dict(grouped), tmp, ensure_ascii=False)
            tmp_path = tmp.name

        return self.export_from_assembled(tmp_path, output_path, add_section_dividers)

    def _create_presentation(self) -> Presentation:
        prs = Presentation()
        prs.slide_width = SLIDE_W
        prs.slide_height = SLIDE_H
        return prs
