# 옵티마이저 (Optimizer)
- 데이터베이스 관리 시스템(DBMS)의 핵심 엔진으로, SQL 쿼리를 가장 효율적으로 실행할 수 있는 최적의 처리 경로를 생성하는 역할을 수행
- 컴퓨터의 두뇌가 CPU인 것처럼 DBMS의 두뇌는 옵티마이저라고 할 수 있음
- 개발자가 SQL을 작성하고 실행하면 즉시 실행되는 것이 아니라, 옵티마이저가 실행 계획을 세우게 됨
- 옵티마이저는 크게 규칙 기반 옵티마이저(Rule-Based Optimizer)와 비용 기반 옵티마이저(Cost-Based Optimizer)로 구분됨

## 옵티마이저의 주요 기능과 역할

### 1. 쿼리 분석(Statement Parsing)
- SQL 문장의 문법 검사 및 의미 분석 수행
- 테이블, 컬럼, 인덱스 등의 데이터베이스 객체 존재 여부 확인
- 사용자 권한 검증
- SQL 문장의 구조를 파싱하여 내부 표현으로 변환
- 쿼리 트리(Query Tree) 생성

### 2. 실행 계획 생성(Execution Plan Generation)
실행 계획 생성은 옵티마이저의 핵심 기능으로, SQL 쿼리를 가장 효율적으로 실행할 수 있는 방법을 결정하는 과정입니다. 이 과정은 마치 GPS가 최적의 경로를 찾는 것과 유사합니다.

#### 2.1 실행 계획의 기본 개념
- **정의**: SQL 쿼리를 실행하기 위한 단계별 처리 방법을 정의한 청사진
- **목적**: 최소한의 자원으로 최대한의 성능을 달성
- **구성 요소**: 테이블 접근 방법, 조인 방식, 정렬 방식, 필터 조건 등

#### 2.2 테이블 접근 방법 (Table Access Methods)
1. **전체 테이블 스캔 (Full Table Scan)**
   - 모든 데이터 블록을 순차적으로 읽는 방식
   - 적합한 경우:
     - 테이블이 작은 경우 (전체 데이터의 5-10% 이하)
     - WHERE 절의 조건이 인덱스를 사용할 수 없는 경우
     - 대부분의 행을 검색해야 하는 경우
   - 예시:
     ```sql
     SELECT * FROM employees WHERE salary > 1000;
     ```

2. **인덱스 스캔 (Index Scan)**
   - **인덱스 범위 스캔 (Index Range Scan)**
     - 특정 범위의 값을 검색할 때 사용
     - 예시:
       ```sql
       SELECT * FROM employees WHERE salary BETWEEN 3000 AND 5000;
       ```
   - **인덱스 고유 스캔 (Index Unique Scan)**
     - 단일 행을 검색할 때 사용
     - 예시:
       ```sql
       SELECT * FROM employees WHERE employee_id = 100;
       ```
   - **인덱스 스킵 스캔 (Index Skip Scan)**
     - 복합 인덱스의 첫 번째 컬럼이 WHERE 절에 없는 경우에도 사용 가능
     - 예시:
       ```sql
       -- (gender, salary) 복합 인덱스가 있는 경우
       SELECT * FROM employees WHERE salary > 5000;
       ```

#### 2.3 조인 방법 (Join Methods)
1. **중첩 루프 조인 (Nested Loop Join)**
   - 작은 테이블을 외부 테이블로 사용
   - 적합한 경우:
     - 조인 조건에 인덱스가 있는 경우
     - 결과 집합이 작은 경우
   - 예시:
     ```sql
     SELECT e.name, d.department_name
     FROM employees e
     JOIN departments d ON e.department_id = d.department_id;
     ```

2. **해시 조인 (Hash Join)**
   - 메모리에 해시 테이블을 생성하여 조인
   - 적합한 경우:
     - 대용량 테이블 간의 조인
     - 동등 조인(=) 조건
   - 예시:
     ```sql
     SELECT e.name, s.salary
     FROM employees e
     JOIN salaries s ON e.employee_id = s.employee_id;
     ```

3. **정렬 병합 조인 (Sort Merge Join)**
   - 양쪽 테이블을 정렬한 후 병합
   - 적합한 경우:
     - 대용량 테이블 간의 조인
     - 정렬된 데이터가 필요한 경우
   - 예시:
     ```sql
     SELECT e.name, s.salary
     FROM employees e
     JOIN salaries s ON e.employee_id = s.employee_id
     ORDER BY e.name;
     ```

#### 2.4 서브쿼리 처리 방식
1. **서브쿼리 언네스팅 (Subquery Unnesting)**
   - 서브쿼리를 조인으로 변환
   - 예시:
     ```sql
     -- 변환 전
     SELECT * FROM employees
     WHERE department_id IN (SELECT department_id FROM departments);
     
     -- 변환 후
     SELECT e.* FROM employees e
     JOIN departments d ON e.department_id = d.department_id;
     ```

2. **서브쿼리 머지 (Subquery Merging)**
   - 서브쿼리를 메인 쿼리와 병합
   - 예시:
     ```sql
     -- 변환 전
     SELECT e.*, (SELECT AVG(salary) FROM employees) as avg_salary
     FROM employees e;
     
     -- 변환 후
     SELECT e.*, avg_salary
     FROM employees e
     CROSS JOIN (SELECT AVG(salary) as avg_salary FROM employees) s;
     ```

