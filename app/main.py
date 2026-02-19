import uuid
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel
from typing import Optional

from .graph import agent_app
from .config import settings


# ── 스케줄러 ─────────────────────────────────────────────────────────────────

scheduler = AsyncIOScheduler()


def get_initial_state(topic: Optional[str] = None) -> dict:
    """그래프 실행을 위한 초기 State"""
    return {
        "rss_items":        [],
        "topic":            topic or "",      # 빈 문자열이면 RSS에서 자동 선정
        "topic_reason":     "",
        "research_results": [],
        "references":       [],
        "outline":          [],
        "seo_keywords":     [],
        "sections":         [],
        "draft":            None,
        "seo_title":        None,
        "meta_description": None,
        "velog_tags":       [],
        "critique":         None,
        "quality_score":    None,
        "revision_count":   0,
        "final_draft":      None,
        "velog_url":        None,
        "is_published":     False,
        "logs":             [],
    }


async def run_daily_job():
    """APScheduler가 매일 자동 실행하는 태스크"""
    print("🕘 [Scheduler] 일일 블로그 자동 생성 시작")
    session_id = f"daily-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": session_id}}
    try:
        # topic을 비워두면 RSS에서 자동 선정
        result = agent_app.invoke(get_initial_state(), config=config)
        url = result.get("velog_url") or "초안 저장됨"
        print(f"✅ [Scheduler] 완료 → {url}")
    except Exception as e:
        print(f"❌ [Scheduler] 실패: {e}")


# ── FastAPI 앱 ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 스케줄러 등록
    scheduler.add_job(
        run_daily_job,
        CronTrigger(hour=settings.schedule_hour, minute=settings.schedule_minute),
        id="daily_blog_job",
        replace_existing=True,
    )
    scheduler.start()
    print(f"⏰ 스케줄러 시작: 매일 {settings.schedule_hour:02d}:{settings.schedule_minute:02d} 자동 실행")
    yield
    scheduler.shutdown()


app = FastAPI(
    title="🦜 Velog Auto Blog Agent",
    description="LangGraph + Gemini + Tavily로 만든 자동 Velog 블로그 작성 에이전트",
    version="2.0.0",
    lifespan=lifespan,
)


# ── 요청/응답 스키마 ──────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    topic: Optional[str] = None   # None이면 RSS에서 자동 선정
    session_id: Optional[str] = None


class GenerateResponse(BaseModel):
    session_id: str
    topic: str
    seo_title: str
    velog_tags: list[str]
    quality_score: int
    revision_count: int
    velog_url: Optional[str]
    is_published: bool
    final_draft: str
    logs: list[str]


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "gemini_model":  settings.gemini_model,
        "auto_publish":  settings.auto_publish,
        "schedule":      f"매일 {settings.schedule_hour:02d}:{settings.schedule_minute:02d}",
    }


@app.post("/generate", response_model=GenerateResponse, tags=["Agent"])
async def generate(req: GenerateRequest):
    """
    블로그 글을 즉시 생성합니다.
    - topic 미입력 → RSS에서 오늘의 트렌드 주제 자동 선정
    - topic 입력   → 해당 주제로 생성
    """
    session_id = req.session_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    try:
        result = agent_app.invoke(get_initial_state(req.topic), config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return GenerateResponse(
        session_id=session_id,
        topic=result.get("topic", ""),
        seo_title=result.get("seo_title") or result.get("topic", ""),
        velog_tags=result.get("velog_tags") or [],
        quality_score=result.get("quality_score") or 0,
        revision_count=result.get("revision_count") or 0,
        velog_url=result.get("velog_url"),
        is_published=result.get("is_published", False),
        final_draft=result.get("final_draft") or "",
        logs=result.get("logs") or [],
    )


@app.post("/stream", tags=["Agent"])
async def stream(req: GenerateRequest):
    """
    생성 과정을 SSE로 실시간 스트리밍합니다.
    각 노드 완료 시마다 이벤트를 전송합니다.
    """
    session_id = req.session_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    def event_stream():
        yield f"data: {json.dumps({'event': 'start', 'session_id': session_id}, ensure_ascii=False)}\n\n"
        try:
            for event in agent_app.stream(get_initial_state(req.topic), config=config):
                for node_name, output in event.items():
                    payload = {
                        "event": "node_complete",
                        "node":  node_name,
                        "logs":  output.get("logs") or [],
                    }
                    if node_name == "publish":
                        payload["velog_url"]   = output.get("velog_url")
                        payload["is_published"] = output.get("is_published")
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'event': 'done'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/history/{session_id}", tags=["Agent"])
async def history(session_id: str):
    """이전 생성 세션의 State를 조회합니다."""
    config = {"configurable": {"thread_id": session_id}}
    try:
        state = agent_app.get_state(config)
        if not state.values:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        v = state.values
        return {
            "session_id":     session_id,
            "topic":          v.get("topic"),
            "seo_title":      v.get("seo_title"),
            "velog_tags":     v.get("velog_tags"),
            "quality_score":  v.get("quality_score"),
            "revision_count": v.get("revision_count"),
            "velog_url":      v.get("velog_url"),
            "is_published":   v.get("is_published"),
            "logs":           v.get("logs"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schedule/trigger", tags=["System"])
async def manual_trigger():
    """스케줄러를 수동으로 즉시 실행합니다."""
    await run_daily_job()
    return {"message": "일일 작업 수동 실행 완료"}
