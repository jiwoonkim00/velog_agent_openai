import httpx
import re
from typing import Optional
from ..config import settings

VELOG_GRAPHQL_URL = "https://v2.velog.io/graphql"


def _make_url_slug(title: str) -> str:
    """제목을 Velog URL slug로 변환합니다."""
    slug = title.lower()
    slug = re.sub(r"[^\w\s가-힣-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = slug[:80]  # 최대 80자
    return slug


def publish_to_velog(
    title: str,
    body: str,
    tags: list[str],
    meta_description: str = "",
    is_private: bool = False,
    is_temp: bool = False,      # True면 임시저장
) -> dict:
    """
    Velog GraphQL API로 글을 발행합니다.
    
    반환:
    {
        "success": True,
        "url": "https://velog.io/@username/slug",
        "post_id": "uuid"
    }
    
    ※ VELOG_ACCESS_TOKEN 필요
      브라우저 DevTools → Application → Cookies → velog.io → access_token
    """
    if not settings.velog_access_token:
        raise ValueError("VELOG_ACCESS_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")

    # Velog write post mutation
    mutation = """
    mutation WritePost($input: WritePostInput!) {
      writePost(input: $input) {
        id
        title
        url_slug
        user {
          username
        }
      }
    }
    """

    variables = {
        "input": {
            "title":        title,
            "body":         body,
            "tags":         tags[:5],           # Velog 최대 5개
            "is_markdown":  True,
            "is_temp":      is_temp,
            "is_private":   is_private,
            "url_slug":     _make_url_slug(title),
            "meta":         {"description": meta_description[:160]},
            "series_id":    None,
            "thumbnail":    None,
        }
    }

    headers = {
        "Content-Type":  "application/json",
        "authorization": f"Bearer {settings.velog_access_token}",
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            VELOG_GRAPHQL_URL,
            json={"query": mutation, "variables": variables},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    if "errors" in data:
        raise Exception(f"Velog API 오류: {data['errors']}")

    post = data["data"]["writePost"]
    username = post["user"]["username"]
    url_slug = post["url_slug"]

    return {
        "success":  True,
        "url":      f"https://velog.io/@{username}/{url_slug}",
        "post_id":  post["id"],
        "username": username,
    }


def save_draft_to_file(
    title: str,
    body: str,
    tags: list[str],
    meta_description: str = "",
) -> dict:
    """
    AUTO_PUBLISH=false일 때 마크다운 파일로 초안을 저장합니다.
    """
    import os
    from datetime import datetime

    os.makedirs("drafts", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _make_url_slug(title)[:40]
    filename = f"drafts/{timestamp}_{slug}.md"

    content = f"""---
title: {title}
tags: {tags}
description: {meta_description}
date: {datetime.now().isoformat()}
---

{body}
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "success":  True,
        "url":      None,
        "filename": filename,
    }
