import json, re, os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from ..state import BlogState
from ..config import settings
from ..services.velog import publish_to_velog, save_draft_to_file

if settings.google_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key

llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    temperature=0.2,
)
llm_writer = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    temperature=0.7,
)


# ── Node 6: Critique ──────────────────────────────────────────────────────────

def critique(state: BlogState) -> dict:
    """
    [Node 6] 초안 품질 + SEO 검토
    
    평가 항목:
    - 내용의 깊이와 정확성
    - SEO 키워드 자연스러운 포함 여부
    - 독자 친화성 및 가독성
    - 실용적 가치
    """
    draft = state.get("draft") or ""
    keywords = ", ".join(state.get("seo_keywords") or [])

    prompt = f"""당신은 기술 블로그 에디터입니다. 아래 초안을 검토해주세요.

SEO 키워드: {keywords}

--- 초안 ---
{draft[:3000]}
--- 끝 ---

평가 기준:
1. 내용의 깊이와 정확성 (최신 정보 반영 여부)
2. SEO 키워드 자연스러운 포함 (억지스럽지 않은지)
3. 가독성 (마크다운 구조, 단락 길이)
4. 실용적 가치 (독자가 실제로 도움받을 수 있는가)
5. 도입부 훅 (첫 문장이 독자를 잡아당기는가)

JSON 형식으로만 응답:
{{
  "score": 7,
  "strengths": ["강점1", "강점2"],
  "improvements": ["개선점1", "개선점2"],
  "summary": "한 줄 총평"
}}"""

    response = llm.invoke([HumanMessage(content=prompt)])

    try:
        content = re.sub(r"```(?:json)?|```", "", response.content).strip()
        data = json.loads(content)
        score = int(data.get("score", 5))
        improvements = data.get("improvements", [])
        summary = data.get("summary", "")
        critique_text = f"총평: {summary}\n개선점:\n" + "\n".join(f"- {i}" for i in improvements)
    except Exception:
        score = 5
        critique_text = response.content.strip()

    return {
        "critique":      critique_text,
        "quality_score": score,
        "logs":          [f"🔎 [Critique] 점수: {score}/10 | {summary if 'summary' in dir() else ''}"],
    }


# ── Node 7: Revise ────────────────────────────────────────────────────────────

def revise(state: BlogState) -> dict:
    """
    [Node 7] 피드백 반영 재작성
    
    critique 노드의 개선점을 반영해 초안을 개선합니다.
    최대 2회 반복 (무한 루프 방지)
    """
    draft = state.get("draft") or ""
    critique_text = state.get("critique") or ""
    keywords = ", ".join(state.get("seo_keywords") or [])
    revision_count = state.get("revision_count") or 0

    prompt = f"""당신은 전문 기술 블로그 작가입니다. 한국어로 작성하세요.

피드백을 반영해 아래 초안을 개선해주세요.

SEO 키워드 (자연스럽게 포함): {keywords}

피드백:
{critique_text}

현재 초안:
{draft[:3000]}

개선 요구사항:
- 피드백의 개선점을 모두 반영할 것
- 기존 좋은 부분은 유지할 것
- SEO 키워드를 더 자연스럽게 녹여낼 것
- 마크다운 형식 유지
- 전체 초안을 완성된 형태로 작성"""

    response = llm_writer.invoke([HumanMessage(content=prompt)])

    return {
        "draft":          response.content.strip(),
        "revision_count": revision_count + 1,
        "logs":           [f"🔄 [Revise] {revision_count + 1}차 수정 완료"],
    }


# ── Node 8: Publish ───────────────────────────────────────────────────────────

def publish(state: BlogState) -> dict:
    """
    [Node 8] Velog 발행 (또는 파일 저장)
    
    AUTO_PUBLISH=true  → Velog GraphQL API로 실제 발행
    AUTO_PUBLISH=false → drafts/ 폴더에 마크다운 파일로 저장
    """
    draft = state.get("draft") or ""
    seo_title = state.get("seo_title") or state.get("topic") or "블로그 초안"
    tags = state.get("velog_tags") or []
    meta_desc = state.get("meta_description") or ""

    # 참고 문헌 섹션 추가
    references = state.get("references") or []
    if references:
        ref_section = "\n\n---\n\n## 참고\n" + "\n".join(f"- {url}" for url in references[:5])
        final_content = draft + ref_section
    else:
        final_content = draft

    # 메타 정보 푸터
    footer = (
        f"\n\n---\n"
        f"*이 글은 LangGraph + Gemini로 자동 생성되었습니다.*  \n"
        f"*품질 점수: {state.get('quality_score', 0)}/10 | "
        f"수정 횟수: {state.get('revision_count', 0)}회*"
    )
    final_content += footer

    try:
        if settings.auto_publish:
            result = publish_to_velog(
                title=seo_title,
                body=final_content,
                tags=tags,
                meta_description=meta_desc,
                is_temp=False,
            )
            log_msg = f"🚀 [Publish] Velog 발행 완료: {result['url']}"
        else:
            result = save_draft_to_file(
                title=seo_title,
                body=final_content,
                tags=tags,
                meta_description=meta_desc,
            )
            log_msg = f"💾 [Publish] 초안 저장: {result['filename']}"

    except Exception as e:
        result = {"success": False, "url": None}
        log_msg = f"❌ [Publish] 발행 실패: {e}"

    return {
        "final_draft":  final_content,
        "velog_url":    result.get("url"),
        "is_published": result.get("success", False) and settings.auto_publish,
        "logs":         [log_msg],
    }
