from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from ..state import BlogState
from ..config import settings
import json, re, os

if settings.google_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key

llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    temperature=0.3,
)


def research(state: BlogState) -> dict:
    """
    [Node 2] Tavily로 주제 관련 최신 정보 웹 검색
    
    흐름:
    1. LLM이 주제를 분석해서 검색 쿼리 3개 생성
    2. 각 쿼리로 Tavily 검색 실행
    3. 검색 결과 요약 + 참고 URL 추출
    """
    topic = state["topic"]

    # ── Step 1: 검색 쿼리 생성 ────────────────────────────────────
    query_prompt = f"""블로그 주제: "{topic}"

이 주제로 깊이 있는 블로그를 작성하기 위한 웹 검색 쿼리 3개를 만들어주세요.

요구사항:
- 영어 쿼리 (검색 결과 품질이 더 높음)
- 각각 다른 각도에서 접근 (개요, 실용적 사례, 최신 동향)

JSON 형식으로만 응답:
{{"queries": ["query1", "query2", "query3"]}}"""

    response = llm.invoke([HumanMessage(content=query_prompt)])

    try:
        content = re.sub(r"```(?:json)?|```", "", response.content).strip()
        queries = json.loads(content).get("queries", [topic])
    except Exception:
        queries = [topic, f"{topic} tutorial", f"{topic} best practices"]

    # ── Step 2: Tavily 검색 실행 ──────────────────────────────────
    os.environ["TAVILY_API_KEY"] = settings.tavily_api_key

    search_tool = TavilySearchResults(max_results=3)
    raw_results = []
    references = []

    for query in queries[:3]:
        try:
            results = search_tool.invoke(query)
            for r in results:
                raw_results.append({
                    "query":   query,
                    "title":   r.get("title", ""),
                    "content": r.get("content", "")[:500],  # 500자 제한
                    "url":     r.get("url", ""),
                })
                if r.get("url"):
                    references.append(r["url"])
        except Exception as e:
            raw_results.append({"query": query, "error": str(e)})

    # ── Step 3: 결과 요약 ─────────────────────────────────────────
    results_text = "\n\n".join([
        f"[검색: {r['query']}]\n제목: {r.get('title','')}\n내용: {r.get('content','')}"
        for r in raw_results if "error" not in r
    ])

    summary_prompt = f"""다음 검색 결과를 한국어로 핵심만 요약해주세요.
블로그 작성에 활용할 핵심 정보, 통계, 사례를 중심으로 정리하세요.

검색 결과:
{results_text[:3000]}

요약 (500자 이내):"""

    summary_response = llm.invoke([HumanMessage(content=summary_prompt)])

    return {
        "research_results": [summary_response.content.strip()],
        "references":       list(set(references)),  # 중복 제거
        "logs":             [f"🔍 [Research] 쿼리 {len(queries)}개, 결과 {len(raw_results)}개 수집 완료"],
    }
