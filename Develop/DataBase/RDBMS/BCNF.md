---
title: BCNF
tags: [database, rdbms]
updated: 2026-07-28
---

# BCNF

BCNF(Boyce-Codd Normal Form)는 3NF보다 한 단계 엄격한 정규형이다. 조건은 단순하다. 릴레이션에 존재하는 모든 비자명 함수 종속 `X → Y`에서 X는 반드시 후보키여야 한다.

3NF는 이행 함수 종속을 제거하되, 결정자가 후보키의 일부인 경우를 허용한다. BCNF는 이 예외를 없앤다. 비자명 함수 종속의 결정자가 후보키가 아니면 무조건 위반이다.

## 3NF를 통과하지만 BCNF를 위반하는 상황

3NF와 BCNF의 차이는 후보키가 여러 개이고 그 후보키들이 속성을 공유할 때 나온다. 이 조건을 동시에 만족해야만 3NF는 통과하면서 BCNF는 위반되는 상황이 만들어진다.

교수 배정 릴레이션을 예로 든다.

```
속성: {학번, 과목명, 교수명}

비즈니스 규칙:
  - 학생은 한 과목에서 한 명의 교수에게만 배정된다
  - 교수는 한 과목만 담당한다 (다른 과목 겸임 없음)

함수 종속:
  {학번, 과목명} → 교수명   -- 학번과 과목명을 알면 담당 교수가 결정됨
  {학번, 교수명} → 과목명   -- 학번과 교수명을 알면 과목이 결정됨
  교수명 → 과목명           -- 교수명만 알면 과목이 결정됨 (한 과목만 담당)
```

후보키는 `{학번, 과목명}`과 `{학번, 교수명}` 두 개다. 두 후보키는 학번을 공유한다.

**3NF 검증**: 비기본키 속성(교수명, 과목명이 기본키가 아닌 경우)이 기본키가 아닌 속성에 의존하는 이행 종속이 있는가? 교수명은 `{학번, 과목명}`의 기본키에 종속되고, 과목명은 `{학번, 교수명}`에 종속된다. 기본키에 종속되므로 3NF는 통과한다.

**BCNF 검증**: `교수명 → 과목명`에서 결정자 '교수명'이 후보키인가? 교수명 하나만으로는 릴레이션의 모든 속성을 결정하지 못한다. 학번을 알 수 없다. 교수명은 후보키가 아니므로 BCNF 위반이다.

데이터로 보면 이 위반이 어떤 문제를 만드는지 보인다.

| 학번 | 과목명 | 교수명 |
|------|--------|--------|
| S001 | 데이터베이스 | 김교수 |
| S002 | 데이터베이스 | 김교수 |
| S003 | 알고리즘 | 이교수 |

신규 교수 박교수가 소프트웨어공학을 담당하게 됐는데 아직 배정된 학생이 없다. 이 릴레이션에 박교수 정보를 넣을 방법이 없다. 학번 없이는 행을 INSERT할 수 없기 때문이다(삽입 이상).

S001이 수강을 전부 취소하면 S001 행이 사라진다. 그 결과 김교수가 데이터베이스를 담당한다는 정보도 함께 사라질 수 있다(삭제 이상). 같은 과목에 다른 학생이 남아 있다면 보존되지만, 마지막 학생이 떠나면 교수 담당 과목 정보가 사라진다.

## BCNF 위반 판별

릴레이션이 BCNF를 위반하는지 판별하는 과정은 다음과 같다.

**1단계: 후보키를 모두 구한다**

함수 종속 집합 F에서 각 속성 집합의 클로저를 계산해서 후보키를 찾는다. 클로저가 릴레이션의 모든 속성을 포함하는 최소 속성 집합이 후보키다.

```
R = {A, B, C, D}
F = {A → B, B → C, A → D}

A+ = {A, B, C, D}  → A가 모든 속성을 결정 → A는 후보키 후보
B+ = {B, C}        → B만으로 모든 속성을 결정 못함
→ A가 후보키
```

**2단계: 비자명 함수 종속의 결정자를 확인한다**

F에 있는 모든 비자명 함수 종속 `X → Y`를 꺼낸다. Y가 X의 부분집합이면 자명한 종속이므로 건너뛴다. 나머지 각각에서 X가 후보키인지 확인한다.

```
교수 배정 예시에서:
후보키 = {{학번, 과목명}, {학번, 교수명}}

검사할 비자명 FD:
  {학번, 과목명} → 교수명    → 결정자가 후보키 → OK
  {학번, 교수명} → 과목명    → 결정자가 후보키 → OK
  교수명 → 과목명           → 결정자 '교수명'이 후보키인가?
    교수명+ = {교수명, 과목명}, 학번이 없음 → 후보키 아님 → BCNF 위반
```

**3단계: 위반 FD 기록**

BCNF를 위반하는 FD를 기록해 둔다. 분해 단계에서 이 FD를 기준으로 테이블을 나눈다.

