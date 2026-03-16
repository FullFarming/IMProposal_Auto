"""
HTMLExporter — final_slides.json → 브라우저 프레젠테이션 (PDF 인쇄 가능).

- 16:9 슬라이드 레이아웃
- 네이비/화이트 회사 색상
- 섹션 구분 슬라이드
- 브라우저에서 Ctrl+P → PDF로 저장하면 됨
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SECTION_ORDER = [
    "cover", "credentials", "asset_understanding", "market_context",
    "pricing_logic", "buyer_strategy", "sale_strategy",
    "execution_plan", "track_record",
]

SECTION_NAMES = {
    "cover":               ("01", "Cover / Mandate Understanding", "표지"),
    "credentials":         ("02", "Why Us / Credentials", "자격 및 전문성"),
    "asset_understanding": ("03", "Asset Understanding", "자산 이해"),
    "market_context":      ("04", "Market Context", "시장 분석"),
    "pricing_logic":       ("05", "Pricing Logic", "가치평가"),
    "buyer_strategy":      ("06", "Buyer Strategy", "매수자 전략"),
    "sale_strategy":       ("07", "Recommended Sale Strategy", "매각 전략"),
    "execution_plan":      ("08", "Execution Plan", "실행 계획"),
    "track_record":        ("09", "Track Record / Team / Fees", "실적 / 팀 / 수수료"),
    "unassigned":          ("--", "Additional Slides", "기타"),
}


CSS = """
:root {
  --navy:  #1B2A4A;
  --blue:  #1F5C99;
  --light: #E8F0F8;
  --white: #FFFFFF;
  --gray:  #555555;
  --lgray: #AAAAAA;
  --accent:#E86B1A;
  --slide-w: 1280px;
  --slide-h: 720px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #2a2a2a;
  font-family: 'Segoe UI', 'Noto Sans KR', Arial, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px 20px;
  gap: 24px;
}

/* ─── Slide wrapper ─── */
.slide {
  width: var(--slide-w);
  height: var(--slide-h);
  background: var(--white);
  position: relative;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  page-break-after: always;
}

/* ─── Section divider ─── */
.slide.divider {
  background: var(--navy);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 60px 80px;
}
.divider .sec-num {
  font-size: 72px;
  font-weight: 800;
  color: var(--blue);
  line-height: 1;
}
.divider .sec-accent-bar {
  width: 100%;
  height: 4px;
  background: var(--accent);
  margin: 18px 0;
}
.divider .sec-name-en {
  font-size: 34px;
  font-weight: 700;
  color: var(--white);
}
.divider .sec-name-ko {
  font-size: 18px;
  font-weight: 400;
  color: var(--light);
  margin-top: 8px;
}

/* ─── Standard slide ─── */
.slide .header-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 44px;
  background: var(--navy);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.header-bar .section-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--white);
  letter-spacing: 1.5px;
  text-transform: uppercase;
}
.header-bar .slide-num {
  font-size: 11px;
  color: var(--lgray);
}

.slide .slide-title {
  position: absolute;
  top: 52px; left: 30px; right: 30px;
  font-size: 22px;
  font-weight: 700;
  color: var(--navy);
  line-height: 1.3;
}

.slide .headline-bar {
  position: absolute;
  top: 110px; left: 30px; right: 30px;
  height: 2px;
  background: var(--blue);
}
.slide .headline-text {
  position: absolute;
  top: 116px; left: 30px; right: 30px;
  font-size: 13px;
  color: var(--blue);
  font-weight: 500;
}

.slide .body-area {
  position: absolute;
  top: 148px; left: 30px; right: 30px;
  bottom: 120px;
  overflow: hidden;
}
.body-area ul {
  list-style: none;
  padding: 0;
}
.body-area ul li {
  padding: 6px 0 6px 18px;
  font-size: 13px;
  color: var(--gray);
  line-height: 1.5;
  border-left: 3px solid transparent;
}
.body-area ul li:first-child {
  color: var(--navy);
  font-weight: 600;
  font-size: 14px;
  border-left-color: var(--accent);
}