#### 2.5 실행 계획 최적화 기법
1. **조인 순서 최적화**
   - 테이블 크기와 선택도를 고려한 조인 순서 결정
   - 작은 결과 집합을 먼저 처리하는 것이 유리
   - 예시:
     ```sql
     -- 최적화 전
     SELECT * FROM large_table l
     JOIN small_table s ON l.id = s.id;
     
     -- 최적화 후
     SELECT * FROM small_table s
     JOIN large_table l ON s.id = l.id;
     ```

2. **인덱스 선택 최적화**
   - 선택도가 높은 인덱스 우선 사용
   - 복합 인덱스의 컬럼 순서 고려
   - 예시:
     ```sql
     -- (last_name, first_name) 인덱스가 있는 경우
     SELECT * FROM employees
     WHERE last_name = 'Smith' AND first_name = 'John';
     ```

3. **정렬 최적화**
   - 인덱스를 활용한 정렬
   - 메모리 정렬 vs 디스크 정렬 결정
   - 예시:
     ```sql
     -- 인덱스를 활용한 정렬
     SELECT * FROM employees
     ORDER BY employee_id;  -- employee_id에 인덱스가 있는 경우
     ```

#### 2.6 실행 계획 생성 시 고려사항
1. **통계 정보 활용**
   - 테이블 크기
   - 컬럼 분포도
   - 인덱스 선택도
   - 데이터 블록 수

2. **시스템 리소스 고려**
   - 사용 가능한 메모리
   - CPU 코어 수
   - 디스크 I/O 성능
   - 네트워크 대역폭

3. **동시성 제어**
   - 락(Lock) 경합
   - 트랜잭션 격리 수준
   - 동시 접근 사용자 수

### 3. 실행 계획 평가(Execution Plan Evaluation)
- 각 실행 계획의 비용 계산
  - I/O 비용: 디스크 읽기/쓰기 작업 비용
  - CPU 비용: 연산 처리 비용
  - 메모리 사용량: 정렬, 해시 조인 등에 필요한 메모리
  - 네트워크 비용: 분산 데이터베이스 환경에서의 통신 비용
- 통계 정보 활용
  - 테이블의 행 수
  - 컬럼의 분포도
  - 인덱스의 선택도
  - 데이터 블록 수
- 비용 기반 최적화(Cost-Based Optimization) 수행
- 최적의 실행 계획 선택

### 4. 실행 계획 실행(Execution Plan Execution)
- 선택된 실행 계획에 따라 쿼리 실행
- 실행 중 모니터링 및 동적 최적화
- 결과 집합 생성 및 반환

## 옵티마이저의 최적화 기법

### 1. 규칙 기반 최적화(Rule-Based Optimization)
- 미리 정의된 우선순위 규칙에 따라 실행 계획 선택
- 통계 정보에 의존하지 않음
- 단순하고 예측 가능한 실행 계획 생성

### 2. 비용 기반 최적화(Cost-Based Optimization)
- 통계 정보를 기반으로 각 실행 계획의 비용 계산
- 가장 낮은 비용의 실행 계획 선택
- 더 정확하고 효율적인 실행 계획 생성 가능

### 3. 힌트(Hint) 사용
- 개발자가 옵티마이저에게 특정 실행 계획을 강제하는 방법
- 특수한 상황에서 성능 최적화에 활용
- 잘못된 사용은 오히려 성능 저하를 야기할 수 있음

## 옵티마이저 성능 향상 방법

### 1. 통계 정보 관리
- 정기적인 통계 정보 갱신
- 샘플링 크기 조정
- 히스토그램 생성

### 2. 인덱스 설계
- 적절한 인덱스 생성
- 복합 인덱스 설계
- 인덱스 선택도 고려

### 3. 쿼리 튜닝
- 효율적인 SQL 작성
- 적절한 조인 방법 선택
- 서브쿼리 최적화

### 4. 데이터베이스 파라미터 설정
- 메모리 크기 조정
- 병렬 처리 설정
- 버퍼 캐시 크기 조정

## 옵티마이저의 한계와 고려사항

### 1. 통계 정보의 정확성
- 오래된 통계 정보는 잘못된 실행 계획을 유발
- 데이터 분포의 급격한 변화는 성능 저하의 원인

### 2. 실행 계획의 복잡성
- 복잡한 쿼리는 많은 실행 계획 후보를 생성
- 최적의 실행 계획을 찾는 데 많은 시간 소요

### 3. 하드웨어 제약
- 메모리, CPU, I/O 자원의 제한
- 분산 환경에서의 네트워크 지연

### 4. 동시성 제어
- 여러 사용자의 동시 접근
- 락(Lock)과 블로킹(Blocking) 관리

## 결론
옵티마이저는 데이터베이스 성능의 핵심 요소로, 효율적인 실행 계획을 생성하여 쿼리 성능을 최적화하는 역할을 수행합니다. 이를 위해서는 정확한 통계 정보, 적절한 인덱스 설계, 효율적인 SQL 작성이 필요하며, 지속적인 모니터링과 튜닝이 요구됩니다.

```
[출처]
1. DB Optimizer(옵티마이저)|작성자 Sodam
2. Oracle Database Performance Tuning Guide
3. SQL Server Query Performance Tuning
```
