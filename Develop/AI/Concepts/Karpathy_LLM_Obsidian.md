---
title: Karpathy의 LLM + Obsidian 워크플로우
tags: [ai, llm, obsidian, pkm, knowledge-management, karpathy, second-brain]
updated: 2026-04-17
---

# Karpathy의 LLM + Obsidian 워크플로우

## 1. 배경: Karpathy가 말한 것

Andrej Karpathy는 Tesla AI Director와 OpenAI 창립 멤버를 거친 인물이다. 본인 트위터(X)와 강연에서 개인 지식관리(PKM)에 대한 본인 셋업을 여러 번 흘렸는데, 핵심은 단순하다. **모든 메모를 로컬 마크다운 파일로 둔다.** 그리고 그 파일들을 LLM에게 컨텍스트로 던진다.

본인이 강조한 포인트는 대략 이렇다.

- 메모는 plain text 마크다운으로 둔다. 외부 SaaS에 묶이는 순간 10년 뒤에는 못 읽는다.
- 폴더 구조는 깊게 가지 않는다. 검색이 트리보다 빠르다.
- LLM이 등장한 이후, "정리"라는 작업의 비용이 사실상 0에 가까워졌다. 따라서 처음부터 잘 정리하려고 애쓰지 않고, 일단 마구잡이로 적고 나중에 LLM에게 정리시킨다.
- Obsidian 자체에 종속되지 말아라. Obsidian은 마크다운 파일을 보여주는 뷰어일 뿐이다. 내일 사라져도 vault는 살아남아야 한다.

이 관점이 기존 PKM 진영(Notion, Roam Research, Logseq, Tana)과 결정적으로 갈리는 지점이다. 기존 진영은 "구조"와 "양방향 링크"에 집착한다. Karpathy의 관점은 "구조 같은 건 LLM이 알아서 만들어주니, 너는 그냥 적기만 해라"에 가깝다.

---

## 2. 왜 마크다운 vault인가

5년차 백엔드 개발자가 Notion, Confluence, Bear, Apple Notes를 거쳐서 Obsidian으로 정착하는 이유는 거의 비슷하다. 이전 도구들이 망하거나, export가 깨지거나, 검색이 느리거나, 코드블록이 못생겨서다.

마크다운 vault의 실질적인 장점은 다음 네 가지다.

### 2.1 grep이 된다

`rg "kafka rebalance"` 한 줄이면 vault 전체를 1초 안에 훑는다. Notion에서 같은 작업을 하려면 API 호출이 필요하고, 로컬 검색은 캐시된 페이지만 된다. 5년 누적된 메모에서 특정 장애 기록을 찾아야 할 때, grep이 안 되는 PKM은 도구로서 죽은 것과 같다.

### 2.2 git이 된다

vault 자체가 git 저장소다. 변경 이력, 브랜치, diff, blame이 전부 공짜로 따라온다. 메모를 잘못 지웠을 때 `git reflog`로 복구할 수 있다는 것은 큰 안정감을 준다.

### 2.3 LLM에 그대로 먹인다

마크다운은 LLM이 가장 자연스럽게 다루는 포맷이다. 헤딩, 리스트, 코드블록 구조를 그대로 인식한다. Notion의 JSON block 구조나 Roam의 outliner 구조는 토큰 낭비가 심하고, LLM이 다시 마크다운으로 바꿔서 처리해야 한다.

### 2.4 종속이 없다

Obsidian이 망해도, Logseq로 옮겨도, VSCode에서 열어도 동일하게 동작한다. 데이터 주권이 본인 하드디스크에 있다는 점은 PKM의 장기 운영에서 가장 중요한 요소다.

---

## 3. Karpathy 스타일 vault 구조

깊은 폴더 트리를 만들지 않는다. 보통 이런 식이다.

```
vault/
├── daily/
│   ├── 2026-04-17.md
│   ├── 2026-04-16.md
│   └── ...
├── notes/
│   ├── kafka-consumer-rebalance.md
│   ├── postgres-vacuum-tuning.md
│   ├── llm-context-window.md
│   └── ...
├── people/
│   ├── jane-doe.md
│   └── ...
├── projects/
│   ├── ygstudy.md
│   └── ...
└── inbox/
    └── (정리 안 된 잡탕)
```

