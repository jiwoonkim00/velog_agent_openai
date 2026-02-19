from typing import TypedDict, Annotated, Optional
import operator


class BlogState(TypedDict):
    # ── 1. RSS 수집 결과 ───────────────────────────────────────────
    rss_items: list[dict]           # 수집된 RSS 아이템 원본
    topic: str                      # 최종 선정된 주제
    topic_reason: str               # 이 주제를 선택한 이유

    # ── 2. 리서치 결과 ────────────────────────────────────────────
    research_results: Annotated[list, operator.add]  # 웹 검색 결과 누적
    references: list[str]           # 참고 URL 목록

    # ── 3. 기획 결과 ──────────────────────────────────────────────
    outline: list[str]              # 목차
    seo_keywords: list[str]         # SEO 핵심 키워드

    # ── 4. 작성 결과 ──────────────────────────────────────────────
    sections: Annotated[list, operator.add]  # 작성된 섹션 누적
    draft: Optional[str]            # 조합된 전체 초안

    # ── 5. SEO 최적화 결과 ────────────────────────────────────────
    seo_title: Optional[str]        # SEO 최적화된 제목
    meta_description: Optional[str] # 메타 디스크립션 (160자 이내)
    velog_tags: list[str]           # Velog 태그 (최대 5개)

    # ── 6. 품질 관리 ──────────────────────────────────────────────
    critique: Optional[str]         # 검토 피드백
    quality_score: Optional[int]    # 품질 점수 (1~10)
    revision_count: int             # 수정 횟수

    # ── 7. 발행 결과 ──────────────────────────────────────────────
    final_draft: Optional[str]      # 최종 초안 (마크다운)
    velog_url: Optional[str]        # 발행된 Velog URL
    is_published: bool              # 발행 여부

    # ── 메타 ──────────────────────────────────────────────────────
    logs: Annotated[list, operator.add]  # 실행 로그
