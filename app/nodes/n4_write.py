import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from ..state import BlogState
from ..config import settings

if settings.google_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key

llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    temperature=0.7,
)


def write(state: BlogState) -> dict:
    """
    [Node 4] 목차의 섹션을 하나씩 작성 (루프 노드)
    
    - 매 호출마다 아직 작성 안 된 섹션 1개를 작성
    - writing_router가 모든 섹션 완료 여부를 체크
    - 모두 작성되면 sections를 합쳐 draft 생성
    """
    outline = state.get("outline") or []
    sections = state.get("sections") or []
    written_count = len(sections)

    # 모든 섹션 작성 완료 → draft 조합
    if written_count >= len(outline):
        full_draft = f"# {state['topic']}\n\n"
        full_draft += "\n\n---\n\n".join(sections)
        return {
            "draft": full_draft,
            "logs":  ["✍️ [Write] 전체 초안 조합 완료"],
        }

    # 현재 작성할 섹션
    current_section = outline[written_count]
    research = "\n".join(state.get("research_results") or [])
    keywords = ", ".join(state.get("seo_keywords") or [])

    prompt = f"""당신은 한국의 전문 기술 블로그 작가입니다.
한국어로 작성하세요.

블로그 주제: {state['topic']}
SEO 키워드: {keywords}
전체 목차: {' → '.join(outline)}
참고 리서치: {research[:1500]}

지금 작성할 섹션: **{current_section}** ({written_count + 1}/{len(outline)})

작성 요구사항:
- 마크다운 형식 (## 헤딩으로 시작)
- 400~600자 분량
- SEO 키워드를 자연스럽게 1~2회 포함
- 구체적인 예시, 코드, 또는 수치 데이터 포함
- 독자가 실제로 도움받을 수 있는 실용적인 내용
- 첫 번째 섹션(들어가며)이면 독자의 관심을 끄는 훅으로 시작"""

    response = llm.invoke([HumanMessage(content=prompt)])

    return {
        "sections": [response.content.strip()],
        "logs":     [f"✍️ [Write] '{current_section}' 작성 완료 ({written_count + 1}/{len(outline)})"],
    }