## BCNF 분해

위반하는 FD `X → Y`를 찾으면 릴레이션을 두 개로 쪼갠다.

- R1 = X ∪ Y (위반 FD의 결정자와 종속 속성)
- R2 = R - Y + X (원래 릴레이션에서 Y를 빼고 X를 남긴 것)

R2에 X를 남기는 이유는 두 테이블을 JOIN할 때 연결 고리가 필요하기 때문이다.

교수 배정 예시에 적용한다. 위반 FD는 `교수명 → 과목명`이다.

```
R = {학번, 과목명, 교수명}
위반 FD: 교수명 → 과목명
  X = {교수명}, Y = {과목명}

R1 = {교수명} ∪ {과목명} = {교수명, 과목명}
R2 = {학번, 과목명, 교수명} - {과목명} + {교수명} = {학번, 교수명}
```

```sql
-- R1: 교수-과목 대응
CREATE TABLE professor_course (
    professor_name VARCHAR(50) PRIMARY KEY,
    course_name    VARCHAR(50) NOT NULL
);

-- R2: 학생-교수 배정
CREATE TABLE student_professor (
    student_id     BIGINT,
    professor_name VARCHAR(50) REFERENCES professor_course(professor_name),
    PRIMARY KEY (student_id, professor_name)
);
```

R1에서 professor_name이 기본키다. 교수는 한 과목만 담당하므로 professor_name → course_name이 성립하고, 결정자가 후보키다. R1은 BCNF를 만족한다.

R2에서 (student_id, professor_name)이 기본키다. 여기에는 다른 비자명 FD가 없다. R2도 BCNF를 만족한다.

분해 후 R1은 교수-담당과목 정보를 독립적으로 관리할 수 있다. 학생 배정 없이도 교수 정보를 INSERT할 수 있게 됐다.

**분해 과정을 반복한다**

R2가 여전히 BCNF를 위반하면 같은 과정을 반복한다. 위반하는 FD를 찾아서 다시 분해한다. 모든 분해 결과가 BCNF를 만족할 때까지 이어간다.

## 의존성 보존 실패

BCNF 분해의 핵심 문제는 의존성 보존(Dependency Preservation)이 깨진다는 점이다.

원래 릴레이션에 있던 FD `{학번, 과목명} → 교수명`이 분해 후 어느 테이블에도 단독으로 표현되지 않는다. student_professor에는 과목명이 없고, professor_course에는 학번이 없다. "학생 S001이 데이터베이스 과목에서 김교수에게 배정됐다"는 사실을 검증하려면 두 테이블을 JOIN해야 한다.

이게 실무에서 문제가 되는 이유가 있다. 새 데이터가 INSERT될 때 이 제약이 자동으로 검증되지 않는다. DB 레벨에서는 student_professor에 (S001, 이교수) 행을 넣는 것을 막을 수단이 없다. 이교수가 담당하는 과목과 S001이 수강하려는 과목이 맞는지 DB가 검증할 방법이 없다.

### 무결성 보완 방법

의존성이 깨진 부분을 어떻게 보완할지는 선택지가 있다.

**트리거**

원래 릴레이션에서 보존하려던 FD를 트리거로 구현한다.

```sql
-- student_professor INSERT 시 과목 일치 여부 검증
CREATE OR REPLACE FUNCTION check_student_course_assignment()
RETURNS TRIGGER AS $$
DECLARE
    assigned_course VARCHAR(50);
    enrolled_course VARCHAR(50);
BEGIN
    -- 해당 교수의 담당 과목 조회
    SELECT course_name INTO assigned_course
    FROM professor_course
    WHERE professor_name = NEW.professor_name;

    -- 학생이 수강 중인 과목 조회 (별도 수강신청 테이블이 있다고 가정)
    SELECT course_name INTO enrolled_course
    FROM course_enrollment
    WHERE student_id = NEW.student_id;

    IF assigned_course != enrolled_course THEN
        RAISE EXCEPTION '교수의 담당 과목과 학생의 수강 과목이 일치하지 않습니다.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_assignment
BEFORE INSERT OR UPDATE ON student_professor
FOR EACH ROW EXECUTE FUNCTION check_student_course_assignment();
```

트리거는 제약 조건처럼 동작하지만 명시적으로 보이지 않는다. 코드를 보는 사람이 이 제약 존재를 모르면 디버깅할 때 혼란이 생긴다. 대용량 배치 INSERT 시 트리거가 행 단위로 실행되면 성능 문제가 된다.

**애플리케이션 레벨 검증**

서비스 레이어에서 데이터를 쓰기 전에 FD가 보존되는지 검증한다.

