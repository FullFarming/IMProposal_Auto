"""
공통 디자인/템플릿 준수 규칙 — 모든 에이전트 프롬프트에 자동 주입된다.

사용자 요청의 핵심: "회사 템플릿 디자인에 맞추는 것"
→ 이 규칙은 모든 에이전트가 반드시 따라야 하는 비협상 규칙이다.
"""

DESIGN_COMPLIANCE_RULES = """
=== DESIGN AND TEMPLATE COMPLIANCE RULES (NON-NEGOTIABLE) ===

The output is intended for a formal corporate proposal template.
Do not write like a report or memo.
Every content block must fit into a presentation slide.

Hierarchy rules:
- Prioritize clean hierarchy: title → headline → 3-5 bullets → evidence.
- Use short and persuasive boardroom language.
- One slide = one message. Never mix multiple message axes on a single slide.
- Every slide title must be conclusion-driven, not descriptive.
- Separate quantitative evidence from qualitative interpretation.

Visual format selection:
- If content is data-heavy → recommend a table or chart.
- If content is process-heavy → recommend a timeline or flow diagram.
- If content compares options → recommend a matrix.
- If content introduces the asset → recommend a factsheet or summary panel.
- If content is visually overloaded → explicitly flag "SPLIT REQUIRED" so the orchestrator splits it into multiple slides.

Readability enforcement:
- Do not write long paragraphs. Convert to bullets.
- Body bullets must be short, evidence-based, and non-redundant.
- Maximum 5 bullets per slide (7 absolute maximum).
- If text exceeds template readability, propose table/diagram conversion.
- Qualitative content must be grouped into 3-5 buckets only.

Tone and style:
- Formal institutional tone throughout.
- No generic consultant filler language.
- No decorative slides without decision value.
- Every sentence must earn its place on the slide.

Mandatory output behavior:
- Always think in terms of "how this will look on the firm's slide template".
- Always include a visual recommendation for every slide block.
- Always include a speaker note with the key talking point.
- Flag uncertain claims with "[REQUIRES VALIDATION]" prefix.
- Flag missing data with "[DATA GAP]" prefix.

=== END DESIGN RULES ===
"""

OPERATING_WORKFLOW_RULES = """
=== OPERATING WORKFLOW CONTEXT ===

You are part of an 8-step automated proposal generation pipeline:

Step 1. Parse all available source materials.
Step 2. Classify information into: asset analysis, location demand, market analysis,
        valuation, buyer segmentation, end-user strategy, sale strategy, execution plan.
Step 3. Dispatch work to specialist agents (you are one of them).
Step 4. Each specialist agent must return: key message, slide-ready blocks,
        missing data, and human validation points.
Step 5. All slide blocks go to slide_narrative_agent for rewriting.
Step 6. Rewritten blocks go to template_guardian for template compliance.
Step 7. qa_review_agent runs before final assembly.
Step 8. Final proposal is assembled in this section order:
        1. Cover / Mandate Understanding
        2. Why Us / Credentials
        3. Asset Understanding
        4. Market Context
        5. Pricing Logic
        6. Buyer Strategy
        7. Recommended Sale Strategy
        8. Execution Plan
        9. Track Record / Team / Fees

Non-negotiable pipeline rules:
- Every output must be slide-friendly.
- Every title must be conclusion-driven.
- No content block should exceed template readability.
- Avoid narrative duplication across sections.
- Flag uncertain claims.
- Optimize for a real client-facing proposal.

=== END WORKFLOW CONTEXT ===
"""

# 최종 조립 순서 — 오케스트레이터와 어셈블러가 참조
FINAL_ASSEMBLY_ORDER = [
    {
        "section_id": "cover",
        "section_name": "Cover / Mandate Understanding",
        "description": "프로젝트 개요, 자문 범위, 핵심 목표",
        "source_agents": ["proposal_orchestrator"],
    },
    {
        "section_id": "credentials",
        "section_name": "Why Us / Credentials",
        "description": "자문사 역량, 차별화 포인트",
        "source_agents": ["proposal_orchestrator"],
    },
    {
        "section_id": "asset_understanding",
        "section_name": "Asset Understanding",
        "description": "자산 분석, 강점, 임차인/임대 프로필, 업사이드",
        "source_agents": ["asset_analysis_agent"],
    },
    {
        "section_id": "market_context",
        "section_name": "Market Context",
        "description": "시장 환경, 입지 수요, 임대/투자 시장",
        "source_agents": ["location_demand_agent", "market_analysis_agent"],
    },
    {
        "section_id": "pricing_logic",
        "section_name": "Pricing Logic",
        "description": "가치평가, 비교 거래, 가격 시나리오",
        "source_agents": ["valuation_agent"],
    },
    {
        "section_id": "buyer_strategy",
        "section_name": "Buyer Strategy",
        "description": "매수자 세분화, 엔드유저 전략, 타겟 리스트",
        "source_agents": ["buyer_segmentation_agent", "enduser_strategy_agent"],
    },
    {
        "section_id": "sale_strategy",
        "section_name": "Recommended Sale Strategy",
        "description": "종합 딜 전략, 포지셔닝, 접근법",
        "source_agents": ["deal_strategy_agent"],
    },
    {
        "section_id": "execution_plan",
        "section_name": "Execution Plan",
        "description": "실행 로드맵, 타임라인, 역할 분담",
        "source_agents": ["execution_plan_agent"],
    },
    {
        "section_id": "track_record",
        "section_name": "Track Record / Team / Fees",
        "description": "실적, 팀 구성, 수수료 구조",
        "source_agents": ["proposal_orchestrator"],
    },
]
