import json
import re
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from ..state import BlogState
from ..services.rss import fetch_rss_items
from ..config import settings

if settings.google_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key

llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    temperature=0.3,
)


def collect_and_select_topic(state: BlogState) -> dict:
    """
    [Node 1] RSS 피드 수집 → 트렌딩 주제 선정
    
    흐름:
    1. 여러 RSS 피드에서 최신 아이템 수집
    2. LLM이 아이템 분석 → 가장 블로그 가치 있는 주제 선정
    3. 선정 이유와 함께 반환
    """
    # 사용자가 topic을 직접 입력한 경우 RSS 없이 그대로 사용
    user_topic = (state.get("topic") or "").strip()
    if user_topic:
        return {
            "rss_items":    [],
            "topic":        user_topic,
            "topic_reason": "사용자 입력 주제 사용",
            "logs":         [f"📝 [Topic] 사용자 입력 주제 사용: '{user_topic}'"],
        }

    # RSS 수집
    rss_items = fetch_rss_items(max_per_feed=5)

    if not rss_items:
        # RSS 수집 실패 시 폴백 주제 사용
        return {
            "rss_items":    [],
            "topic":        "2025년 AI 에이전트 트렌드와 LangGraph 실전 활용",
            "topic_reason": "RSS 수집 실패로 기본 주제 사용",
            "logs":         ["⚠️ [RSS] 수집 실패, 기본 주제로 진행"],
        }

    # RSS 아이템 요약 (LLM 컨텍스트 절약)
    items_summary = "\n".join([
        f"[{i+1}] {item['source']} | {item['title']}"
        for i, item in enumerate(rss_items[:20])
    ])

    prompt = f"""당신은 기술 블로그 편집장입니다.
아래는 오늘 수집된 AI/Tech 최신 뉴스 목록입니다.

{items_summary}

한국 개발자 독자를 위한 Velog 기술 블로그 포스팅 주제를 1개 선정해주세요.

선정 기준:
- 한국 개발자들이 실용적으로 활용할 수 있는 주제
- 최신 트렌드를 반영한 주제
- 너무 광범위하지 않고 하나의 포스팅으로 깊게 다룰 수 있는 주제
- 한국어 블로그에 적합한 주제

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "topic": "선정된 블로그 주제 (한국어, 구체적으로)",
  "reason": "이 주제를 선정한 이유 (2~3문장)",
  "source_index": 3
}}"""

    response = llm.invoke([HumanMessage(content=prompt)])

    try:
        content = re.sub(r"```(?:json)?|```", "", response.content).strip()
        data = json.loads(content)
        topic = data.get("topic", "")
        reason = data.get("reason", "")
    except Exception:
        # 파싱 실패 시 첫 번째 아이템 제목 사용
        topic = rss_items[0]["title"]
        reason = "자동 파싱 실패로 첫 번째 아이템 사용"

    return {
        "rss_items":    rss_items,
        "topic":        topic,
        "topic_reason": reason,
        "logs":         [f"📰 [RSS] {len(rss_items)}개 수집 → 주제 선정: '{topic}'"],
    }
