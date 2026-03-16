# IM Proposal Auto — 상업용 부동산 매각 자문 제안서 자동 생성 시스템

## 개요

상업용 부동산 컨설팅 회사의 매각 자문(Sell-Side Advisory) 제안서를 원본 자료만으로 자동 생성하는 멀티 에이전트 파이프라인입니다.

핵심 원칙:
- **슬라이드 블록 단위 출력** — 모든 에이전트는 "보고서"가 아니라 "슬라이드 블록"을 생산합니다
- **템플릿 준수 최우선** — `template_guardian`이 모든 출력의 디자인/톤 일관성을 보장합니다
- **분석과 디자인 적합화 동시 수행** — 각 에이전트가 내용과 표현 방식을 함께 제안합니다

## 아키텍처

```
proposal_orchestrator (메인 에이전트)
├── Stage 1: 입력 분해 및 사전 검증
├── Stage 2: 기반 분석 (병렬)
│   ├── asset_analysis_agent
│   ├── location_demand_agent
│   ├── market_analysis_agent
│   └── buyer_segmentation_agent
├── Stage 3: 파생 분석
│   ├── valuation_agent
│   ├── enduser_strategy_agent
│   └── deal_strategy_agent
├── Stage 4: 실행 계획
│   └── execution_plan_agent
├── Stage 5: 문안 정제 + 템플릿 적합화
│   ├── slide_narrative_agent
│   └── template_guardian
└── Stage 6: 최종 QA 검토
    └── qa_review_agent
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

# 최종 슬라이드 블록 확인
for i, slide in enumerate(result.final_slide_blocks):
    print(f"Slide {i+1}: {slide.get('slide_title', 'N/A')}")

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

## 출력

- `output/proposal_output.json` — 전체 파이프라인 결과 (모든 에이전트 결과 포함)
- `output/final_slides.json` — 최종 승인된 슬라이드 블록만 추출

## 에이전트 구성

| 에이전트 | 역할 | 단계 |
|---------|------|------|
| `proposal_orchestrator` | 전체 파이프라인 지휘 | — |
| `template_guardian` | 템플릿 준수 검증/리라이트 | 5 |
| `asset_analysis_agent` | 자산 분석 및 포지셔닝 | 2 |
| `location_demand_agent` | 입지-수요 연결 논리 | 2 |
| `market_analysis_agent` | 시장 환경 → 매각 근거 | 2 |
| `buyer_segmentation_agent` | 매수자 세분화/우선순위화 | 2 |
| `valuation_agent` | 가격 논리 및 시나리오 | 3 |
| `enduser_strategy_agent` | 실사용 매수자 전략 | 3 |
| `deal_strategy_agent` | 종합 딜 전략 수립 | 3 |
| `execution_plan_agent` | 실행 로드맵 | 4 |
| `slide_narrative_agent` | 서사/카피 정제 | 5 |
| `qa_review_agent` | 최종 품질 검토 | 6 |

## 공통 슬라이드 블록 스키마

모든 에이전트는 아래 형식의 슬라이드 블록을 출력합니다:

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
  "speaker_note": "발표자 메모"
}
```
