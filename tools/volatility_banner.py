"""
MkDocs hook: volatility: high 문서 상단에 "빠르게 낡는 문서" 배너 자동 삽입.

프론트매터에 volatility: high 가 있으면 admonition 배너를 페이지 최상단에 붙인다.

주의: 예전에는 안내 문구가 "Anthropic 공식 문서를 확인하세요"로 하드코딩돼 있었다.
그래서 Gemini·GPT·Cursor 같은 비-Anthropic 문서 21개가 엉뚱한 곳을 가리켰다.
문서 경로에서 제공사를 판별해 각자 맞는 곳을 안내한다.
"""

# 경로 조각 → (제공사 이름, 확인처). 위에서부터 먼저 맞는 것을 쓴다.
_PROVIDERS = [
    ("AI/Claude", ("Anthropic", "Anthropic 공식 문서와 릴리스 노트")),
    ("AI/Gemini", ("Google", "Google AI 공식 문서와 릴리스 노트")),
    ("AI/GPT", ("OpenAI", "OpenAI 공식 문서와 릴리스 노트")),
    ("AI/Codex", ("OpenAI", "OpenAI 공식 문서와 릴리스 노트")),
    ("AI/Grok", ("xAI", "xAI 공식 문서")),
    ("AI/Qwen", ("Alibaba", "Qwen 공식 문서")),
    ("AI/DeepSeek", ("DeepSeek", "DeepSeek 공식 문서")),
    ("AI/Ollama", ("Ollama", "Ollama 공식 문서")),
    ("AI/GitHub_Copilot", ("GitHub", "GitHub Copilot 공식 문서")),
    ("AI/Cursor", ("Cursor", "Cursor 공식 문서")),
    ("AI/MCP", ("MCP", "Model Context Protocol 명세")),
]

_DEFAULT = (None, "해당 제품의 공식 문서와 릴리스 노트")


def _provider_for(src_path: str):
    normalized = (src_path or "").replace("\\", "/")
    for prefix, info in _PROVIDERS:
        if normalized.startswith(prefix):
            return info
    return _DEFAULT


def on_page_markdown(markdown, page, **kwargs):
    if page.meta.get("volatility") != "high":
        return markdown

    # 프론트매터 updated 는 손으로 적는 값이라 실제 수정일과 몇 달씩 어긋난다.
    # 신선도를 알려주려고 만든 배너가 오히려 거짓말을 하게 되므로,
    # git 리비전 날짜(git-revision-date-localized 플러그인이 넣어준다)를 우선한다.
    updated = (
        page.meta.get("git_revision_date_localized")
        or page.meta.get("updated")
        or "날짜 미지정"
    )
    _, where = _provider_for(getattr(page.file, "src_path", ""))

    banner = (
        '!!! warning "빠르게 낡는 문서"\n'
        f"    이 주제는 릴리스 주기가 빠릅니다. 최종 확인: **{updated}**  \n"
        f"    읽기 전 {where}에서 최신 여부를 확인하세요.\n\n"
    )
    return banner + markdown
