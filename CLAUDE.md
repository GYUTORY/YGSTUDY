# YGSTUDY — 작업 규칙

MkDocs + Material 로 만든 개인 기술 블로그다. 문서 1,351개, 빌드 산출물 1,666쪽.

이 파일은 **실제로 사이트를 망가뜨렸던 사고와 그 원인**을 적어둔 것이다.
전부 이 저장소에서 직접 관측한 것이고, 각 항목에 재현·검증 방법을 함께 적었다.
추상적인 모범 사례는 없다 — 같은 사고를 두 번 내지 않기 위한 목록이다.

---

## 0. 푸시 전에 반드시

```bash
bash tools/verify.sh      # 약 40초. 전부 통과해야 푸시한다.
```

`pages yaml → gen_tags → check_frontmatter → check_mermaid → check_links → mkdocs build --strict → check_built_assets`
순서로 돈다. CI 와 같은 순서다. **하나라도 FAIL 이면 푸시하지 않는다.**

빌드가 오래 걸리는 플러그인(minify·rss·git-revision-date)은 `FULL_BUILD` 환경변수로 갈린다.
로컬 검증은 끄고 돌려 45초, CI 는 켜고 돈다. §5 참조.

### 0-1. FAIL 이 떴을 때 — 문서부터 고치지 않는다

`mkdocs build --strict FAIL` 은 **원인을 말해 주지 않는다.** 게이트는 로그
꼬리 12줄만 보여주는데 진짜 메시지가 그 위에 있는 경우가 많다. 문서를
의심하기 전에 **원인을 먼저 특정한다.**

```bash
# 게이트가 감춘 전문을 본다 (이걸 먼저 한다)
DISABLE_MKDOCS_2_WARNING=true mkdocs build --strict -d /tmp/_dbg 2>&1 | tail -40
```

실제로 겪은 두 가지. 둘 다 **문서에는 아무 문제가 없었다.**

**(1) 도구가 사라진 경우.** venv 를 `/tmp/v3` 에 두고 있었는데 macOS 가
`/tmp` 를 주기적으로 비워서 통째로 날아갔다. 진짜 메시지는
`mkdocs: command not found` 였는데 게이트에서는 그냥 `FAIL` 이었다. 봇이
멀쩡한 문서를 몇 번이나 고쳐 쓰다 커밋을 보류했다.

지금은 게이트가 이걸 구분해서 **검사를 시작하지도 않고** 안내한다.
`mkdocs 를 못 찾았다` 가 뜨면 문서 문제가 아니다:

```bash
bash tools/setup_venv.sh    # venv(~/.venvs/ygstudy) + npm 한 번에
```

**(2) `.pages` 제목에 콜론이 들어간 경우.** 항목 하나가

```yaml
- React 내장 상태 관리: useState, useReducer, Context API: React_Built_in_State.md
```

였다. 제목 안 콜론 때문에 `키: 값` 이 두 번 나오는 꼴이라 YAML 이 죽고,
awesome-pages 가 nav 를 못 만들고, `nav.json` 미생성 + redirects
`MISSING SRC` 12건이 거기서 파생됐다. **증상 세 개가 전부 한 줄에서 나왔다.**

제목에 콜론을 쓰는 건 자연스러운 일이라 또 난다. 쓸 거면 따옴표로 감싼다:

```yaml
- "React 내장 상태 관리: useState, useReducer, Context API": React_Built_in_State.md
```

이제 `pages yaml` 검사가 빌드 **앞에서** 파일·줄·원문·해법까지 낸다.
거기서 걸리면 그게 원인이고, 뒤의 nav·redirects 실패는 따라온 것이다.

### 0-2. 판단 순서

1. **`pages yaml` FAIL** → `.pages` 문법. 문서 내용과 무관
2. **`mkdocs 를 못 찾았다`** → 도구 부재. `bash tools/setup_venv.sh`
3. **`mkdocs build --strict` 만 FAIL** → 위 명령으로 전문을 보고 나서 판단.
   깨진 링크·없는 앵커면 그때 문서를 고친다
4. **`nav index` / `redirects` FAIL** → 거의 항상 1번의 여파다. `.pages` 부터 본다

**증상이 여러 개 뜨면 각각 고치려 들지 말고 가장 앞 단계부터 본다.**
위 사례에서 실제 수정은 한 줄이었고 나머지는 저절로 사라졌다.

