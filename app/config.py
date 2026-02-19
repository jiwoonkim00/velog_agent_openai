from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    google_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"   # 예: gemini-1.5-flash / gemini-1.5-pro

    # 웹 검색
    tavily_api_key: str = ""

    # Velog
    velog_access_token: str = ""

    # 스케줄러
    schedule_hour: int = 9
    schedule_minute: int = 0
    auto_publish: bool = False  # False면 초안만 저장, True면 Velog 자동 발행

    class Config:
        env_file = ".env"


settings = Settings()
