---
title: Karpathy의 LLM + Obsidian 워크플로우
tags: [ai, llm]
updated: 2026-09-24
volatility: high
---

# Karpathy의 LLM + Obsidian 워크플로우

## Karpathy가 말한 것

Andrej Karpathy는 Tesla AI Director와 OpenAI 창립 멤버를 거친 인물이다. 본인 X(트위터)와 강연에서 개인 지식관리(PKM) 셋업을 여러 번 흘렸다. 핵심은 단순하다. **모든 메모를 로컬 마크다운 파일로 둔다.** 그 파일들을 LLM에게 컨텍스트로 던진다.

본인이 강조한 포인트는 대략 이렇다.

메모는 plain text 마크다운으로 둔다. 외부 SaaS에 묶이는 순간 10년 뒤에는 못 읽는다. 폴더 구조는 깊게 가지 않는다. 검색이 트리보다 빠르다. LLM이 등장한 이후, "정리"라는 작업의 비용이 사실상 0에 가까워졌다. 따라서 처음부터 잘 정리하려 하지 않고 일단 마구잡이로 적고 나중에 LLM에게 정리시킨다. Obsidian 자체에 종속되지 말아야 한다. Obsidian은 마크다운 파일을 보여주는 뷰어일 뿐이다. 내일 사라져도 vault는 살아남아야 한다.

이 관점이 기존 PKM 진영(Notion, Roam Research, Logseq, Tana)과 갈리는 지점이다. 기존 진영은 "구조"와 "양방향 링크"에 집착한다. Karpathy의 관점은 "구조 같은 건 LLM이 알아서 만들어주니, 너는 그냥 적기만 해라"에 가깝다.

---

## 왜 마크다운 vault인가

5년차 백엔드 개발자가 Notion, Confluence, Bear, Apple Notes를 거쳐 Obsidian으로 정착하는 이유는 거의 비슷하다. 이전 도구들이 망하거나, export가 깨지거나, 검색이 느리거나, 코드블록이 못생겨서다.

마크다운 vault의 실질적인 장점은 네 가지다.

**grep이 된다.** `rg "kafka rebalance"` 한 줄이면 vault 전체를 1초 안에 훑는다. Notion에서 같은 작업을 하려면 API 호출이 필요하고, 로컬 검색은 캐시된 페이지만 된다. 5년 누적된 메모에서 특정 장애 기록을 찾아야 할 때, grep이 안 되는 PKM은 도구로서 죽은 것과 같다.

**git이 된다.** vault 자체가 git 저장소다. 변경 이력, 브랜치, diff, blame이 전부 공짜로 따라온다. 메모를 잘못 지웠을 때 `git reflog`로 복구할 수 있다.

**LLM에 그대로 먹인다.** 마크다운은 LLM이 가장 자연스럽게 다루는 포맷이다. 헤딩, 리스트, 코드블록 구조를 그대로 인식한다. Notion의 JSON block 구조나 Roam의 outliner 구조는 토큰 낭비가 심하고, LLM이 다시 마크다운으로 바꿔서 처리해야 한다.

**종속이 없다.** Obsidian이 망해도, Logseq로 옮겨도, VSCode에서 열어도 동일하게 동작한다. 데이터 주권이 본인 하드디스크에 있다는 점은 PKM의 장기 운영에서 가장 중요한 요소다.

---

## Vault 실제 파일 구조

깊은 폴더 트리를 만들지 않는다. 실제로 쓰는 구조는 이렇다.

```
vault/
├── .obsidian/
│   ├── community-plugins.json
│   └── plugins/
│       ├── dataview/data.json
│       ├── templater-obsidian/data.json
│       └── obsidian-git/data.json
├── daily/
│   ├── 2026-09-24.md
│   └── 2026-09-23.md
├── notes/
│   ├── kafka-consumer-rebalance.md
│   ├── postgres-vacuum-tuning.md
│   └── redis-cluster-vs-sentinel.md
├── templates/
│   └── daily.md
├── projects/
│   └── ygstudy.md
└── inbox/
    └── (정리 안 된 잡탕)
```

