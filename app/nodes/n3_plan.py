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


def plan(state: BlogState) -> dict:
    """
    [Node 3] SEO 키워드 분석 + 블로그 목차 기획
    
    흐름:
    1. 주제 + 리서치 결과 분석
    2. SEO 키워드 5~7개 추출
    3. 키워드를 반영한 목차 설계
    """
    topic = state["topic"]
    research = "\n".join(state.get("research_results") or [])

    prompt = f"""당신은 SEO 전문 기술 블로그 편집장입니다.

블로그 주제: {topic}

리서치 결과:
{research[:2000]}

다음 두 가지를 함께 기획해주세요:

1. SEO 키워드: 한국 개발자가 이 주제를 검색할 때 쓸 핵심 키워드 5~7개
2. 블로그 목차: SEO 키워드를 자연스럽게 포함한 5~7개 섹션 구성
   - 들어가며(훅이 되는 도입부)로 시작
   - 실용적인 내용 위주
   - 마치며(핵심 요약 + CTA)로 마무리

JSON 형식으로만 응답:
{{
  "seo_keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
  "outline": [
    "들어가며: (흥미로운 도입 문구)",
    "섹션 제목 2",
    "섹션 제목 3",
    "섹션 제목 4",
    "섹션 제목 5",
    "마치며"
  ]
}}"""

    response = llm.invoke([HumanMessage(content=prompt)])

    try:
        content = re.sub(r"```(?:json)?|```", "", response.content).strip()
        data = json.loads(content)
        seo_keywords = data.get("seo_keywords", [])
        outline = data.get("outline", [])
    except Exception:
        seo_keywords = [topic]
        lines = [l.strip().lstrip("-•*0123456789. ") for l in response.content.splitlines() if l.strip()]
        outline = [l for l in lines if len(l) > 2][:7]

    return {
        "seo_keywords": seo_keywords,
        "outline":      outline,
        "logs":         [f"📋 [Plan] 키워드 {len(seo_keywords)}개, 목차 {len(outline)}개 설계 완료"],
    }
