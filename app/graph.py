from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import BlogState
from .nodes import (
    collect_and_select_topic,
    research, plan, write,
    seo_optimize, critique, revise, publish,
)


# ── 라우터 함수들 ─────────────────────────────────────────────────────────────

def writing_router(state: BlogState) -> str:
    """섹션을 모두 작성했으면 seo로, 아니면 다시 write로"""
    outline = state.get("outline") or []
    sections = state.get("sections") or []
    if len(sections) < len(outline):
        return "write_more"
    return "seo"


def quality_router(state: BlogState) -> str:
    """
    품질 점수 7점 이상 또는 2회 수정 완료 → publish
    그 외 → revise
    """
    score = state.get("quality_score") or 0
    revision_count = state.get("revision_count") or 0
    if score >= 7 or revision_count >= 2:
        return "publish"
    return "revise"


# ── 그래프 구성 ──────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(BlogState)

    # ── 노드 등록 ─────────────────────────────────────────────────
    graph.add_node("collect",  collect_and_select_topic)
    graph.add_node("research", research)
    graph.add_node("plan",     plan)
    graph.add_node("write",    write)
    graph.add_node("seo",      seo_optimize)
    graph.add_node("critique", critique)
    graph.add_node("revise",   revise)
    graph.add_node("publish",  publish)

    # ── 엣지 연결 ─────────────────────────────────────────────────
    #
    #  collect → research → plan → write ──┐(더 쓸 섹션 있음)
    #                                       ↓
    #                               write ←─┘
    #                                 │ (완료)
    #                                 ↓
    #                               seo → critique ──┐(점수 낮음)
    #                                                 ↓
    #                                            revise → critique
    #                                                 │ (점수 OK)
    #                                                 ↓
    #                                            publish → END
    #
    graph.set_entry_point("collect")
    graph.add_edge("collect",  "research")
    graph.add_edge("research", "plan")
    graph.add_edge("plan",     "write")

    # write 루프: 섹션 완성까지 반복
    graph.add_conditional_edges(
        "write", writing_router,
        {"write_more": "write", "seo": "seo"}
    )

    graph.add_edge("seo", "critique")

    # critique 분기: 품질 OK → publish, 부족 → revise
    graph.add_conditional_edges(
        "critique", quality_router,
        {"revise": "revise", "publish": "publish"}
    )

    # revise 후 재검토
    graph.add_edge("revise",  "critique")
    graph.add_edge("publish", END)

    return graph


# ── 컴파일 ───────────────────────────────────────────────────────────────────

checkpointer = MemorySaver()
agent_app = build_graph().compile(checkpointer=checkpointer)
