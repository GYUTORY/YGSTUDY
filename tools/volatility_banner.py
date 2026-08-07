"""
MkDocs hook: volatility: high 문서 상단에 "빠르게 낡는 문서" 배너 자동 삽입.

프론트매터에 volatility: high 가 있으면 admonition 배너를 페이지 최상단에 붙인다.
updated 날짜를 함께 표시해 독자가 마지막 검토 시점을 알 수 있게 한다.
"""


def on_page_markdown(markdown, page, **kwargs):
    if page.meta.get("volatility") != "high":
        return markdown

    updated = page.meta.get("updated", "날짜 미지정")
    banner = (
        '!!! warning "빠르게 낡는 문서"\n'
        f"    AI·클라우드 관련 내용은 릴리스 주기가 빠릅니다. 최종 확인: **{updated}**  \n"
        "    읽기 전 Anthropic 공식 문서 또는 릴리스 노트에서 최신 여부를 확인하세요.\n\n"
    )
    return banner + markdown