`daily/` 파일은 frontmatter를 최소로 유지한다.

```markdown
---
date: 2026-09-24
tags: [daily]
---

09:30 standup
- auth 서비스 Redis 세션 만료 이슈 재현 못 함. 스테이징에서만 발생
- PostgreSQL vacuum full 실행 스케줄 잡을 것 → #task

14:00 Kafka consumer group lag 스파이크
lag이 갑자기 5000까지 튀었다가 내려갔다. 원인 미파악.
관련 노트: [[kafka-consumer-rebalance]]
```

`notes/` 파일은 영구 메모다. frontmatter에 관련 태그를 달고, 내용은 시간이 지나도 읽을 수 있게 정리한다.

```markdown
---
title: Kafka Consumer Rebalance 디버깅
tags: [kafka, backend]
updated: 2026-09-20
---

# Kafka Consumer Rebalance 디버깅

## 재현 조건

consumer group에서 멤버 수가 변하거나, `max.poll.interval.ms` 내에 poll을 못 하면
rebalance가 트리거된다.

실제로 겪은 케이스:
- 처리 로직에 외부 API 호출이 있었는데 타임아웃 30초 → rebalance 연속 발생
- 해결: 타임아웃을 8초로 줄이고 `max.poll.interval.ms`를 60000으로 조정

## 진단 커맨드

```bash
kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --group my-consumer-group
```

LAG 컬럼이 계속 늘어나면 consumer가 처리를 못 따라가는 것이다.
```

---

## 플러그인 설정

Obsidian 커뮤니티 플러그인 중 vault + LLM 워크플로우에 실제로 필요한 건 세 개다.

`.obsidian/community-plugins.json`에 활성화된 플러그인 목록이 들어간다.

```json
[
  "dataview",
  "templater-obsidian",
  "obsidian-git"
]
```

**Dataview 설정** (`.obsidian/plugins/dataview/data.json`)

```json
{
  "enableDataviewJs": true,
  "enableInlineDataview": true,
  "enableInlineDataviewJs": false,
  "inlineQueriesInCodeblocks": true,
  "renderNullAs": "-",
  "taskCompletionTracking": false,
  "refreshInterval": 2500,
  "maxRecursiveRenderDepth": 4
}
```

`enableDataviewJs: true`는 `dataviewjs` 코드블록에서 JS를 실행할 수 있게 한다. 커스텀 집계 쿼리를 짤 때 필요하다. 신뢰하는 vault에서만 켠다.

**Templater 설정** (`.obsidian/plugins/templater-obsidian/data.json`)

```json
{
  "trigger_on_file_creation": false,
  "auto_jump_to_cursor": true,
  "enable_system_commands": false,
  "templates_folder": "templates",
  "syntax_highlighting": true,
  "enabled_templates_hotkeys": [
    {
      "template": "templates/daily.md",
      "hotkey": []
    }
  ]
}
```

`enable_system_commands: false`가 기본값이다. 이걸 켜면 Templater 템플릿 안에서 셸 명령을 실행할 수 있는데, vault가 공유 환경에 있다면 보안 리스크가 생긴다.

daily 노트 템플릿 (`templates/daily.md`):

```markdown
---
date: <% tp.date.now("YYYY-MM-DD") %>
tags: [daily]
---

## <% tp.date.now("YYYY-MM-DD (ddd)") %>

<%*
const yesterday = tp.date.now("YYYY-MM-DD", -1);
tR += `이전: [[daily/${yesterday}]]`;
%>
```

**obsidian-git 설정** (`.obsidian/plugins/obsidian-git/data.json`)

```json
{
  "commitMessage": "vault: auto-commit {{date}}",
  "autoCommitMessage": "vault: auto-commit {{date}}",
  "commitDateFormat": "YYYY-MM-DD HH:mm:ss",
  "autoSaveInterval": 10,
  "autoPushInterval": 30,
  "pullBeforePush": true,
  "disablePush": false,
  "syncMethod": "merge"
}
```

`autoSaveInterval: 10`은 10분마다 자동 커밋이다. `autoPushInterval: 30`은 30분마다 자동 push. `syncMethod: "merge"`는 rebase 대신 merge를 쓴다. 여러 기기에서 동시에 쓰다가 충돌이 나면 rebase가 더 꼬인다.

