from pydantic import BaseModel, Field, HttpUrl


class ArticleSummary(BaseModel):
    pmid: str | None
    title: str
    journal: str
    year: str
    url: HttpUrl | None


class LiteratureSearchResponse(BaseModel):
    query: str
    count: int = Field(ge=0)
    articles: list[ArticleSummary]
