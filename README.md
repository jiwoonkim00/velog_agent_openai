# 🦜 Velog Auto Blog Agent

> **LangGraph + Gemini + Tavily**로 만든 자동 Velog 블로그 작성 에이전트  
> RSS에서 AI 트렌드를 감지하고, 웹 검색으로 최신 정보를 반영한 SEO 최적화 글을 매일 자동 발행합니다.

## 아키텍처

```
[APScheduler] ──매일 09:00──▶ LangGraph
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
          [1. collect]        [2. research]       [3. plan]
          RSS 수집 +          Tavily 웹 검색       SEO 키워드 +
          주제 선정           최신 정보 수집        목차 설계
                                    │
                         ┌──────────┘
                         ▼
                   [4. write] ◀─────┐ 섹션 루프
                   섹션별 본문        │
                   작성              │
                         │ 완료      │
                         ▼          │
                   [5. seo]         │
                   제목/태그/        │
                   메타디스크립션    │
                         │          │
                         ▼          │
                   [6. critique]    │
                   품질 검토        │
                   (1~10점)         │
                         │          │
               점수<7 ───┼─── 점수≥7│
                         ▼          │
                   [7. revise] ─────┘ (최대 2회)
                   피드백 반영
                   재작성
                         │ (2회 완료 또는 점수≥7)
                         ▼
                   [8. publish]
                   Velog 자동 발행
                   (또는 파일 저장)
```

## 시작하기

### 1. 사전 준비

```bash
# Gemini API 키 발급 (Google AI Studio)
# https://aistudio.google.com/app/apikey → API Key 복사

# Tavily API 키 발급 (무료 1000회/월)
# https://tavily.com → Sign up → API Key 복사

# Velog Access Token 발급 (자동 발행 시 필요)
# 브라우저 → velog.io 로그인
# DevTools(F12) → Application → Cookies → velog.io → access_token 값 복사
```

### 2. 환경변수 설정

```bash
# .env 파일 열어서 값 채우기
```

필수 값:
- `GOOGLE_API_KEY`
- `GEMINI_MODEL` (예: `gemini-2.5-flash`)

선택 값:
- `TAVILY_API_KEY` (리서치 기능 사용 시)
- `VELOG_ACCESS_TOKEN` (자동 발행 시)

### 3. 패키지 설치 및 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## API 사용법

```bash
# RSS에서 자동 주제 선정 후 생성
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{}'

# 특정 주제로 생성
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "2025년 AI 에이전트 트렌드"}'

# 실시간 스트리밍으로 생성 과정 보기
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{}'

# 스케줄러 수동 트리거
curl -X POST http://localhost:8000/schedule/trigger

# API 문서
open http://localhost:8000/docs
```

## 테스트

```bash
# LLM 없이 실행 가능한 유닛 테스트
pytest tests/ -v

# 전체 통합 테스트 (Gemini API 키 필요)
pytest tests/ -v -m integration
```

## 파일 구조

```
velog_agent/
├── app/
│   ├── config.py              # 환경변수 설정
│   ├── state.py               # BlogState 정의
│   ├── graph.py               # LangGraph 그래프 + 라우터
│   ├── main.py                # FastAPI + APScheduler
│   ├── nodes/
│   │   ├── n1_collect.py      # RSS 수집 + 주제 선정
│   │   ├── n2_research.py     # Tavily 웹 검색
│   │   ├── n3_plan.py         # SEO 키워드 + 목차
│   │   ├── n4_write.py        # 섹션 작성 (루프)
│   │   ├── n5_seo.py          # SEO 최적화
│   │   └── n6_n7_n8.py        # Critique / Revise / Publish
│   └── services/
│       ├── rss.py             # RSS 피드 수집
│       └── velog.py           # Velog GraphQL 발행
├── tests/
│   └── test_agent.py
├── drafts/                    # AUTO_PUBLISH=false 시 초안 저장
├── .env
├── requirements.txt
└── README.md
```