---

## 1. Material 테마를 건드릴 때

### 1-1. `data-md-color-scheme` 는 `<body>` **자신**에 붙는다

```css
/* ✗ 영원히 매치 안 됨 — 자손 body 를 찾는 선택자다 */
[data-md-color-scheme="slate"] body { background: #1F1C1E; }

/* ✓ */
body[data-md-color-scheme="slate"] { background: #1F1C1E; }
```

`html` 도 마찬가지다. `html` 은 body 의 **조상**이라 자손 선택자로 못 잡는다.

**이 한 줄 때문에 다크모드가 통째로 죽어 있었다.** 배경은 라이트(#FDFBFA)인데 글자만
다크(#F0EDE9)로 바뀌어 대비 1.13:1, 본문·제목·표가 전부 유령 글자였다.
빌드는 통과하고 라이트 모드는 멀쩡해서 아무도 눈치채지 못했다.

**검증**: 다크로 전환한 뒤 `getComputedStyle(document.body).backgroundColor` 가
실제로 어두운 값인지 본다. `--md-default-bg-color` 변수 값만 보면 속는다 —
변수는 맞는데 body 에 안 먹고 있을 수 있다.

### 1-2. 다크모드에서 색 변수를 재정의했는지 전수 확인

`--warm-white` 를 slate 블록에서 재정의하지 않아 배경 7곳이 다크에서도 밝게 남아 있었다.
새 색 변수를 만들면 **라이트/다크 양쪽에 정의가 있는지** 확인한다.

### 1-3. `1rem` 은 16px 이 아니라 **20px** 이다

Material 이 `html { font-size: 125% }` 를 건다. `0.8rem` = 16px 이다.
"폰트가 작아 보인다"고 rem 값을 고치기 전에 실제 계산값을 재라.
(한 번 이 착각으로 "폰트가 작아졌다"고 잘못 보고한 적이 있다.)

### 1-4. `.md-header__topic` 은 `position: absolute` 다

Material 은 헤더 제목에 topic 두 개를 겹쳐 두고 교차 페이드시킨다.
부모의 `align-items: center` 가 안 먹는다. 세로 정렬은 topic 자체에
`top: 50%; transform: translateY(-50%)` 로 건다.

### 1-5. 테마 템플릿 override 는 `overrides/` + `custom_dir`

```yaml
theme:
  name: material
  custom_dir: overrides
```

`overrides/main.html` 이 `base.html` 을 extends 하고 `{% block extrahead %}` 에 넣는다.
`{{ super() }}` 를 빼먹으면 Material 이 그 블록에 넣던 것이 사라진다.

---

## 2. 링크·경로

### 2-1. 마크다운 이미지는 경로가 재작성되고, raw `<img>` 는 안 된다

```markdown
![설명](images/x.svg)          <!-- mkdocs 가 출력 URL 기준으로 재작성한다 -->
<img src="images/x.svg">       <!-- 손 안 댄다. 브라우저가 그대로 해석한다 -->
```

`use_directory_urls: true`(기본) 라서 `LLM.md` 는 `/AI/Concepts/LLM/index.html` 로 나간다.
**출력이 한 단계 더 깊다.** 그래서 raw `<img>` 는 `../` 가 하나 더 필요하다.

이걸 모르고 raw `<img>` 의 `../images/` 를 `images/` 로 "고쳤다가" 잘 나오던 이미지 6개를
깨뜨린 적이 있다. `mkdocs build --strict` 는 **마크다운 링크만** 검사해서 안 잡힌다.

- **원칙**: 새 이미지는 마크다운 문법으로 쓴다. `<figure>` 안에 마크다운을 쓰려면
  `<figure markdown="1">` 로 열고 `md_in_html` 확장이 켜져 있어야 한다.
- **가드**: `tools/check_built_assets.py` 가 **빌드 산출물**의 `<img src>` 를 디스크와 대조한다.
  소스 검사로는 못 잡는 이 부류 전용이다. verify.sh 와 CI 양쪽에 물려 있다.

### 2-2. `.pages` 는 하위 폴더 **안의 파일**을 가리키면 안 된다

```yaml
# ✗ GPT/.pages 가 이미 이 파일을 nav 에 넣은 뒤라 두 번째 참조가 Page 에 못 붙는다
#   → href 가 원본 .md 경로로 그대로 나간다 (죽은 링크)
- GPT: GPT/GPT_5_5.md

# ✓ 폴더를 가리킨다. 그 폴더의 .pages 가 내용을 책임진다
- GPT: GPT
```

이것 때문에 **27종 264곳**의 사이드바 링크가 죽어 있었다. 게다가 그 문서를 열어도
사이드바가 접힌 채 현재 위치를 표시하지 못했다(링크가 트리에 안 붙어서).

**같은 폴더를 `.pages` 하단에 또 나열하면 중복**이 되니 한쪽을 지운다.

**검증** — 해결된 링크는 절대 `.md` 로 끝나지 않는다. 이게 곧 판정 기준이다:

```bash
find site -name "*.html" -exec grep -ho 'href="[^"]*\.md"' {} + | grep -v http | sort -u
# 결과가 있으면 전부 죽은 링크다
```

> `navigation.prune` 은 이 문제의 원인이 아니다. prune 없이 빌드하면 오히려
> 208종 36,477회로 훨씬 많다 — prune 이 트리를 안 그려서 가려줬을 뿐이다.

### 2-3. 한글 파일명은 NFC 로 저장한다

macOS 파일시스템은 한글을 NFD(자모 분리)로 쓴다. 저장소는 NFC 다.
로컬에서는 잘 열리는데 리눅스 CI·GitHub Pages 에서 404 가 난다.
`tools/nfc_normalize.py` 로 정규화한다.

### 2-4. 문서를 옮기면 `redirect_maps` 에 남긴다

`mkdocs.yml` 의 `plugins.redirects.redirect_maps`. 옛 URL 이 죽지 않게 한다.
**목적지 경로 오타가 나면 빌드가 실패한다** — 실제로 이걸로 배포가 막힌 적이 있다.

---

## 3. 내비게이션 기능 조합

### 3-1. `navigation.instant` 와 `navigation.prune` 은 같이 쓰지 않는다

prune 은 현재 경로의 가지만 그린다. 그래서 **페이지마다 사이드바 트리가 다르다** —
직렬화 → RDBMS 로 이동하면 항목 11개가 사라지고 28개가 새로 생기며 높이가
1505 → 2171px 로 바뀐다. instant 는 이 교체를 페이지 리로드 없이 화면 안에서
그대로 갈아끼우니 **메뉴가 통째로 요동친다.**

현재 선택: **prune 유지, instant 제거.** prune 을 빼면 페이지 DOM 이
109KB → 542KB(gzip +28KB)로 늘어 렉이 되살아난다.

### 3-2. `navigation.indexes` 를 쓰면 폴더 참조가 그룹 + 인덱스 링크로 렌더된다

폴더를 가리키면 사이드바에 "그룹 라벨 + 그 인덱스 링크"가 함께 나온다.
같은 이름이 두 번 보이는 것처럼 느껴지지만 Material 의 정상 구조다.
아이콘만 있는 빈 `<label class="md-nav__link">` 는 접기/펼치기 토글이다 — 결함 아니다.

---

## 4. 자동 생성물은 생성기를 고친다

빌드 훅이 매번 다시 만든다. **파일을 직접 고치면 되돌아간다.**

| 생성물 | 생성기 |
|---|---|
| 섹션 허브 `*/index.md` 194개 | `tools/section_index.py` |
| 태그 | `tools/gen_tags.py` |
| 최근 변경 문서 | (훅) |
| 관련 문서 | `tools/related_docs.py` |

허브 파일 머리에 `<!-- AUTO-SECTION-INDEX -->` 주석이 있으면 자동 생성물이다.

**허브 제목은 폴더 이름만으로 만들면 겹친다.** `Backend/Security` 와 `Cloud/AWS/Security` 가
둘 다 "Security 전체 보기" 였고, 검색하면 똑같이 생긴 항목이 5개 나왔다.
지금은 겹치는 이름에만 상위 폴더를 붙인다(`AWS · Security`).
설명 문구(`BLURB`)도 잎 이름으로만 찾으면 남의 설명을 가져다 쓴다 — 전체 경로를 먼저 본다.

---

## 5. CI / 배포

### 5-1. 환경변수는 **실제로 배포하는 스텝**에 붙인다

```yaml
- name: Deploy
  env:
    FULL_BUILD: "true"          # ← 이게 없으면 검증과 배포가 다른 빌드가 된다
  run: mkdocs gh-deploy --force
```

`FULL_BUILD` 가 검증 스텝에만 붙어 있어서, **CI 는 초록불인데 실제로 나가는 사이트는
minify·rss·git-revision-date 가 전부 꺼진 채**였다. 결과로

- 1,349개 페이지가 존재하지 않는 RSS 피드를 광고(404)
- HTML 비압축 (2,864줄 vs 136줄)
- 문서마다 최종 수정일 소실

가 몇 달간 방치됐다. **검증 빌드와 배포 빌드의 설정이 같은지 항상 확인한다.**

`git-revision-date-localized` 는 전체 히스토리가 필요하다 — `fetch-depth: 0` 유지.

### 5-2. `|| true` 로 게이트를 무력화하지 않는다

`check_sources.py` 가 `|| true` 로 꺼져 있었다. 실패를 삼키니 있으나 마나였다.
원인은 오탐이었고(131건), 패턴을 정밀화해 24건으로 줄인 뒤 되살렸다.

**오탐이 많으면 아무도 안 본다.** 게이트는 정밀도가 재현율보다 중요하다.
기존 빚 때문에 켤 수 없으면 `|| true` 대신 **변경분만 검사**한다
(`BEFORE_SHA` → 바뀐 파일 선별 → 그 파일의 새로 추가된 줄만).

### 5-3. 배포는 10~14분 걸리고 `cancel-in-progress: true` 다

연달아 푸시하면 앞 배포가 취소된다. 커밋은 누적이라 **내용 손실은 없고**
마지막 푸시가 전부 반영한다. 취소 로그를 보고 놀랄 필요 없다.

### 5-4. GitHub Pages CDN 은 `max-age=600`

배포 직후 확인하면 **최대 10분간 옛 파일을 본다.**
"반영 안 됐다"고 판단하기 전에 gh-pages 브랜치의 실제 바이트와 대조한다:

```bash
curl -s "https://api.github.com/repos/GYUTORY/YGSTUDY/contents/tags/index.html?ref=gh-pages" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['size'])"
```

---

## 6. 접근성 — 최소 기준

**WCAG AA**: 24px 미만 글자는 배경 대비 **4.5:1** 이상. 24px 이상(또는 18.66px 이상 굵은 글씨)은 3:1.

이 저장소에서 실제로 미달이었던 것들:

| 자리 | 전 | 후 |
|---|---|---|
| `--notion-blue` (링크·강조, 16곳 중 11곳이 글자색) | 2.42:1 | `#3D7387` 5.25:1 |
| `--text-muted` 라이트 | 2.49:1 | `#736E68` 4.89:1 |
| `--text-muted` 다크 | 3.46:1 | `#9A948C` 5.19:1 |
| 푸터 저작권 | 1.03:1 (흰 배경에 흰 글씨) | 4.89:1 |

**푸터 저작권은 클래스명 불일치였다.** 사이트는 `.md-footer-copyright` 를 스타일링하는데
Material 의 실제 마크업은 `.md-copyright__highlight` 다. 스타일이 안 먹어 흰색 기본값이 살아 있었다.
**CSS 를 쓰기 전에 실제 렌더된 DOM 의 클래스명을 확인한다.**

mermaid 화살표 라벨은 SVG 안에 `#mmd-xxx .edgeLabel{background:#e8e8e8}` 가 구워진다.
ID 선택자라 클래스로는 못 이긴다. 다크에서 배경·글자를 함께 지정해야 한다.

---

## 7. 성능

### 7-1. mermaid 는 **런타임 렌더**다

`tools/` 가 만드는 게 아니라 `Develop/javascripts/mermaid-init.js` 가 브라우저에서 그린다.
CDN 에서 mermaid **10.9.3 고정**으로 받는다 — 버전을 올리면 반드시 브라우저에서 확인한다.
(예전에 Material 번들이 CDN 최신본을 끌어다 쓰다가 다이어그램 938개가 빈 상자로 나갔다.)

두 가지 제약이 있다:

1. **클래스 이름은 `mermaid` 가 아니라 `mermaid-diagram` / `yg-mermaid`**
   Material 번들이 `.mermaid` 를 먼저 낚아채 `pre` 를 빈 div 로 바꿔 소스를 날린다.
2. **렌더는 전역 단일 큐로 직렬화한다**
   mermaid 10 은 공용 DOM 샌드박스를 쓴다. 배치마다 렌더 체인을 따로 만들면
   서로 겹쳐 **일부가 조용히 실패한다** (14개 중 10개만 그려지고 예외도 안 났다).

화면에 들어올 때만 그린다(`IntersectionObserver`, rootMargin 600px).
초기 롱태스크가 1001ms → 454ms 로 줄었다.

### 7-2. 이미지는 표시 크기의 2배까지만

2878×1494 원본을 325×203 로 표시하고 있었다(8.8배). 720px 로 줄여 234KB → 23KB.

- **원본보다 크게 리사이즈하지 말 것** — 602px 짜리를 720px 로 "줄이면" 확대된다.
- 화면 아래 이미지는 `loading="lazy" decoding="async"`.
- **`width`/`height` 를 반드시 명시한다** — 없으면 지연 로딩이 레이아웃을 흔든다.

### 7-3. 검색 인덱스가 47MB 다

`search/search_index.json` 이 32,784 문서 / 47MB(gzip 10.5MB)다.
문서가 늘수록 커진다. 크기를 볼 때 이 파일을 먼저 본다.

---

## 8. 측정할 때 내가 실제로 틀렸던 것들

수치를 근거로 결론 내기 전에 아래를 의심한다. 전부 이 저장소에서 낸 오판이다.

| 오판 | 실제 | 교훈 |
|---|---|---|
| "표 6/6 가로 넘침" | `overflow-x:auto` 컨테이너 안 정상 스크롤 | 넘침을 셀 때 **스크롤 가능한 조상**을 제외한다 |
| "PC 메뉴 42~50% 두 줄" | 한 줄인데 높이 임계값(38px)을 잘못 잡음 | 줄 수는 높이가 아니라 **한 줄일 때 필요한 폭**과 비교한다 |
| "본문 12.8px" | 경고 박스 내부 텍스트. 본문은 20px | 첫 번째 `<p>` 를 본문으로 가정하지 않는다 |
| "다크모드 대비 미달 164건" | 테마를 속성만 바꿔 반쪽 적용된 상태였음 | 다크 검증은 **실제 토글을 클릭**한다 |
| "다이어그램 4개 미렌더" | 문서가 47,756px 인데 27,000px 만 스크롤함 | 스크롤 테스트는 `scrollHeight` 를 먼저 잰다 |
| "녹화에 굵은 파란 세로 바" | 파란 픽셀 195개뿐. 다운스케일 JPEG 아티팩트 | 압축된 축소 이미지에서 색을 판정하지 않는다 |
| "태그 2,951개 / 1회성 1,887개" | 실제 69개 / 4개 | 옛 감사 수치를 재확인 없이 인용하지 않는다 |
| "CSS 규칙 적용됨" | 주석이 `/* … */` 첫 줄에서 닫혀 뒤 규칙이 통째로 무효 | CSS 를 넣었으면 **산출물에서 그 규칙을 grep** 한다 |
| "한글 검색이 안 된다" | 정상. 같은 페이지에서 입력을 지우고 재입력하면 Material 이 상태를 잃음 | 검색 테스트는 **쿼리마다 새 페이지**로 연다 (§8-1) |
| "검색 인덱스에 한글이 없다" | JSON 이 `\uXXXX` 로 이스케이프한 것뿐 | 인덱스는 원문 문자열이 아니라 **파싱해서** 본다 |
| "404 링크가 전부 죽었다" | 로컬 서버가 루트 배포라 `/YGSTUDY/...` 가 없었을 뿐 | 하위 경로 배포는 **같은 경로로 서빙**해 확인한다 (§8-2) |
| "표 열 수가 안 맞는다" 12건 | 셀 안의 `\|`(이스케이프)를 열 구분자로 셌다 | 파이프를 셀 때 `\|` 와 인라인 코드 안을 제외한다 |
| "미완성 표식(TODO) 8건" | 홈의 "준비 중" 배지, SonarQube 룰 설명 속 `TODO` 등 본문 | 키워드 매칭 전에 **그 줄이 뭘 하는 줄인지** 본다 |
| "빈 섹션 3,505건" | `## 핵심` 아래 `### 하위`가 오는 정상 구조를 셌다 | 빈 섹션은 **같은 레벨 이하** 헤딩이 바로 올 때만이다 |
| "게이트 종료코드가 0이다" | 파이프 뒤에서 `tail` 의 코드를 읽었다 | `cmd \| tail; echo $?` 는 `tail` 의 코드다. 리다이렉트로 분리한다 |
| "미착수 문서가 22개" | 커밋하면 워킹트리가 비어 `git status` 로는 안 보인다 | 진행률은 **상태를 다시 측정**해서 센다 (커밋 후에도 유효한 기준으로) |

---

### 8-1. 검색을 테스트할 때

Material 의 검색은 쿼리마다 새 페이지로 열어야 정확하다.
같은 페이지에서 입력값을 지우고 다시 넣으면 내부 상태가 어긋나 **영어까지 0건**이 된다.
결과 개수(`.md-search-result__meta`)가 쿼리를 바꿔도 그대로면 그건 이전 쿼리의 잔상이다.

```js
// 쿼리마다 새 페이지 → 검색 토글 열기 → value 주입 + input 이벤트 → 3~4초 대기
await page.goto(url, {waitUntil:'networkidle'});
await page.evaluate(() => { const t = document.getElementById('__search');
  t.checked = true; t.dispatchEvent(new Event('change', {bubbles:true})); });
await page.evaluate(q => { const i = document.querySelector('.md-search__input');
  i.focus(); i.value = q; i.dispatchEvent(new Event('input', {bubbles:true})); }, '직렬화');
```

### 8-2. 로컬로 확인할 때는 배포 경로를 맞춘다

이 사이트는 `https://gyutory.github.io/YGSTUDY/` 즉 **하위 경로**에 배포된다.
`site/` 를 루트로 서빙하면 `/YGSTUDY/assets/...` 를 참조하는 CSS·이미지가 전부 404 가 나고,
스타일이 안 붙은 화면을 보고 "레이아웃이 깨졌다"고 오판하게 된다.

```bash
mkdir -p /tmp/srv && ln -s "$PWD/site" /tmp/srv/YGSTUDY
cd /tmp/srv && python3 -m http.server 8080   # http://127.0.0.1:8080/YGSTUDY/
```

---

## 8-3. 문서 내용을 고칠 때

문서 1,156개 중 94개가 **코드만 있고 설명이 없는 상태**였다. 그걸 채우면서 배운 것들이다.

### 부실한 문서를 찾는 방법

길이로는 안 찾아진다(중앙값 5,060자로 충분했다). **코드 대비 설명 비율**이 실제 신호다.

```bash
# 코드가 설명의 5배 이상 + 코드 2000자 초과
# 코드 블록·표·HTML·헤딩을 제외한 순수 산문 길이로 잰다
```

`배경 / 핵심 / 예시` 라는 h2 구조를 쓰는 문서 54개 중 47개(87%)가 여기 걸렸다. **틀만 잡고 코드만 채운 뒤 설명을 안 쓴 문서군**이다. 같은 템플릿의 양호한 7개는 설명이 2,600~10,800자였다.

비율은 **찾기 위한 지표지 목표가 아니다.** 코드가 4만자인 문서는 설명을 1,000자 넣어도 비율이 안 내려간다. 그건 실패가 아니다.

### 무엇을 쓸 것인가

장점 나열은 이미 문서에 있다. 반복하지 말고 **"언제 쓰면 안 되는지"와 "어디서 조용히 깨지는지"**를 쓴다.

가장 값있는 것은 **문서 자신의 코드에 있는 버그를 지적하는 것**이다. 실제로 이런 것들이 나왔다.

- `leading: false` 옵션이 동작하지 않음 (`setTimeout` 이 음수를 0으로 취급)
- `Omit<User,'salt'>` — `Omit` 은 없는 키를 검증하지 않아 민감정보 필터가 샌다
- 리버스 프록시 동시 접속 계산표 — 요청당 커넥션 2개를 안 셈
- 주석의 기대 출력이 실제와 다름 (`countWords` 15인데 12)

### 반드시 실행해서 확인한다

**돌려보지 않은 주장은 쓰지 않는다.** `/tmp` 에서 실제로 실행하고, 필요하면 그 버전을 설치해서 대조한다. 확인 못 하는 주제는 조건을 붙이거나 아예 안 쓴다.

특히 이 부류는 **반드시 갈린다**:

| 주장 | 실제 |
|---|---|
| "CommonJS 최상위 `await` 은 SyntaxError" | `type` 필드 없으면 ESM 으로 재파싱돼 실행됨 |
| "산술 확장 실패 시 셸이 종료한다" | bash 는 계속 진행, sh·zsh 만 종료 |
| "`Refill` 클래스가 없어졌다" | deprecated 일 뿐, 클래스는 존재 |

셸 동작은 **셋 다 돌려봐야** 안다(`bash`/`sh`/`zsh`). Node 동작은 `type` 필드와 확장자 조합을 다 봐야 한다.

### 예제가 주장을 증명하는지 확인한다

주장이 맞아도 예제가 그걸 못 보여주는 경우가 있다.

```bash
local v; v="$(false; echo hi)"   # -e 가 안 걸린다
```

`$(false; echo hi)` 는 **마지막 명령이 `echo` 라 종료 코드가 0** 이다. 실패한 적이 없으니 `-e` 가 발동할 수 없다. `$(false)` 로 바꿔야 주장이 성립한다.

### 새 절을 넣을 때 기존 헤딩을 지우지 않는다

`## 핵심` 자리에 `###` 를 넣어 h2 를 없앤 적이 있다. 본문 700여 줄이 통째로 `## 배경` 하위로 밀려 사이드바에서 본문이 배경의 일부처럼 보였다.

```bash
# 문서 내용 커밋 전에 — 삭제된 헤딩이 있는지 본다
git diff <base> HEAD -- Develop | grep "^-#"
```

순수 추가여야 정상이다. 삭제 줄이 헤딩이면 구조가 깨진 것이다.

---

## 9. 저장소 구조

```
Develop/                 docs_dir. 실제 문서는 전부 여기.
  .pages                 최상위 nav (awesome-pages)
  */index.md             섹션 허브 — 자동 생성물(§4)
  stylesheets/extra.css  사이트 CSS 전부
  javascripts/           extra.js, mermaid-init.js
  assets/images/         공용 이미지
overrides/main.html      테마 override (Open Graph)
tools/                   검사기·생성기 (tools/README.md 참조)
  verify.sh              푸시 전 검증 — 이것부터 돌린다
docs/GATES.md            게이트 목록
.github/
  actions/docs-checks/   검사 스텝 정의 — 두 워크플로가 공유한다
  workflows/             deploy-docs.yml, quality-gate.yml
```

**검사 스텝은 `.github/actions/docs-checks/action.yml` 한 곳에만 정의한다.**
워크플로마다 복붙하면 갈라진다.

---

## 10. 글쓰기

- 정량 비교 주장(`N% 빨라진다`, `N배 느리다`)에는 **출처 링크**를 단다.
  없으면 `check_sources.py` 가 막는다. 단순 수치(`타임아웃 5초`, `메모리 64MB`)는 대상이 아니다.
- **겪은 일을 수치와 함께 적는 것은 막지 않는다.** "히트율 92%가 61%로 내려간 사례가 실제로
  있다" 같은 서술은 저장소 전역에 35건 있는 기존 관행이고 그대로 둔다(2026-08-14 결정).
  남의 벤치마크를 인용하는 것과 자기가 겪은 것을 적는 것은 다르다 — 후자에 출처를 요구하면
  글이 부자연스러워지고, 게이트를 그쪽까지 넓히면 오탐이 늘어 결국 또 꺼지게 된다(§5-2).
  **감사할 때 이 부류를 오류로 올리지 말 것.**
- frontmatter 필수 키는 `tools/check_frontmatter.py` 가 강제한다 (`title`, `tags`, `updated`).
- 태그는 `tools/tags.yml` 의 어휘를 쓴다. 현재 69종이고 1회성은 4개다 — 이 상태를 유지한다.
- sequenceDiagram 안에서 이름 있는 HTML 엔티티(`&lt;` 등)를 쓰면 mermaid 가 깨진다.
  `tools/check_mermaid_entities.py` 가 원인 줄을 직접 짚어준다.
