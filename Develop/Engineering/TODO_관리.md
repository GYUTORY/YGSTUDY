---
title: TODO 주석 관리 실무
tags: [backend, architecture, devops]
updated: 2026-09-10
---

# TODO 주석 관리

코드베이스에서 TODO 주석을 처음 grep 해보면 대부분 충격을 받는다. 수백 개가 쏟아지고, 그 중 절반은 작성자도 퇴사했고, 나머지 절반은 이미 해결됐는데 주석만 남아 있다.

이 문서는 TODO를 없애는 법이 아니다. **어떤 상황에서 어떤 태그를 써야 하는지, 그게 방치됐을 때 어떤 문제가 생기는지**를 다룬다.

## 태그 체계

IDE와 린터 대부분이 `TODO`, `FIXME`, `HACK`, `NOTE` 네 가지를 기본으로 인식한다. 팀 내에서 이 구분을 어떻게 정의하느냐에 따라 grep 결과의 신뢰도가 달라진다.

### TODO

아직 구현하지 않은 것. 지금 당장 문제는 없지만 나중에 해야 할 일이다.

```java
// TODO(김개발): 페이지네이션 추가. 현재는 최대 100건만 반환. PROJ-891
List<Order> orders = orderRepository.findAll();
```

괄호 안에 작성자나 담당자를 넣는 팀이 많다. 혼자 쓰는 저장소라면 의미 없지만, 팀 프로젝트에서는 "누구한테 물어봐야 하나"를 즉시 알 수 있다.

### FIXME

지금도 잘못 동작하거나, 특정 조건에서 확실히 깨진다는 걸 아는 것. TODO보다 급하다.

```python
# FIXME: timezone 없는 datetime이 들어오면 UTC로 처리된다.
# 프론트에서 로컬 시간을 그대로 보낼 때 1~9시간 오차 발생.
# 임시로 +09:00 가정하고 처리 중 — 근거 없는 가정이라 다국가 확장 시 터진다.
def parse_order_time(raw: str) -> datetime:
    return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
```

FIXME는 TODO와 달리 **지금 버그가 있다는 선언**이다. 리뷰에서 FIXME를 마주치면 "왜 이걸 머지했냐"는 질문이 나오기 때문에, 팀에 따라 FIXME가 있는 PR을 아예 머지 못하게 CI를 걸기도 한다.

### HACK

동작은 하지만 제대로 된 방법이 아니라는 걸 안다. 특정 외부 라이브러리 버그 우회, 레거시와의 호환성 유지 등이 여기 해당한다.

```go
// HACK: gorilla/mux 1.8.0에서 쿼리 파라미터가 있을 때 path matching이
// 깨지는 버그가 있다. 1.8.1에서 패치 예정이라고 이슈에 달려 있음.
// 업그레이드하면 이 라인 제거.
r.StrictSlash(true).PathPrefix("/api").Subrouter()
```

HACK을 쓸 때는 **왜 이 방법을 쓸 수밖에 없었는지**, 가능하면 **언제 제거할 수 있는지**까지 적어야 한다. 없으면 6개월 뒤에 이게 의도된 것인지 실수인지 알 수 없다.

### NOTE

이 코드를 이해하는 데 필요한 맥락. 나중에 할 것도, 지금 잘못된 것도 아니지만, 읽는 사람이 "왜 이렇게 했지?" 라고 고칠 가능성이 있는 부분이다.

```typescript
// NOTE: 여기서 async를 쓰지 않은 것은 실수가 아니다.
// Redis 클라이언트 초기화가 동기적으로 완료되어야 하는 의존성이 있다.
// async로 바꾸면 health check endpoint가 초기화 전에 응답할 수 있다.
const client = createClient({ url: process.env.REDIS_URL });
```

NOTE는 리뷰어에게 "이건 건드리지 마세요"를 전달하는 용도다. 없었다면 리뷰어가 "이거 왜 동기야?" 라는 코멘트를 달았을 것이다.

## TODO와 기술 부채의 차이

같아 보이지만 관리 방법이 다르다.

TODO 주석은 **코드를 읽는 사람에게 전달하는 메시지**다. 그 파일을 여는 사람만 본다.

기술 부채는 **팀 전체가 인식하고 우선순위를 매겨야 하는 작업**이다. 코드를 안 열어도 봐야 한다.

