---
title: Test Markdown Image
updated: 2026-08-18
---

# 마크다운 이미지 픽스처

MkDocs 는 마크다운 이미지의 상대 경로를 빌드하면서 다시 써 준다.
그래서 아래 참조는 원본이 있는 자리 기준으로 찾아야 하고, 깨진 것으로 잡히면 안 된다.

![있는 그림](images/real-image-fixture.svg)

반대로 이건 어느 기준으로도 없는 파일이라 반드시 보고돼야 한다.

![없는 그림](images/missing-image-fixture.svg)