---

## Dataview로 vault 탐색

Dataview는 vault를 데이터베이스처럼 쿼리할 수 있게 해준다. LLM에 던지기 전에 어떤 노트가 관련 있는지 먼저 파악하는 용도로 쓴다.

최근 수정된 `#kafka` 노트 찾기:

```dataview
TABLE file.mtime AS "수정일", tags
FROM #kafka
SORT file.mtime DESC
LIMIT 10
```

특정 기간 daily 노트 목록:

```dataview
LIST
FROM "daily"
WHERE file.day >= date(2026-09-01) AND file.day <= date(2026-09-24)
SORT file.day DESC
```

완료 안 된 task 전체 수집:

```dataview
TASK
FROM "daily"
WHERE !completed
SORT file.day DESC
```

이 쿼리들은 `notes/` 인덱스 파일에 박아두면 Obsidian에서 바로 렌더된다. "어떤 노트가 있지?" 확인할 때 grep보다 편하다.

DataviewJS로 태그별 노트 수를 세는 집계 쿼리:

```dataviewjs
const tagCount = {};
for (const page of dv.pages()) {
  for (const tag of (page.tags ?? [])) {
    tagCount[tag] = (tagCount[tag] ?? 0) + 1;
  }
}

const sorted = Object.entries(tagCount)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 20);

dv.table(["태그", "노트 수"], sorted);
```

---

## LLM 연결 방식

vault에 LLM을 붙이는 방식은 크게 세 가지다. 각각 트레이드오프가 다르다.

**Cursor / Claude Code에 vault 폴더 물리기.** 가장 단순한 방법이다. Cursor를 vault 디렉토리에서 열고, 채팅창에서 `@notes/kafka-consumer-rebalance.md`로 파일을 참조한다. Claude Code는 vault 디렉토리에서 `claude` 명령으로 시작하면 자동으로 `Glob`, `Grep`, `Read`를 써서 vault를 탐색한다. RAG를 본인이 구축할 필요가 없다. 단점은 vault 전체가 외부 API(Anthropic, OpenAI)로 흘러나간다는 점이다. 민감한 메모가 섞여 있다면 이 방식은 위험하다.

**로컬 LLM (Ollama, llama.cpp).** `ollama run llama3.1:70b`로 로컬 모델을 띄우고 vault를 컨텍스트로 던진다. 외부 망으로 데이터가 안 나간다는 점이 결정적인 장점이다. 민감한 일기, 회사 내부 문서를 다룰 때는 사실상 이 방식 외에는 답이 없다. 단점은 모델 품질이다. 70B 모델이라도 Claude Sonnet과 비교하면 한국어 요약/재작성 품질이 눈에 띄게 떨어진다. M2 Max 64GB 정도는 되어야 70B를 돌릴 수 있다. M1 Pro 16GB로는 8B 모델이 한계다.

**직접 짠 스크립트 + API.** vault에서 필요한 파일만 골라서 API로 보내는 스크립트다. 민감 파일을 코드 단계에서 필터링할 수 있고 비용 통제가 가능하다. 아래 섹션에서 Node.js 예제를 보여준다.

---

## Claude API 연동 코드

Node.js로 vault에서 마크다운을 읽어 Anthropic API로 보내는 예제다. 같은 vault 컨텍스트로 여러 번 질문할 때 비용을 줄이기 위해 프롬프트 캐싱을 적용했다.

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
    (n) => n.tags.includes(tag) || n.body.includes(`#${tag}`)
  );
}

function buildContext(notes: VaultNote[], maxBytes = 80_000): string {
  let total = 0;
  const parts: string[] = [];
  let skipped = 0;

  for (const n of notes) {
    if (total + n.bytes > maxBytes) {
      skipped++;
      continue;
    }
    parts.push(`<note path="${n.path}">\n${n.body}\n</note>`);
    total += n.bytes;
  }

  if (skipped > 0) {
    console.warn(`컨텍스트 한도 초과로 ${skipped}개 노트 제외됨`);
  }
  return parts.join("\n\n");
}