핵심 원칙 세 가지다.

- `daily/`에 그날 떠오른 모든 것을 시간 순으로 적는다. 회의 중 메모, 디버깅 로그, 책 인용, 아이디어 다 섞여도 된다.
- `notes/`에는 "주제별 영구 메모"만 둔다. 한 파일 = 한 주제. 파일명은 영문 슬러그.
- `inbox/`는 임시 파일 폴더다. 어디 둘지 모르겠으면 일단 여기 던지고 나중에 LLM이 분류한다.

태그는 `#kafka`, `#postgres` 같은 hashtag 형태로 본문에 박는다. 폴더는 절대 깊게 파지 않는다. 깊게 팔수록 옮길 때마다 "어느 폴더에 둘까"를 고민하게 되고, 이 고민 비용이 메모 자체보다 커진다.

---

## 4. LLM 연결 방식

vault에 LLM을 붙이는 방식은 크게 세 가지다. 각각 트레이드오프가 다르다.

### 4.1 Cursor / Claude Code에 vault 폴더 물리기

가장 단순한 방법이다. Cursor를 vault 디렉토리에서 열고, 채팅창에서 `@notes/kafka-consumer-rebalance.md`로 파일을 참조한다. Claude Code는 vault 디렉토리에서 `claude` 명령으로 시작하면 자동으로 `Glob`, `Grep`, `Read`를 써서 vault를 탐색한다.

이 방식의 장점은 RAG를 본인이 구축할 필요가 없다는 점이다. 도구가 알아서 인덱싱하고 검색한다. 단점은 vault 전체가 외부 API(Anthropic, OpenAI)로 흘러나간다는 점이다. 민감한 메모(고객사 이름, 본인 인사 평가, 개인 일기)가 섞여 있다면 이 방식은 위험하다.

### 4.2 로컬 LLM (Ollama, llama.cpp)

`ollama run llama3.1:70b`로 로컬 모델을 띄우고, vault를 컨텍스트로 던진다. 외부 망으로 데이터가 안 나간다는 점이 결정적인 장점이다. 민감한 일기, 회사 내부 문서를 다룰 때는 사실상 이 방식 외에는 답이 없다.

단점은 모델 품질이다. 70B 모델이라도 Claude Sonnet이나 GPT-5와 비교하면 요약/재작성 품질이 한 수 떨어진다. 그리고 M2 Max 64GB 정도는 되어야 70B를 돌릴 수 있다. M1 Pro 16GB로는 8B 모델이 한계다.

### 4.3 본인이 직접 짠 스크립트 + API

vault에서 필요한 파일만 골라서 Anthropic/OpenAI API로 보내는 스크립트를 짠다. 가장 유연하고, 비용이 가장 통제 가능하다. 민감 파일을 코드 단계에서 필터링할 수 있다는 점이 핵심이다.

이 글의 6장에서 Node.js로 짜는 예제를 보여준다.

---

## 5. 워크플로우 패턴

실제로 vault + LLM을 어떻게 쓰는지가 중요하다. Karpathy가 직접 시연하지는 않았지만, 본인 발언과 커뮤니티에서 정착된 패턴은 대략 이렇다.

### 5.1 일일 메모 → 주간 요약

매일 `daily/2026-04-17.md`에 잡탕으로 적는다. 일요일 밤에 LLM에게 그 주의 7개 daily 파일을 던진다. 프롬프트는 이런 식이다.

```
다음 7개 일일 메모를 읽고 아래를 추출해줘.
1. 이번 주 작업한 프로젝트와 진행 상황
2. 새로 배운 기술적 내용
3. 다음 주에 이어서 할 일
4. 영구 메모로 옮길 만한 주제 (notes/ 폴더 후보)
```

이 결과를 `weekly/2026-W16.md`로 저장한다. 한 달 뒤에는 4개의 weekly를 던져서 monthly를 만든다. 시간이 지날수록 정보가 압축되면서 검색 가능한 형태로 남는다.

