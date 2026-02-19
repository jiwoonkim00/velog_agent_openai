import json, re, os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from ..state import BlogState
from ..config import settings

if settings.google_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key

llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    temperature=0.4,
)


def seo_optimize(state: BlogState) -> dict:
    """
    [Node 5] SEO 최적화
    
    - 클릭률 높은 SEO 제목 생성
    - 160자 이내 메타 디스크립션
    - Velog 태그 5개 선정
    """
    topic = state["topic"]
    keywords = ", ".join(state.get("seo_keywords") or [])
    draft_preview = (state.get("draft") or "")[:500]

    prompt = f"""당신은 기술 블로그 SEO 전문가입니다.

블로그 주제: {topic}
핵심 키워드: {keywords}
초안 미리보기: {draft_preview}

다음 세 가지를 최적화해주세요:

1. SEO 제목: 검색 노출 + 클릭률을 동시에 높이는 제목
   - 핵심 키워드 포함
   - 숫자나 연도 활용 (예: "2025년", "5가지", "완전 정복")
   - 50자 이내
   
2. 메타 디스크립션: 검색 결과에 표시될 요약문
   - 핵심 키워드 포함
   - 독자가 클릭하고 싶게 만드는 문장
   - 반드시 120자 이내
   
3. Velog 태그: 관련 태그 5개
   - 한국어/영어 혼합 OK
   - 너무 광범위하지 않게

JSON 형식으로만 응답:
{{
  "seo_title": "SEO 최적화된 제목",
  "meta_description": "120자 이내 메타 디스크립션",
  "velog_tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]
}}"""

    response = llm.invoke([HumanMessage(content=prompt)])

    try:
        content = re.sub(r"```(?:json)?|```", "", response.content).strip()
        data = json.loads(content)
        seo_title = data.get("seo_title", topic)
        meta_desc = data.get("meta_description", "")[:160]
        tags = data.get("velog_tags", [])[:5]
    except Exception:
        seo_title = topic
        meta_desc = ""
        tags = (state.get("seo_keywords") or [])[:5]

    return {
        "seo_title":        seo_title,
        "meta_description": meta_desc,
        "velog_tags":       tags,
        "logs":             [f"🎯 [SEO] 제목: '{seo_title}' | 태그: {tags}"],
    }