```
// TODO(박개발): 캐시 TTL을 설정 파일로 빼야 한다. PROJ-1122
const CACHE_TTL = 3600;
```

이 주석이 있다는 건 담당자가 있고, 이슈도 있다는 뜻이다. 이 정도면 된다. 하지만 이게 **기술 부채라면** 주석에 있으면 안 된다. 이슈 트래커에 있어야 하고, 스프린트 백로그에 있어야 하고, 영향도 분석이 달려 있어야 한다.

"나중에 리팩터링" 이라고 적힌 TODO가 기술 부채 관리의 전부인 팀이 있다. 그러면 회의에서 "기술 부채가 얼마나 됩니까?" 라는 질문에 grep 결과 개수로 답하게 된다. 그 숫자가 실제 부채와 관계없다는 걸 모두가 안다.

## 이슈 트래커 연동 패턴

가장 흔히 쓰는 패턴은 주석에 이슈 번호를 달고, CI에서 번호가 없는 TODO를 경고로 잡는 것이다.

### 이슈 번호 포함 강제

```yaml
# .github/workflows/todo-check.yml
- name: Check TODO without issue reference
  run: |
    # PROJ-숫자 형태의 참조가 없는 TODO/FIXME를 찾는다
    grep -rn 'TODO\|FIXME' --include="*.java" --include="*.kt" --include="*.py" . \
      | grep -v 'PROJ-[0-9]' \
      | grep -v 'node_modules' \
      | grep -v '\.git' \
      > /tmp/todo_without_issue.txt
    
    count=$(wc -l < /tmp/todo_without_issue.txt)
    if [ "$count" -gt 0 ]; then
      echo "이슈 번호 없는 TODO/FIXME ${count}건:"
      cat /tmp/todo_without_issue.txt
      exit 1
    fi
```

이걸 처음 도입하면 기존 코드에서 수백 개가 걸린다. 그 자리에서 다 고치려 하면 안 된다. **신규 추가 분만 잡는** 방식으로 시작하는 게 현실적이다.

```bash
# 변경된 파일에서만 확인
git diff --name-only origin/main | xargs grep -n 'TODO\|FIXME' \
  | grep -v 'PROJ-[0-9]'
```

### GitHub Issues 직접 연동

GitHub를 쓴다면 이슈 번호 대신 `#123` 형식으로 달아도 된다. GitHub가 코드 검색에서 이슈와 연결해 준다.

```python
# TODO: 응답 캐싱 추가 — #456
def get_user_profile(user_id: int):
    return db.query(User).filter(User.id == user_id).first()
```

다만 이슈가 닫혔는데 주석이 남아 있는 경우가 생긴다. 닫힌 이슈 번호를 코드에서 찾아내는 자동화를 추가하면 더 좋지만, 관리 비용 대비 효과를 따져봐야 한다.

## IDE별 지원

TODO를 파일마다 grep하는 건 불편하다. IDE가 이걸 모아서 보여준다.

### IntelliJ IDEA / Android Studio

기본으로 `TODO` 탭이 있다. `View > Tool Windows > TODO` 로 열면 프로젝트 전체 또는 현재 파일의 TODO를 목록으로 보여준다. 필터로 FIXME만, 또는 특정 파일 범위만 볼 수 있다.

커스텀 패턴 추가: `Preferences > Editor > TODO > +`로 팀 내부 태그(예: `PERF`, `SECURITY`)를 정규식으로 등록하면 같은 화면에서 보인다.

### VS Code

`Todo Tree` 확장을 설치하면 사이드바에서 태그별로 묶어 보여준다. `.vscode/settings.json`에 태그와 색을 지정할 수 있다.

```json
{
  "todo-tree.general.tags": ["TODO", "FIXME", "HACK", "NOTE", "PERF"],
  "todo-tree.highlights.customHighlight": {
    "FIXME": { "foreground": "#ff0000", "background": "#ffdddd" },
    "HACK": { "foreground": "#ff8800" }
  }
}
```

팀 저장소에 `.vscode/settings.json`을 커밋하면 팀원 모두가 같은 시각화를 쓴다.

### 커맨드라인 정기 확인

