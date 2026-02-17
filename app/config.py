from __future__ import annotations

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")
    timezone_name: str = Field(default="Europe/Moscow", alias="TIMEZONE")
    max_posts: int = Field(default=1, alias="MAX_POSTS")

    studio_name: str = Field(default="Drivon Detailing", alias="STUDIO_NAME")
    works_url: str = Field(default="", alias="WORKS_URL")
    promotions_text: str = Field(default="Актуальные акции уточняйте у администратора.", alias="PROMOTIONS_TEXT")
    contacts_text: str = Field(default="📍 Адрес: ...\\n📞 Телефон: ...", alias="CONTACTS_TEXT")
    admin_contact: str = Field(default="@admin", alias="ADMIN_CONTACT")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def normalize_text_fields(self) -> "Settings":
        self.promotions_text = self.promotions_text.replace("\\n", "\n")
        self.contacts_text = self.contacts_text.replace("\\n", "\n")
        return self

    @property
    def admin_ids(self) -> set[int]:
        values: set[int] = set()
        for item in self.admin_ids_raw.split(","):
            item = item.strip()
            if not item:
                continue
            try:
                values.add(int(item))
            except ValueError:
                continue
        return values

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