### 5.2 inbox 자동 분류

`inbox/`에 던진 잡문을 LLM이 읽고 적절한 위치로 옮길 후보를 제안한다.

```
inbox/에 있는 다음 파일을 읽고:
1. 영구 메모로 가치가 있는지 판단
2. 있다면 어떤 제목으로 notes/에 저장할지 제안
3. 어떤 태그를 붙일지 제안
4. 기존 notes/ 파일과 합쳐야 하는지 검토
```

판단은 LLM이 하지만 최종 이동은 사람이 한다. 자동 이동을 시키면 6개월 뒤에 "내가 적은 적도 없는 이상한 폴더"가 만들어져 있다. 이건 본인이 한 번 당해봤다.

### 5.3 영구 메모 재작성

`notes/kafka-consumer-rebalance.md`를 6개월 뒤에 다시 보면 누더기다. 처음 적을 때는 디버깅 중이라 두서가 없고, 중간에 추가한 내용은 톤이 다르고, 결론이 흐릿하다.

LLM에게 "이 파일을 다시 읽기 좋게 재구성해줘. 사실 관계는 절대 바꾸지 말고, 헤딩 구조와 문장 흐름만 손봐줘"라고 시킨다. 결과를 git diff로 확인하고 머지한다. 이 작업이 LLM 등장 전에는 1시간 걸렸는데 이제는 3분이다.

### 5.4 질문에 vault로 답하기

"우리가 작년에 Redis Sentinel 도입할 때 왜 Cluster 안 갔지?" 같은 질문이 떠올랐을 때, vault에 grep으로 관련 파일을 찾고, 그걸 LLM에게 던지면서 질문한다. 본인의 과거 결정 기록이 본인의 질문에 답하는 구조다.

---

## 6. 코드 예제: vault → LLM 컨텍스트 주입

Node.js로 vault에서 마크다운을 읽어 Anthropic API로 보내는 최소 예제다. 실무에서 쓸 수 있는 수준으로 짠다.

```typescript
// vault-query.ts
import Anthropic from "@anthropic-ai/sdk";
import { readFile, readdir, stat } from "node:fs/promises";
import { join } from "node:path";
import matter from "gray-matter";

const VAULT_ROOT = process.env.VAULT_ROOT ?? "/Users/me/vault";
const SENSITIVE_DIRS = ["journal", "people", "private"];

interface VaultNote {
  path: string;
  title: string;
  tags: string[];
  body: string;
  bytes: number;
}

async function walkVault(dir: string): Promise<string[]> {
  const entries = await readdir(dir);
  const files: string[] = [];

  for (const entry of entries) {
    const full = join(dir, entry);
    const s = await stat(full);

    if (s.isDirectory()) {
      const rel = full.replace(VAULT_ROOT + "/", "");
      if (SENSITIVE_DIRS.some((d) => rel.startsWith(d))) continue;
      files.push(...(await walkVault(full)));
    } else if (entry.endsWith(".md")) {
      files.push(full);
    }
  }
  return files;
}

async function loadNote(path: string): Promise<VaultNote> {
  const raw = await readFile(path, "utf-8");
  const { data, content } = matter(raw);
  return {
    path: path.replace(VAULT_ROOT + "/", ""),
    title: data.title ?? path.split("/").pop()!.replace(".md", ""),
    tags: data.tags ?? [],
    body: content,
    bytes: Buffer.byteLength(content, "utf-8"),
  };
}

function searchByTag(notes: VaultNote[], tag: string): VaultNote[] {
  return notes.filter(
    (n) => n.tags.includes(tag) || n.body.includes(`#${tag}`),
  );
}

function buildContext(notes: VaultNote[], maxBytes = 80_000): string {
  let total = 0;
  const parts: string[] = [];

  for (const n of notes) {
    if (total + n.bytes > maxBytes) break;
    parts.push(`<note path="${n.path}">\n${n.body}\n</note>`);
    total += n.bytes;
  }
  return parts.join("\n\n");
}

