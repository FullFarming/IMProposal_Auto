# IM Proposal Auto — 상업용 부동산 매각 자문 제안서 자동 생성 시스템

## 개요

상업용 부동산 컨설팅 회사의 매각 자문(Sell-Side Advisory) 제안서를 원본 자료만으로 자동 생성하는 멀티 에이전트 파이프라인입니다.

핵심 원칙:
- **슬라이드 블록 단위 출력** — 모든 에이전트는 "보고서"가 아니라 "슬라이드 블록"을 생산합니다
- **템플릿 준수 최우선** — `template_guardian`이 모든 출력의 디자인/톤 일관성을 보장합니다
- **분석과 디자인 적합화 동시 수행** — 각 에이전트가 내용과 표현 방식을 함께 제안합니다
- **공통 디자인 규칙 자동 주입** — 모든 에이전트 프롬프트에 디자인/템플릿 준수 규칙이 자동 삽입됩니다

## 8-Step Operating Workflow

```
Step 1. Parse all available source materials
Step 2. Classify information → agent categories
Step 3. Dispatch work to specialist agents
Step 4. Collect: key_message + slide blocks + missing data + human validation
Step 5. Send all blocks to slide_narrative_agent for rewriting
Step 6. Send rewritten blocks to template_guardian for compliance
Step 7. Run qa_review_agent before final assembly
Step 8. Assemble final proposal in section order
```

## Final Assembly Order

```
1. Cover / Mandate Understanding
2. Why Us / Credentials
3. Asset Understanding
4. Market Context
5. Pricing Logic
6. Buyer Strategy
7. Recommended Sale Strategy
8. Execution Plan
9. Track Record / Team / Fees
```

## 아키텍처

```
proposal_orchestrator (메인 에이전트)
│
├── Step 1-2: Parse & Classify (입력 자료 분해)
│
├── Step 3-4: Dispatch & Collect
│   ├── Parallel Group 1 (기반 분석)
│   │   ├── asset_analysis_agent      → asset_understanding
│   │   ├── location_demand_agent     → market_context
│   │   ├── market_analysis_agent     → market_context
│   │   └── buyer_segmentation_agent  → buyer_strategy
│   │
│   ├── Parallel Group 2 (파생 분석 — G1 결과 필요)
│   │   ├── valuation_agent           → pricing_logic
│   │   └── enduser_strategy_agent    → buyer_strategy
│   │
│   ├── Sequential: deal_strategy_agent → sale_strategy
│   ├── Sequential: execution_plan_agent → execution_plan
│   └── Framing: cover + credentials + track_record
│
├── Step 5: slide_narrative_agent (섹션 간 중복 제거, 서사 정제)
├── Step 6: template_guardian (섹션별 시각 기준 검증)
├── Step 7: qa_review_agent (조립 순서 인식 QA)
└── Step 8: Final Assembly (9개 섹션 순서대로 조립)
```

## 설치

```bash
pip install -e .
```

## 사용법

### 환경 변수 설정

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### CLI 실행

```bash
# 기본 실행
python -m core.cli --input data/sample_input/sample_asset.json

# 출력 디렉터리 지정
python -m core.cli --input data/sample_input/sample_asset.json --output output/my_proposal

# 모델 변경 및 디버그 로그
python -m core.cli --input data/sample_input/sample_asset.json --model claude-sonnet-4-20250514 --verbose
```

### Python에서 직접 사용

```python
import asyncio
import json
from core.orchestrator import ProposalOrchestrator

with open("data/sample_input/sample_asset.json") as f:
    input_data = json.load(f)

orchestrator = ProposalOrchestrator()
result = asyncio.run(orchestrator.run(input_data))

# 섹션별 조립 결과 확인
for section_id, blocks in result.assembled_proposal.items():
    print(f"{section_id}: {len(blocks)} slides")

# 최종 슬라이드 목록 (순서대로)
for i, slide in enumerate(result.final_slide_blocks):
    print(f"Slide {i+1} [{slide.get('proposal_section')}]: {slide.get('slide_title')}")

# 결과 저장
orchestrator.save_output("output")
```