async function withRetry<T>(fn: () => Promise<T>, maxAttempts = 3): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (err) {
      if (attempt === maxAttempts) throw err;
      const delay = Math.pow(2, attempt) * 1000;
      console.warn(`재시도 ${attempt}/${maxAttempts - 1} (${delay}ms 후)`);
      await new Promise((r) => setTimeout(r, delay));
    }
  }
  throw new Error("unreachable");
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

  const response = await withRetry(() =>
    client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 4096,
      system: [
        {
          type: "text",
          text:
            "너는 사용자의 개인 vault에 저장된 메모를 읽고 질문에 답하는 보조 도구다. " +
            "메모에 없는 사실은 추측하지 말고 모른다고 답해라. " +
            "답변에 사용한 노트의 path를 인용해라.",
          cache_control: { type: "ephemeral" },
        },
      ],
      messages: [
        {
          role: "user",
          content: [
            {
              type: "text",
              text: `다음은 내 vault에서 #${tag} 태그가 붙은 노트다.\n\n${context}`,
              cache_control: { type: "ephemeral" },
            },
            {
              type: "text",
              text: `\n\n질문: ${question}`,
            },
          ],
        },
      ],
    })
  );

  const text = response.content
    .filter((b) => b.type === "text")
    .map((b) => (b as { type: "text"; text: string }).text)
    .join("\n");

  const usage = response.usage;
  console.log(
    `[캐시] 히트: ${usage.cache_read_input_tokens ?? 0} / 생성: ${usage.cache_creation_input_tokens ?? 0}`
  );
  console.log(text);
}

ask("Kafka consumer rebalance가 자주 일어나면 어떻게 디버깅했지?", "kafka");
```

이 코드의 핵심 결정 세 가지다.

`SENSITIVE_DIRS`로 민감 폴더를 코드 레벨에서 제외한다. 일기, 사람 메모, 비공개 폴더는 외부 API로 안 보낸다.

system prompt와 vault 컨텍스트 양쪽에 `cache_control: { type: "ephemeral" }`을 붙였다. 같은 tag의 노트를 연속으로 여러 번 질문할 때, 두 번째 호출부터 vault 컨텍스트를 다시 처리하지 않는다. 80KB 컨텍스트 기준으로 캐시 히트 시 비용이 약 90% 절감된다.

`buildContext`에서 byte 단위로 컨텍스트를 자르고, 잘린 노트 수를 경고로 출력한다. 조용히 잘리는 걸 막는다.

---

## LLM 연동 실패 사례

실제로 vault + LLM 연동을 운영하면서 겪은 실패들이다.

**컨텍스트 초과 후 조용한 잘림.**

`buildContext`에서 byte 한도를 안 뒀을 때, 80개 노트를 그대로 던졌더니 API가 200K 토큰 한도에서 조용히 잘랐다. LLM은 "뒤쪽 노트는 없다"는 사실을 모르고 답했다. 에러가 없었기 때문에 한참 뒤에 "왜 그 노트 내용을 모르지?"라고 의아해하면서 발견했다. 지금은 byte 체크 후 잘린 노트 수를 경고로 출력한다.

**inbox 자동 이동 스크립트가 wrong move를 냈다.**

LLM이 `inbox/2026-09-10.md`를 읽고 "이건 `notes/redis-session.md`와 합치면 좋겠다"고 판단해서 자동으로 이동시키는 스크립트를 만들었다. 3주 뒤에 inbox 파일 12개가 사라졌는데, 일부는 LLM이 판단을 잘못해서 엉뚱한 notes 파일에 합쳐져 있었다. git history로 복구했지만 원본 복구에 한 시간이 걸렸다. 지금은 자동 이동을 완전히 없앴다. LLM은 "이동 후보 목록"만 출력하고, 실행은 사람이 한다.

**노트 재작성 중 수치 변조.**

`notes/postgres-vacuum-tuning.md`를 재구성하도록 시켰을 때, 원본에 있던 `autovacuum_vacuum_scale_factor = 0.01`이 `0.1`로 바뀌어서 들어왔다. diff 없이 머지했다면 나중에 틀린 설정값으로 실수할 뻔했다. 재작성 결과는 무조건 diff로 검토해야 한다.

```bash
git diff HEAD notes/postgres-vacuum-tuning.md
```

수치, 커맨드, 코드블록 안의 값이 변경됐으면 원본과 대조한다.

**로컬 Ollama 모델이 한국어 노트에서 hallucination을 더 많이 냈다.**

llama3.1:70b로 한국어 메모를 처리할 때 요약 품질이 영어 대비 눈에 띄게 떨어졌다. "이번 주 작업 요약해줘"를 시켰을 때 실제 daily 노트에 없는 내용이 2~3개씩 끼어들었다. Claude Sonnet으로 같은 프롬프트를 돌렸을 때는 이런 현상이 거의 없었다. 민감하지 않은 업무 메모는 Anthropic API로, 일기·개인 메모는 Ollama로 처리하는 식으로 분리했다.

**API rate limit으로 배치 처리가 중간에 끊겼다.**

vault 초기 정리 작업으로 노트 340개를 배치 처리하다가 23번째에서 `RateLimitError`가 났다. retry 없이 짠 스크립트라 처음부터 다시 돌려야 했다. 지금은 지수 백오프를 넣고, 처리 완료된 파일 목록을 체크포인트 파일에 저장한다.

```typescript
const CHECKPOINT_FILE = "/tmp/vault-batch-checkpoint.json";