async function ask(question: string, tag: string) {
  const files = await walkVault(VAULT_ROOT);
  const notes = await Promise.all(files.map(loadNote));
  const matched = searchByTag(notes, tag);

  if (matched.length === 0) {
    console.log(`태그 #${tag}에 매칭되는 노트 없음`);
    return;
  }

  const context = buildContext(matched);
  const client = new Anthropic();

  const response = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 4096,
    system:
      "너는 사용자의 개인 vault에 저장된 메모를 읽고 질문에 답하는 보조 도구다. " +
      "메모에 없는 사실은 추측하지 말고 모른다고 답해라. " +
      "답변에 사용한 노트의 path를 인용해라.",
    messages: [
      {
        role: "user",
        content: `다음은 내 vault에서 #${tag} 태그가 붙은 노트다.\n\n${context}\n\n질문: ${question}`,
      },
    ],
  });

  const text = response.content
    .filter((b) => b.type === "text")
    .map((b) => (b as { text: string }).text)
    .join("\n");

  console.log(text);
}

ask("Kafka consumer rebalance가 자주 일어나면 어떻게 디버깅했지?", "kafka");
```

이 코드의 핵심 디자인 결정 세 가지를 짚어둔다.

- `SENSITIVE_DIRS`로 민감 폴더를 코드 레벨에서 제외한다. 일기, 사람 메모, 비공개 폴더는 절대 LLM으로 안 보낸다.
- `buildContext`에서 byte 단위로 컨텍스트를 자른다. Claude Sonnet 4.6의 컨텍스트는 200K 토큰이지만, 실제로 80KB(약 2만 토큰) 넘기면 비용이 부담된다.
- system 프롬프트에서 "추측 금지, 출처 인용"을 박는다. vault 기반 질의응답에서 hallucination을 막는 가장 단순한 방법이다.

---

## 7. 한계와 트레이드오프

이 워크플로우가 만능은 아니다. 6개월 정도 운영하면서 부딪힌 문제들이다.

### 7.1 컨텍스트 비용

vault가 커질수록 매 질문마다 컨텍스트로 던지는 양이 늘어난다. 1MB짜리 vault를 통째로 던지면 한 번에 $0.5 정도 깨진다. 하루에 10번 질문하면 한 달 $150이다.

해결책은 두 가지다. 첫째, 태그/폴더로 검색 범위를 좁힌다. 둘째, 임베딩 기반 검색을 앞단에 둬서 관련 노트만 컨텍스트로 보낸다. 후자는 벡터 DB를 들여야 해서 무게가 늘어난다. 본인 vault가 50MB 안 넘으면 그냥 grep + 태그 필터로 버틸 수 있다.

### 7.2 민감 메모 분리

이게 가장 골치 아프다. "외부 API에 절대 보내면 안 되는 메모"와 "보내도 되는 메모"를 어떻게 나누는가. 폴더로 분리하는 게 가장 단순하지만, 한 파일 안에 민감/비민감이 섞여있는 경우가 생긴다. 회의록에 사람 이름이 박혀 있는 식이다.

본인은 `journal/`, `people/`, `private/` 세 폴더를 만들고, 이 폴더는 코드 레벨에서 외부 API 호출을 막는다. 로컬 LLM(Ollama llama3.1:70b)으로만 처리한다. 완벽하지 않지만 사고를 한 단계 줄여준다.

### 7.3 LLM이 만든 정리본의 hallucination

"이 노트를 재구성해줘"라고 시키면 LLM이 가끔 사실을 살짝 비튼다. 원본에 없던 숫자가 끼어들거나, 원래 결론과 미묘하게 다른 결론으로 바뀐다. 이걸 git diff 없이 머지하면 6개월 뒤에 본인 메모가 본인을 속인다.

해결: 재작성 결과는 무조건 diff로 검토. 사실 관계 변경이 의심되면 원본을 보존하고 재작성본은 별도 파일로 둔다.

### 7.4 동기화

vault를 여러 기기에서 쓰려면 동기화가 필요하다. iCloud, Dropbox, Syncthing, git 다 써봤는데 git이 가장 안정적이다. iCloud는 충돌 파일(`~conflict`)이 자꾸 생기고, Dropbox는 큰 vault에서 느려진다. git + 자동 commit/push 스크립트가 답이다.

### 7.5 모바일에서의 한계

Obsidian 모바일 앱은 있지만, LLM 통합은 데스크톱이 중심이다. 모바일에서는 보통 "읽기/짧은 추가"만 하고, 정리/재작성은 데스크톱에서 한다. 이 경계를 명확히 두면 스트레스가 줄어든다.

---

## 8. 기존 PKM 진영과의 차이

Roam Research, Obsidian의 Zettelkasten 신봉자들, Logseq, Tana 진영은 "양방향 링크"와 "atomic note"를 종교처럼 여긴다. 한 메모는 하나의 원자적 개념을 담고, 메모끼리 링크로 엮어서 그래프를 만든다. 이걸 잘 만들면 본인의 "second brain"이 된다는 주장이다.

Karpathy의 관점은 본질적으로 이걸 부정한다.

- 사람이 손으로 link를 거는 비용이 너무 크다. 그래서 대부분의 사람은 vault를 만들고 6개월 뒤에 포기한다.
- LLM이 등장한 이후, link는 사후적으로 LLM이 만들어주면 된다. 사람이 매번 `[[wikilink]]` 칠 필요가 없다.
- atomic note에 집착할수록 한 메모를 작성하는 비용이 커진다. 그냥 길게 적고 LLM에게 "이 메모를 atomic으로 쪼개줘"라고 시키는 게 빠르다.

이 차이는 단순한 도구 선택이 아니라 PKM의 철학 자체를 바꾼다. **사전 구조화에서 사후 구조화로의 전환**이다. 작성 시점에는 마구잡이로 적고, 검색/질의/요약 시점에 LLM이 구조를 만들어낸다. 본인이 5년치 메모를 LLM 도입 전후로 비교해보면, 도입 후 메모량이 3배 늘었고 활용도도 더 높아졌다.

기존 진영의 반론도 일리는 있다. "LLM이 만들어준 정리본은 본인 사고가 아니다." 메모는 적는 행위 자체가 학습이다. LLM이 다 정리해주면 본인은 아무것도 학습하지 않은 채로 메모만 쌓인다. 이 비판은 진지하게 받아들여야 한다. 본인 경험으로는 "초안은 사람이 적고, 정리는 LLM이"라는 분업이 학습 효과를 가장 덜 해친다.

---

## 9. 5년차 백엔드 개발자가 적용할 때

PKM을 처음 시작하는 사람과, 이미 다른 도구로 운영 중인 사람은 접근이 다르다.

처음 시작하는 경우: 폴더 두 개(`daily/`, `notes/`)로 시작해라. 태그도 안 붙여도 된다. 한 달 적은 뒤 LLM에게 "내 메모를 보고 자주 등장하는 주제로 태그 후보를 뽑아줘"라고 시킨다. 그때부터 태그를 붙여도 늦지 않다.

이미 Notion으로 운영 중인 경우: export → 마크다운 변환 → vault에 통합이다. Notion export는 깨진 부분이 많아서 LLM에게 "이 파일을 깨끗한 마크다운으로 정리해줘"라고 시켜야 한다. 100개 단위로 나눠서 배치 처리하면 하루면 끝난다.

회사 메모와 개인 메모를 한 vault에 두느냐: 본인은 분리한다. `~/vault-personal`과 `~/vault-work`. 회사 vault는 회사 git, 개인 vault는 개인 git. LLM 호출 정책도 다르다. 회사 vault는 사내 프록시를 거치는 Anthropic API만, 개인 vault는 외부 직통 가능. 이 분리를 안 하면 언젠가 사고가 난다.

마지막으로, vault는 "지식의 무덤"이 되기 쉽다. 적기만 하고 다시 안 본다. LLM 통합의 가장 큰 가치는 이 무덤을 다시 살아있는 자료로 만든다는 점이다. 매일 작성한 메모가 매주 요약으로 응축되고, 그 요약이 다시 검색 가능한 영구 메모가 되는 흐름. 이 흐름이 돌아가야 vault는 죽지 않는다.
