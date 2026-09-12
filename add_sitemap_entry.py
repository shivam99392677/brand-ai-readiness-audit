
from pathlib import Path

content = Path("src/evidence/models.py").read_text(encoding="utf-8")
if "class SitemapEntry" not in content:
    entry_code = """
class SitemapEntry(BaseModel):
    \"\"\"Single URL entry from a sitemap XML payload.\"\"\"
    url: str = Field(..., description="Target URL")
    lastmod: Optional[str] = Field(default=None, description="Last modified date string")
    changefreq: Optional[str] = Field(default=None, description="Declared change frequency")
    priority: Optional[float] = Field(default=None, description="Declared sitemap priority")
"""
    content = content.replace("class SitemapEvidence", entry_code + "\n\nclass SitemapEvidence")
    Path("src/evidence/models.py").write_text(content, encoding="utf-8")
    print("Added SitemapEntry successfully!")