async function loadCheckpoint(): Promise<Set<string>> {
  try {
    const raw = await readFile(CHECKPOINT_FILE, "utf-8");
    return new Set(JSON.parse(raw));
  } catch {
    return new Set();
  }
}

async function saveCheckpoint(done: Set<string>) {
  await writeFile(CHECKPOINT_FILE, JSON.stringify([...done]));
}
```

---

## 워크플로우 패턴

실제로 vault + LLM을 어떻게 쓰는지가 중요하다. Karpathy가 직접 시연하지는 않았지만, 본인 발언과 커뮤니티에서 정착된 패턴이다.

**일일 메모 → 주간 요약.** 매일 `daily/2026-09-24.md`에 잡탕으로 적는다. 일요일 밤에 LLM에게 그 주의 7개 daily 파일을 던진다.

```
다음 7개 일일 메모를 읽고 아래를 추출해줘.
1. 이번 주 작업한 프로젝트와 진행 상황
2. 새로 배운 기술적 내용
3. 다음 주에 이어서 할 일
4. 영구 메모로 옮길 만한 주제 (notes/ 폴더 후보)
```

이 결과를 `weekly/2026-W39.md`로 저장한다. 한 달 뒤에는 4개의 weekly를 던져서 monthly를 만든다. 시간이 지날수록 정보가 압축되면서 검색 가능한 형태로 남는다.

**inbox 분류.** `inbox/`에 던진 잡문을 LLM이 읽고 적절한 위치로 옮길 후보를 제안한다. 위에서 말했듯 자동 이동은 안 한다. 판단은 LLM이 하지만 최종 이동은 사람이 한다.

**영구 메모 재작성.** `notes/kafka-consumer-rebalance.md`를 6개월 뒤에 다시 보면 누더기다. LLM에게 "이 파일을 다시 읽기 좋게 재구성해줘. 사실 관계는 절대 바꾸지 말고, 헤딩 구조와 문장 흐름만 손봐줘"라고 시킨다. 결과를 git diff로 확인하고 머지한다. 이 작업이 LLM 등장 전에는 1시간 걸렸는데 이제는 3분이다.

**질문에 vault로 답하기.** "우리가 작년에 Redis Sentinel 도입할 때 왜 Cluster 안 갔지?" 같은 질문이 떠올랐을 때, vault에 grep으로 관련 파일을 찾고 그걸 LLM에게 던지면서 질문한다. 본인의 과거 결정 기록이 본인의 질문에 답하는 구조다.

---

## 한계

**컨텍스트 비용.** vault가 커질수록 매 질문마다 컨텍스트로 던지는 양이 늘어난다. 1MB짜리 vault를 통째로 던지면 한 번에 $0.5 정도 깨진다. 하루에 10번 질문하면 한 달 $150이다. 태그/폴더로 검색 범위를 좁히거나, 임베딩 기반 검색을 앞단에 두면 된다. vault가 50MB 안 넘으면 grep + 태그 필터로 버틸 수 있다.

**민감 메모 분리.** 폴더로 분리하는 게 가장 단순하지만, 한 파일 안에 민감/비민감이 섞이는 경우가 생긴다. 회의록에 사람 이름이 박혀 있는 식이다. `journal/`, `people/`, `private/` 세 폴더를 만들고 코드 레벨에서 API 호출을 막는다. 완벽하지 않지만 사고를 한 단계 줄여준다.

**동기화.** vault를 여러 기기에서 쓰려면 동기화가 필요하다. iCloud, Dropbox, Syncthing, git 다 써봤는데 git이 가장 안정적이다. iCloud는 충돌 파일(`~conflict`)이 자꾸 생기고, Dropbox는 큰 vault에서 느려진다. obsidian-git 플러그인 + 자동 commit/push 스크립트가 답이다.

**모바일에서의 한계.** Obsidian 모바일 앱은 있지만, LLM 통합은 데스크톱이 중심이다. 모바일에서는 "읽기/짧은 추가"만 하고, 정리/재작성은 데스크톱에서 한다.

---

## PKM 진영과의 차이, 그리고 5년차 관점

Roam Research, Obsidian의 Zettelkasten 신봉자들, Logseq, Tana 진영은 "양방향 링크"와 "atomic note"를 종교처럼 여긴다. 한 메모는 하나의 원자적 개념을 담고, 메모끼리 링크로 엮어서 그래프를 만든다. 잘 만들면 본인의 "second brain"이 된다는 주장이다.

Karpathy의 관점은 이걸 부정한다. 사람이 손으로 link를 거는 비용이 너무 크다. 그래서 대부분의 사람은 vault를 만들고 6개월 뒤에 포기한다. LLM이 등장한 이후, link는 사후적으로 LLM이 만들어주면 된다. atomic note에 집착할수록 한 메모를 작성하는 비용이 커진다. 그냥 길게 적고 LLM에게 "이 메모를 atomic으로 쪼개줘"라고 시키는 게 빠르다.

이 차이는 단순한 도구 선택이 아니라 PKM 철학 자체를 바꾼다. **사전 구조화에서 사후 구조화로의 전환**이다. 작성 시점에는 마구잡이로 적고, 검색/질의/요약 시점에 LLM이 구조를 만들어낸다.

기존 진영의 반론도 일리는 있다. "LLM이 만들어준 정리본은 본인 사고가 아니다." 메모는 적는 행위 자체가 학습이다. LLM이 다 정리해주면 본인은 아무것도 학습하지 않은 채로 메모만 쌓인다. 본인 경험으로는 "초안은 사람이 적고, 정리는 LLM이"라는 분업이 학습 효과를 가장 덜 해친다.

PKM을 처음 시작하는 경우: 폴더 두 개(`daily/`, `notes/`)로 시작해라. 태그도 안 붙여도 된다. 한 달 적은 뒤 LLM에게 "내 메모를 보고 자주 등장하는 주제로 태그 후보를 뽑아줘"라고 시킨다. 그때부터 태그를 붙여도 늦지 않다.

이미 Notion으로 운영 중인 경우: export → 마크다운 변환 → vault 통합이다. Notion export는 깨진 부분이 많아서 LLM에게 "이 파일을 깨끗한 마크다운으로 정리해줘"라고 시켜야 한다. 100개 단위로 나눠서 배치 처리하면 하루면 끝난다.

회사 메모와 개인 메모를 한 vault에 두느냐: 분리한다. `~/vault-personal`과 `~/vault-work`. 회사 vault는 회사 git, 개인 vault는 개인 git. LLM 호출 정책도 다르다. 회사 vault는 사내 프록시를 거치는 Anthropic API만, 개인 vault는 외부 직통 가능. 이 분리를 안 하면 언젠가 사고가 난다.
