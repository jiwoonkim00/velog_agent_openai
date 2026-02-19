import feedparser
import httpx
from datetime import datetime, timezone
from typing import Optional


# ── AI/Tech RSS 피드 목록 ────────────────────────────────────────────────────
RSS_FEEDS = [
    # 글로벌
    {"name": "Hacker News (AI)",    "url": "https://hnrss.org/newest?q=AI+LLM+machine+learning&count=20"},
    {"name": "Dev.to (AI)",         "url": "https://dev.to/feed/tag/ai"},
    {"name": "Towards Data Science","url": "https://towardsdatascience.com/feed"},
    {"name": "The Batch (DeepLearning.AI)", "url": "https://www.deeplearning.ai/the-batch/feed/"},
    # 국내
    {"name": "카카오 테크블로그",    "url": "https://tech.kakao.com/feed/"},
    {"name": "네이버 D2",           "url": "https://d2.naver.com/d2.atom"},
    {"name": "당근 테크블로그",     "url": "https://medium.com/feed/daangn"},
]


def fetch_rss_items(max_per_feed: int = 5) -> list[dict]:
    """
    등록된 RSS 피드들을 모두 수집하여 아이템 리스트로 반환합니다.
    
    반환 형식:
    [
        {
            "title": "GPT-5 Released with New Capabilities",
            "summary": "OpenAI announced...",
            "url": "https://...",
            "source": "Hacker News (AI)",
            "published": "2025-02-19T09:00:00Z"
        },
        ...
    ]
    """
    items = []

    with httpx.Client(timeout=10.0) as client:
        for feed_info in RSS_FEEDS:
            try:
                response = client.get(feed_info["url"])
                feed = feedparser.parse(response.text)

                for entry in feed.entries[:max_per_feed]:
                    # 날짜 파싱
                    published = ""
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

                    # 요약 추출 (summary 또는 content)
                    summary = ""
                    if hasattr(entry, "summary"):
                        # HTML 태그 간단 제거
                        import re
                        summary = re.sub(r"<[^>]+>", "", entry.summary)[:300]

                    items.append({
                        "title":     entry.get("title", ""),
                        "summary":   summary,
                        "url":       entry.get("link", ""),
                        "source":    feed_info["name"],
                        "published": published,
                    })

            except Exception as e:
                # 하나의 피드 실패가 전체를 막지 않도록
                print(f"⚠️ RSS 수집 실패 [{feed_info['name']}]: {e}")
                continue

    return items