CI가 없거나, 전체 현황을 빠르게 보고 싶을 때 쓰는 방법이다.

```bash
# 태그별 개수
grep -rn 'TODO\|FIXME\|HACK\|NOTE' --include="*.java" --include="*.kt" src/ \
  | awk -F: '{
      if ($3 ~ /FIXME/) fixme++;
      else if ($3 ~ /HACK/) hack++;
      else if ($3 ~ /TODO/) todo++;
      else if ($3 ~ /NOTE/) note++;
    }
    END { printf "TODO:%d FIXME:%d HACK:%d NOTE:%d\n", todo, fixme, hack, note }'
```

## 방치됐을 때 실제로 생긴 문제들

### HACK이 코드베이스 전체로 퍼진 경우

결제 모듈에 외부 라이브러리 버그 우회용 HACK이 하나 들어갔다. 주석에는 "v2.3.1 버전 패치 예정" 이라고 적혀 있었다. 그 라이브러리는 한 달 뒤에 패치됐다. 하지만 아무도 그 주석을 다시 보지 않았다.

6개월 뒤 같은 로직이 필요한 신규 기능을 개발하던 팀원이 그 HACK 코드를 참고 삼아 복붙했다. 그다음 달에 또 다른 팀원이 복붙했다. 1년 뒤 HACK이 세 군데가 됐는데, 왜 이렇게 됐는지 아는 사람이 없었다.

**HACK은 제거 조건을 반드시 적어야 한다.** 조건이 충족됐을 때 누가 알아채고 없앨 것인지 구조가 있어야 한다.

### FIXME가 프로덕션으로 간 경우

어드민 대시보드에 다음 코드가 있었다.

```java
// FIXME: 권한 체크 빠짐. 임시로 admin role만 접근 가능하게 막아둠.
// 세분화 필요. PROJ-2287
if (!user.hasRole("ADMIN")) {
    throw new ForbiddenException();
}
```

PROJ-2287은 두 스프린트 뒤로 밀렸다가, 그다음 스프린트로 또 밀렸다가, 결국 백로그 하단에 가라앉았다. 그 사이에 기능이 빠르게 늘어났고, 모든 신규 기능이 ADMIN 체크 하나에 의존하는 구조가 됐다.

세분화 작업이 필요해졌을 때는 영향 범위가 너무 커서 한 스프린트에 할 수 없었다. 프리징 기간이 겹쳐서 또 밀렸다.

이 패턴이 위험한 이유는 **FIXME가 있다는 걸 알면서도 배포를 계속했기 때문에**, 팀이 FIXME를 "나중에 해결할 것"이 아니라 "이런 상태가 정상"으로 받아들이기 시작한다는 것이다.

### 작성자 퇴사 후 맥락이 사라진 경우

```python
# TODO(이개발): 이건 나중에 다시 보자
def calculate_discount(user, order):
    if user.created_at.year < 2022:
        return order.total * 0.15
    return order.total * 0.10
```

이 주석은 무엇을 말하는지 알 수 없다. 2022년 기준이 왜 있는지, 15%는 어디서 나온 숫자인지, "다시 보자"는 게 수정인지 확인인지 불명확하다. 이개발이 퇴사한 뒤 아무도 건드리지 않았고, 신입 개발자가 "이건 버그 같은데?" 라며 2022년 분기를 제거했다가 일부 구독자에게 할인이 사라지는 장애가 났다.

할인 정책 변경 당시 "구 회원에게는 기존 할인율 유지" 라는 기획 결정이 있었는데, 그게 코드에서 `0.15` 숫자 하나로만 남아 있었다.

## 태그를 고를 때

- **아직 없는 것**: TODO
- **지금 깨진 것, 또는 특정 조건에서 깨지는 것**: FIXME
- **동작은 하지만 제대로 된 방법이 아닌 것**: HACK
- **이 코드를 오해할 수 있어서 맥락을 남겨야 하는 것**: NOTE

태그 체계를 팀 내에서 통일하는 것보다 중요한 건 **이슈 번호를 함께 적는 습관**이다. 태그가 네 가지든 두 가지든, 번호가 없으면 주석이 티켓과 분리된다. 분리되면 grep 결과와 이슈 트래커가 따로 움직이고, 어느 쪽도 신뢰할 수 없게 된다.