## 입력 데이터 형식

입력 JSON은 다음 3개 섹션으로 구성됩니다:

```json
{
  "asset_data": { ... },      // 자산 정보 (물리적 특성, 임차인, NOI 등)
  "location_data": { ... },   // 입지 정보 (교통, 주변 시설, 미래 개발 등)
  "market_data": { ... }      // 시장 정보 (투자시장, 임대시장, 비교 거래 등)
}
```

상세 스키마는 `data/sample_input/sample_asset.json` 참조.

## 출력 파일

| 파일 | 설명 |
|------|------|
| `proposal_output.json` | 전체 파이프라인 결과 (모든 에이전트 결과 포함) |
| `final_slides.json` | 최종 슬라이드 블록 (조립 순서대로) |
| `assembled_proposal.json` | 섹션별로 그룹화된 슬라이드 |
| `human_review_items.json` | 수동 검토/확인이 필요한 항목 |

## 에이전트 구성

| 에이전트 | 역할 | 제안서 섹션 | 실행 단계 |
|---------|------|-----------|----------|
| `proposal_orchestrator` | 전체 파이프라인 지휘 | cover, credentials, track_record | 1-2, 3 |
| `asset_analysis_agent` | 자산 분석 및 포지셔닝 | asset_understanding | 3 (G1) |
| `location_demand_agent` | 입지-수요 연결 논리 | market_context | 3 (G1) |
| `market_analysis_agent` | 시장 환경 → 매각 근거 | market_context | 3 (G1) |
| `buyer_segmentation_agent` | 매수자 세분화/우선순위화 | buyer_strategy | 3 (G1) |
| `valuation_agent` | 가격 논리 및 시나리오 | pricing_logic | 3 (G2) |
| `enduser_strategy_agent` | 실사용 매수자 전략 | buyer_strategy | 3 (G2) |
| `deal_strategy_agent` | 종합 딜 전략 수립 | sale_strategy | 3 (seq) |
| `execution_plan_agent` | 실행 로드맵 | execution_plan | 3 (seq) |
| `slide_narrative_agent` | 서사/카피 정제 | all sections | 5 |
| `template_guardian` | 템플릿 준수 검증/리라이트 | all sections | 6 |
| `qa_review_agent` | 최종 품질 검토 | all sections | 7 |

## Non-Negotiable Rules

1. Every output must be slide-friendly
2. Every title must be conclusion-driven
3. No content block should exceed template readability
4. Avoid narrative duplication across sections
5. Flag uncertain claims with `[REQUIRES VALIDATION]`
6. Flag missing data with `[DATA GAP]`
7. Optimize for a real client-facing proposal

## Design Compliance Rules (자동 주입)

모든 에이전트에 자동으로 주입되는 규칙 (`agents/common_rules.py`):

- 데이터 중심 → 표/차트 추천
- 프로세스 중심 → 타임라인/흐름도 추천
- 비교 중심 → 매트릭스 추천
- 자산 소개 → 팩트시트/서머리 패널 추천
- 시각적 과부하 → `SPLIT REQUIRED` 플래그
- 슬라이드당 최대 5개 불릿 (절대 최대 7개)
- 정성적 내용은 3-5개 그룹으로 제한

## 공통 슬라이드 블록 스키마

```json
{
  "slide_title": "결론형 제목",
  "slide_purpose": "이 슬라이드의 존재 이유",
  "headline": "핵심 메시지 1줄",
  "body_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "evidence_points": ["근거 1", "근거 2"],
  "recommended_visual": "표/차트/다이어그램 제안",
  "layout_guidance": "배치 권장 영역",
  "template_notes": "템플릿 준수 참고사항",
  "speaker_note": "발표자 메모",
  "proposal_section": "asset_understanding"
}
```
