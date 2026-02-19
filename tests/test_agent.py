"""
실행: pytest tests/ -v
- Unit 테스트는 Ollama/Tavily 없이 실행 가능
- Integration 테스트는 Ollama 실행 필요
"""
import pytest
from unittest.mock import patch, MagicMock


# ── Unit Tests (LLM 없이) ─────────────────────────────────────────────────────

def test_graph_builds():
    """그래프가 오류 없이 빌드되는지 확인"""
    from app.graph import build_graph
    graph = build_graph()
    assert graph is not None


def test_all_nodes_registered():
    """8개 노드가 모두 등록되어 있는지 확인"""
    from app.graph import build_graph
    graph = build_graph()
    node_names = list(graph.nodes.keys())
    expected = ["collect", "research", "plan", "write", "seo", "critique", "revise", "publish"]
    for node in expected:
        assert node in node_names, f"'{node}' 노드 누락"


def test_writing_router_loops():
    """섹션이 남아있으면 write_more 반환하는지 확인"""
    from app.graph import writing_router
    state = {
        "outline":  ["섹션1", "섹션2", "섹션3"],
        "sections": ["섹션1 내용"],           # 2개 남음
    }
    assert writing_router(state) == "write_more"


def test_writing_router_done():
    """모든 섹션 완료 시 seo 반환하는지 확인"""
    from app.graph import writing_router
    state = {
        "outline":  ["섹션1", "섹션2"],
        "sections": ["내용1", "내용2"],       # 완료
    }
    assert writing_router(state) == "seo"


def test_quality_router_publish():
    """점수 7점 이상이면 publish 반환하는지 확인"""
    from app.graph import quality_router
    state = {"quality_score": 8, "revision_count": 0}
    assert quality_router(state) == "publish"


def test_quality_router_revise():
    """점수 낮으면 revise 반환하는지 확인"""
    from app.graph import quality_router
    state = {"quality_score": 5, "revision_count": 0}
    assert quality_router(state) == "revise"


def test_quality_router_max_revision():
    """2회 수정 후에는 점수 낮아도 publish로 가는지 확인 (무한루프 방지)"""
    from app.graph import quality_router
    state = {"quality_score": 4, "revision_count": 2}
    assert quality_router(state) == "publish"


# ── Integration Tests (Ollama 필요) ──────────────────────────────────────────

@pytest.mark.integration
def test_full_pipeline_with_topic():
    """
    특정 주제로 전체 파이프라인 실행 테스트
    실행: pytest tests/ -v -m integration
    """
    import uuid
    from app.graph import agent_app
    from app.main import get_initial_state

    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    result = agent_app.invoke(
        get_initial_state(topic="FastAPI 비동기 프로그래밍"),
        config=config,
    )

    assert result["topic"] != ""
    assert result["outline"] and len(result["outline"]) > 0
    assert result["seo_keywords"] and len(result["seo_keywords"]) > 0
    assert result["final_draft"] and len(result["final_draft"]) > 200
    assert result["quality_score"] is not None
    assert result["velog_tags"] and len(result["velog_tags"]) > 0

    print(f"\n✅ 주제: {result['topic']}")
    print(f"✅ SEO 제목: {result['seo_title']}")
    print(f"✅ 태그: {result['velog_tags']}")
    print(f"✅ 품질 점수: {result['quality_score']}/10")
    print(f"✅ 수정 횟수: {result['revision_count']}")