```typescript
async function assignProfessorToStudent(
  studentId: number,
  professorName: string,
  enrolledCourse: string
): Promise<void> {
  const professorCourse = await this.professorCourseRepo.findOne({
    where: { professorName },
  });

  if (!professorCourse) {
    throw new Error(`교수 ${professorName}의 담당 과목 정보를 찾을 수 없습니다.`);
  }

  if (professorCourse.courseName !== enrolledCourse) {
    throw new Error(
      `교수 ${professorName}의 담당 과목은 ${professorCourse.courseName}입니다. ` +
      `수강 과목 ${enrolledCourse}와 다릅니다.`
    );
  }

  await this.studentProfessorRepo.save({ studentId, professorName });
}
```

애플리케이션 레벨 검증은 DB를 직접 건드리는 배치 스크립트나 마이그레이션에서 우회된다. DB 레벨 제약이 아니기 때문에 완전한 보장이 되지 않는다.

**CHECK 제약 활용**

일부 RDBMS는 서브쿼리가 포함된 CHECK 제약을 지원하지 않는다. PostgreSQL도 CHECK 내에서 다른 테이블을 참조하는 서브쿼리는 허용하지 않는다. 의존성 보존이 깨진 상황에서 CHECK 제약만으로는 테이블 간 일관성을 보장하기 어렵다.

현실적으로 가장 많이 쓰는 방법은 트리거와 애플리케이션 레벨 검증을 함께 쓰는 것이다. 트리거가 DB 레벨에서 마지막 방어선이 되고, 애플리케이션 레벨 검증이 사용자에게 더 명확한 오류 메시지를 제공한다.

## 실무에서 BCNF를 적용하지 않는 이유

BCNF 분해를 결정하기 전에 따져야 할 것들이 있다.

**의존성 보존 손실이 의미하는 비용**

의존성이 깨지면 그 종속 관계를 애플리케이션 또는 트리거로 유지해야 한다. 이 비용은 단순히 코드 몇 줄이 아니다. 어디선가 이 제약을 알고 있는 사람이 없으면 유지보수 중에 조용히 무너진다. 데이터 정합성 문제는 나중에야 발견되는 경우가 많다.

**JOIN 복잡도**

BCNF로 분해하면 테이블 수가 늘고 JOIN이 늘어난다. 특히 분해가 여러 단계로 이어지면 원래 엔티티를 복원하는 쿼리가 복잡해진다. 쿼리가 복잡해지면 실수하기 쉽고, ORM에서 관계를 올바르게 정의하지 않으면 N+1 문제나 잘못된 JOIN이 조용히 발생한다.

**BCNF 위반이 생기는 빈도**

후보키가 여러 개이고 겹치는 속성을 가지면서 비후보키 결정자가 있는 상황은 일반적인 CRUD 서비스에서 자주 나오지 않는다. 흔히 보이는 위반 사례는 대부분 3NF 위반(이행 종속)이다. 3NF까지 적용하면 삽입, 삭제, 갱신 이상 대부분이 제거된다.

**3NF의 장점**

3NF는 무손실 분해(Lossless Decomposition)와 의존성 보존을 동시에 보장한다. BCNF는 무손실 분해만 보장하고 의존성 보존은 보장하지 않는다. 의존성 보존이 가능한 3NF 분해가 존재하면 3NF를 선택하는 편이 설계 관리 비용이 낮다.

## 3NF vs BCNF 선택

BCNF를 선택하는 경우는 제한적이다.

이상 현상 제거가 최우선이고 의존성 보존이 필요 없는 상황이면 BCNF를 선택한다. 참조 무결성을 트리거나 애플리케이션 레벨로 관리할 여건이 있어야 한다.

3NF를 선택하는 경우는 의존성 보존이 중요할 때다. 팀 규모가 크거나 오래 유지보수할 시스템이라면 DB 레벨에서 제약이 명시적으로 보이는 3NF가 낫다. 트리거나 애플리케이션 코드로 숨겨진 제약을 관리하는 것은 장기적으로 부담이 된다.

3NF를 만족하는 분해 중에서 의존성을 보존하는 분해가 항상 존재한다. BCNF를 만족하는 분해는 항상 존재하지만 의존성을 보존하는 BCNF 분해는 존재하지 않을 수 있다.

```
판단 기준:

BCNF 선택:
  - 이상 현상(삽입/삭제/갱신)이 실제로 운영에 지장을 준다
  - 분해로 손실되는 의존성을 트리거나 서비스 코드로 대체할 수 있다
  - 쿼리 복잡도 증가를 수용할 수 있다

3NF 유지:
  - 의존성 보존이 중요하다 (DB 레벨 제약이 명시적이어야 한다)
  - 팀이 분산돼 있거나 시스템 유지 기간이 길다
  - 3NF 분해 후 이상 현상이 허용 가능한 수준이다
```

실무에서는 3NF까지 정규화하고, 그 이상의 이상 현상이 실제로 문제가 됐을 때 BCNF 분해를 검토한다. 이론적으로 더 완벽한 정규형보다 팀이 유지보수할 수 있는 설계가 낫다.