/* Evidence box */
.slide .evidence-bar {
  position: absolute;
  bottom: 60px; left: 30px; right: 30px;
  background: var(--light);
  padding: 8px 14px;
  border-radius: 2px;
  font-size: 10px;
  color: var(--gray);
  line-height: 1.5;
}
.evidence-bar .ev-label {
  font-size: 9px;
  font-weight: 700;
  color: var(--navy);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 3px;
}

/* Visual banner */
.slide .visual-banner {
  position: absolute;
  bottom: 12px; left: 30px; right: 30px;
  font-size: 10px;
  font-weight: 700;
  color: var(--accent);
}

/* 2-column layout (factsheet) */
.slide .two-col {
  position: absolute;
  top: 148px; left: 30px; right: 30px;
  bottom: 120px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.two-col .col-right-box {
  background: var(--light);
  padding: 14px;
  border-radius: 2px;
}
.col-right-box .box-label {
  font-size: 9px;
  font-weight: 700;
  color: var(--navy);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}
.col-right-box ul li { border-left: none !important; }

/* Valuation right box */
.slide .val-box {
  position: absolute;
  top: 148px; right: 30px;
  width: 380px;
  bottom: 120px;
  background: var(--navy);
  padding: 16px;
  border-radius: 2px;
}
.val-box .box-label {
  font-size: 9px;
  font-weight: 700;
  color: var(--light);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}
.val-box ul li { color: var(--white) !important; border-left: none !important; }
.slide .body-area.with-val { right: 430px; }

/* Timeline */
.slide .timeline-area {
  position: absolute;
  top: 148px; left: 30px; right: 30px;
  height: 200px;
}
.timeline-rail {
  position: absolute;
  top: 90px;
  left: 0; right: 0;
  height: 4px;
  background: var(--blue);
}
.timeline-steps {
  display: flex;
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  align-items: center;
  justify-content: space-around;
}
.timeline-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  font-size: 11px;
  color: var(--navy);
  font-weight: 500;
  text-align: center;
}
.timeline-step .node {
  width: 18px; height: 18px;
  background: var(--navy);
  border-radius: 50%;
  margin-bottom: 6px;
  flex-shrink: 0;
}
.slide .timeline-ev {
  position: absolute;
  bottom: 60px; left: 30px; right: 30px;
}

/* Cover */
.slide.cover-slide {
  background: var(--navy);
}
.cover-slide .accent-bar {
  position: absolute;
  top: 48%;
  left: 0; right: 0;
  height: 4px;
  background: var(--accent);
}
.cover-slide .cover-title {
  position: absolute;
  top: 15%; left: 60px; right: 60px;
  font-size: 40px;
  font-weight: 800;
  color: var(--white);
  line-height: 1.25;
}
.cover-slide .cover-sub {
  position: absolute;
  top: 40%; left: 60px; right: 60px;
  font-size: 18px;
  color: var(--light);
}
.cover-slide .cover-bullets {
  position: absolute;
  top: 52%; left: 60px; right: 60px;
  font-size: 14px;
  color: var(--light);
  line-height: 2;
}

/* Print styles */
@media print {
  body { background: white; padding: 0; gap: 0; }
  .slide {
    box-shadow: none;
    page-break-after: always;
    width: 100vw;
    height: 56.25vw; /* 16:9 */
  }
}
"""


def _bullets_html(bullets: list[str], max_n: int = 5) -> str:
    items = "".join(f"<li>{b}</li>" for b in bullets[:max_n])
    return f"<ul>{items}</ul>"


def _evidence_html(ev: list[str]) -> str:
    if not ev:
        return ""
    joined = " &nbsp;│&nbsp; ".join(ev[:4])
    return (
        f'<div class="evidence-bar">'
        f'<div class="ev-label">Evidence</div>{joined}'
        f"</div>"
    )


def _visual_html(visual: str) -> str:
    if not visual:
        return ""
    return f'<div class="visual-banner">[ VISUAL ] {visual}</div>'


def _section_label_html(section_id: str, num: int, total: int) -> str:
    _, en, ko = SECTION_NAMES.get(section_id, ("--", section_id, ""))
    label = ko or en
    return (
        f'<div class="header-bar">'
        f'<span class="section-label">{label}</span>'
        f'<span class="slide-num">{num} / {total}</span>'
        f"</div>"
    )


def _render_standard(block: dict, num: int, total: int) -> str:
    sid = block.get("proposal_section", "")
    title = block.get("slide_title", "")
    headline = block.get("headline", "")
    bullets = block.get("body_bullets", [])
    ev = block.get("evidence_points", [])
    visual = block.get("recommended_visual", "")

    headline_html = ""
    if headline:
        headline_html = (
            '<div class="headline-bar"></div>'
            f'<div class="headline-text">{headline}</div>'
        )

    return (
        f'<div class="slide">'
        f"{_section_label_html(sid, num, total)}"
        f'<div class="slide-title">{title}</div>'
        f"{headline_html}"
        f'<div class="body-area">{_bullets_html(bullets)}</div>'
        f"{_evidence_html(ev)}"
        f"{_visual_html(visual)}"
        f"</div>"
    )


def _render_factsheet(block: dict, num: int, total: int) -> str:
    sid = block.get("proposal_section", "")
    title = block.get("slide_title", "")
    headline = block.get("headline", "")
    bullets = block.get("body_bullets", [])
    ev = block.get("evidence_points", [])
    visual = block.get("recommended_visual", "")

    left_items = "".join(f"<li>{b}</li>" for b in bullets[:5])
    ev_items = "".join(f"<li>{e}</li>" for e in ev[:4])
    visual_note = f'<div style="font-size:10px;color:#E86B1A;font-weight:700;margin-top:10px;">[VISUAL] {visual}</div>' if visual else ""

    return (
        f'<div class="slide">'
        f"{_section_label_html(sid, num, total)}"
        f'<div class="slide-title">{title}</div>'
        f'<div class="headline-bar"></div>'
        f'<div class="headline-text">{headline}</div>'
        f'<div class="two-col">'
        f"  <ul>{left_items}</ul>"
        f'  <div class="col-right-box">'
        f'    <div class="box-label">Key Evidence</div>'
        f"    <ul>{ev_items}</ul>"
        f"    {visual_note}"
        f"  </div>"
        f"</div>"
        f"</div>"
    )


def _render_valuation(block: dict, num: int, total: int) -> str:
    sid = block.get("proposal_section", "")
    title = block.get("slide_title", "")
    headline = block.get("headline", "")
    bullets = block.get("body_bullets", [])
    ev = block.get("evidence_points", [])
    visual = block.get("recommended_visual", "")

    b_items = "".join(f"<li>{b}</li>" for b in bullets[:5])
    ev_items = "".join(f"<li>{e}</li>" for e in ev[:4])
    visual_note = f'<div class="visual-banner">[CHART] {visual}</div>' if visual else ""

    return (
        f'<div class="slide">'
        f"{_section_label_html(sid, num, total)}"
        f'<div class="slide-title">{title}</div>'
        f'<div class="headline-bar"></div>'
        f'<div class="headline-text">{headline}</div>'
        f'<div class="body-area with-val"><ul>{b_items}</ul></div>'
        f'<div class="val-box">'
        f'  <div class="box-label">Valuation Reference</div>'
        f"  <ul>{ev_items}</ul>"
        f"</div>"
        f"{_evidence_html([])}"
        f"{visual_note}"
        f"</div>"
    )


def _render_timeline(block: dict, num: int, total: int) -> str:
    sid = block.get("proposal_section", "")
    title = block.get("slide_title", "")
    headline = block.get("headline", "")
    bullets = block.get("body_bullets", [])
    ev = block.get("evidence_points", [])

    steps_html = ""
    for b in bullets[:6]:
        steps_html += (
            f'<div class="timeline-step">'
            f'<div class="node"></div>'
            f"{b}"
            f"</div>"
        )

    ev_html = _evidence_html(ev) if ev else ""

    return (
        f'<div class="slide">'
        f"{_section_label_html(sid, num, total)}"
        f'<div class="slide-title">{title}</div>'
        f'<div class="headline-bar"></div>'
        f'<div class="headline-text">{headline}</div>'
        f'<div class="timeline-area">'
        f'  <div class="timeline-rail"></div>'
        f'  <div class="timeline-steps">{steps_html}</div>'
        f"</div>"
        f"{ev_html}"
        f"</div>"
    )


def _render_cover(block: dict, **_) -> str:
    title = block.get("slide_title", "Sell-Side Advisory Proposal")
    headline = block.get("headline", "")
    bullets = block.get("body_bullets", [])
    b_html = "".join(f"• {b}<br>" for b in bullets[:4])
    return (
        f'<div class="slide cover-slide">'
        f'<div class="cover-title">{title}</div>'
        f'<div class="cover-sub">{headline}</div>'
        f'<div class="accent-bar"></div>'
        f'<div class="cover-bullets">{b_html}</div>'
        f"</div>"
    )


def _render_divider(section_id: str) -> str:
    num, en, ko = SECTION_NAMES.get(section_id, ("--", section_id, ""))
    return (
        f'<div class="slide divider">'
        f'<div class="sec-num">{num}</div>'
        f'<div class="sec-accent-bar"></div>'
        f'<div class="sec-name-en">{en}</div>'
        f'<div class="sec-name-ko">{ko}</div>'
        f"</div>"
    )


def _pick_renderer(block: dict):
    sid = block.get("proposal_section", "")
    return {
        "cover":               _render_cover,
        "asset_understanding": _render_factsheet,
        "pricing_logic":       _render_valuation,
        "execution_plan":      _render_timeline,
    }.get(sid, _render_standard)


class HTMLExporter:
    """assembled_proposal.json or final_slides.json → HTML presentation."""

    def export_from_assembled(
        self,
        assembled_json_path: str | Path,
        output_path: str | Path,
        add_section_dividers: bool = True,
    ) -> Path:
        with open(assembled_json_path, encoding="utf-8") as f:
            assembled: dict[str, list[dict]] = json.load(f)

        total_slides = sum(len(v) for v in assembled.values())

        slides_html: list[str] = []
        slide_num = 1

        for sid in SECTION_ORDER:
            blocks = assembled.get(sid, [])
            if not blocks:
                continue
            if add_section_dividers:
                slides_html.append(_render_divider(sid))
            for block in blocks:
                block["proposal_section"] = sid
                renderer = _pick_renderer(block)
                slides_html.append(renderer(block, slide_num, total_slides))
                slide_num += 1

        for block in assembled.get("unassigned", []):
            renderer = _pick_renderer(block)
            slides_html.append(renderer(block, slide_num, total_slides))
            slide_num += 1

        html = self._wrap_html("\n".join(slides_html))

        out = Path(output_path)
        out.write_text(html, encoding="utf-8")
        return out

    def export_from_slides(
        self,
        slides_json_path: str | Path,
        output_path: str | Path,
        add_section_dividers: bool = True,
    ) -> Path:
        with open(slides_json_path, encoding="utf-8") as f:
            slides: list[dict] = json.load(f)

        from collections import defaultdict
        grouped: dict[str, list[dict]] = defaultdict(list)
        for s in slides:
            sec = s.get("proposal_section") or "unassigned"
            grouped[sec].append(s)

        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(dict(grouped), tmp, ensure_ascii=False)
            tmp_path = tmp.name

        return self.export_from_assembled(tmp_path, output_path, add_section_dividers)

    def _wrap_html(self, body: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Sell-Side Advisory Proposal</title>
  <style>{CSS}</style>
</head>
<body>
{body}
<script>
// 키보드 화살표로 슬라이드 스크롤
const slides = document.querySelectorAll('.slide');
let cur = 0;
document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {{
    cur = Math.min(cur + 1, slides.length - 1);
  }} else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {{
    cur = Math.max(cur - 1, 0);
  }}
  slides[cur].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
}});
</script>
</body>
</html>"""
