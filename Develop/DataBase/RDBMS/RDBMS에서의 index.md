---
title: RDBMS에서의 Index
tags: [database, rdbms, index, performance, optimization, b-tree]
updated: 2024-12-19
---

# RDBMS에서의 Index

## 배경

### 인덱스란?
인덱스는 데이터베이스 테이블의 검색 성능을 향상시키기 위한 자료구조입니다.
책의 목차와 같이 특정 컬럼의 값을 기준으로 데이터를 빠르게 찾을 수 있게 해줍니다.
인덱스는 테이블과 별도의 저장 공간에 저장되며, 데이터의 물리적 위치를 가리키는 포인터를 포함합니다.
데이터베이스의 성능 최적화에서 가장 중요한 요소 중 하나입니다.

### 인덱스의 필요성
1. **데이터 접근 방식**
   - Table Full Scan: 테이블의 모든 데이터를 순차적으로 읽는 방식
   - Index Scan: 인덱스를 통해 필요한 데이터만 선택적으로 읽는 방식
   - Index Range Scan: 인덱스를 통해 특정 범위의 데이터를 읽는 방식

2. **인덱스의 물리적 구조**
   - 데이터 페이지: 실제 데이터가 저장되는 공간
   - 인덱스 페이지: 인덱스 데이터가 저장되는 공간
   - 페이지 링크: 페이지 간의 연결 정보

## 핵심

### 인덱스의 종류
1. **B-Tree 인덱스**
   - 가장 일반적으로 사용되는 인덱스 구조
   - 범위 검색과 정렬된 데이터 접근에 최적화
   - MySQL의 InnoDB, PostgreSQL 등에서 기본적으로 사용
   - 균형 트리 구조로 데이터의 삽입/삭제/수정 시 자동으로 균형을 맞춤
   - 각 노드는 여러 개의 키와 포인터를 가질 수 있음

2. **Hash 인덱스**
   - 해시 함수를 사용하여 데이터를 저장
   - 동등 비교(=) 연산에 매우 빠름
   - 범위 검색이나 정렬에는 적합하지 않음
   - MySQL의 Memory 스토리지 엔진에서 사용
   - 충돌 해결을 위한 체이닝이나 개방 주소법 사용

3. **Fractal 인덱스**
   - 프랙탈 기하학을 기반으로 한 인덱스 구조
   - 대용량 데이터 처리에 특화
   - 특수한 용도로 사용
   - 공간 데이터나 시계열 데이터에 효과적

4. **Full-Text 인덱스**
   - 텍스트 검색을 위한 특수 인덱스
   - 자연어 처리 기능 지원
   - MySQL의 FULLTEXT 인덱스, PostgreSQL의 GIN 인덱스 등

5. **Spatial 인덱스**
   - 공간 데이터를 위한 특수 인덱스
   - R-Tree 구조 사용
   - 위치 기반 검색에 최적화

### 인덱스의 장점
- **검색 성능 향상**
  - O(log n)의 시간 복잡도로 데이터 접근
  - 대용량 데이터에서 효과적
  - 특정 조건의 데이터 검색이 빠름

- **정렬 작업 최적화**
  - 인덱스는 이미 정렬된 상태
  - ORDER BY 작업이 인덱스 순서로 처리
  - 정렬 작업의 부하 감소

- **조인 연산 가속화**
  - 조인 조건의 컬럼에 인덱스가 있으면 효율적
  - Nested Loop Join에서 특히 효과적
  - 조인 성능 향상

- **유니크 제약 조건 강제**
  - 중복 데이터 방지
  - 데이터 무결성 보장
  - 유니크 인덱스로 구현

### 인덱스의 단점
- **저장 공간 증가**
  - 인덱스는 별도의 저장 공간 필요
  - 대용량 데이터에서는 상당한 공간 차지
  - 디스크 I/O 증가 가능성

- **삽입/수정/삭제 성능 저하**
  - 인덱스 구조 유지를 위한 추가 작업
  - B-Tree 재구성 비용
  - 동시성 제어 복잡성

- **관리 오버헤드**
  - 인덱스 유지보수 필요
  - 통계 정보 업데이트
  - 인덱스 조각화 관리

## 예시

### B-Tree 인덱스 스캔 과정
```javascript
// 인덱스 스캔 시뮬레이션
class BTreeIndex {
  constructor() {
    this.root = null;
  }
  
  // 인덱스 스캔 과정
  search(key) {
    console.log('1. 루트 노드 접근');
    let current = this.root;
    
    while (current) {
      console.log('2. 키 값 비교:', key, 'vs', current.key);
      
      if (key === current.key) {
        console.log('3. 리프 노드 도달 - 데이터 위치:', current.dataPointer);
        console.log('4. 데이터 읽기 완료');
        return current.dataPointer;
      } else if (key < current.key) {
        current = current.left;
      } else {
        current = current.right;
      }
    }
    
    console.log('데이터를 찾을 수 없습니다');
    return null;
  }
}

// 사용 예시
const index = new BTreeIndex();
index.search(42);
```

### 인덱스 생성 및 사용 예시
```sql
-- 사용자 테이블 생성
CREATE TABLE users (
  id INT PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(100),
  age INT,
  created_at TIMESTAMP
);

-- 단일 컬럼 인덱스 생성
CREATE INDEX idx_users_name ON users(name);
CREATE INDEX idx_users_email ON users(email);

-- 복합 인덱스 생성
CREATE INDEX idx_users_age_created ON users(age, created_at);

-- 부분 인덱스 (PostgreSQL)
CREATE INDEX idx_users_active ON users(email) WHERE active = true;

-- 유니크 인덱스
CREATE UNIQUE INDEX idx_users_email_unique ON users(email);

-- 인덱스 사용 예시
-- 인덱스 스캔이 발생하는 쿼리
SELECT * FROM users WHERE name = 'John Doe';
SELECT * FROM users WHERE age BETWEEN 20 AND 30;
SELECT * FROM users WHERE email LIKE 'john%';

-- 복합 인덱스 활용
SELECT * FROM users WHERE age = 25 ORDER BY created_at DESC;
```

### I/O 작업의 종류
```javascript
// 순차 I/O vs 랜덤 I/O 시뮬레이션
class IOOperation {
  // 순차 I/O (인덱스 범위 스캔)
  sequentialRead(startBlock, endBlock) {
    console.log('순차 I/O 시작');
    for (let i = startBlock; i <= endBlock; i++) {
      console.log(`블록 ${i} 읽기 - 연속된 데이터`);
    }
    console.log('순차 I/O 완료 - 효율적');
  }
  
  // 랜덤 I/O (인덱스를 통한 단일 레코드 조회)
  randomRead(blockNumbers) {
    console.log('랜덤 I/O 시작');
    blockNumbers.forEach(block => {
      console.log(`블록 ${block} 읽기 - 디스크 헤드 이동 필요`);
    });
    console.log('랜덤 I/O 완료 - 상대적으로 느림');
  }
}

// 사용 예시
const io = new IOOperation();
io.sequentialRead(1, 10);  // 연속된 블록 읽기
io.randomRead([1, 15, 7, 23, 4]);  // 불연속된 블록 읽기
```

### 인덱스 성능 비교
```javascript
// 인덱스 유무에 따른 성능 비교
class PerformanceTest {
  constructor() {
    this.data = this.generateTestData(1000000);
  }
  
  generateTestData(size) {
    const data = [];
    for (let i = 0; i < size; i++) {
      data.push({
        id: i,
        name: `User${i}`,
        email: `user${i}@example.com`,
        age: Math.floor(Math.random() * 50) + 18
      });
    }
    return data;
  }
  
  // 인덱스 없는 검색 (Table Full Scan)
  searchWithoutIndex(targetId) {
    console.time('인덱스 없는 검색');
    const result = this.data.find(item => item.id === targetId);
    console.timeEnd('인덱스 없는 검색');
    return result;
  }
  
  // 인덱스 있는 검색 (Index Scan)
  searchWithIndex(targetId) {
    console.time('인덱스 있는 검색');
    // B-Tree 인덱스 시뮬레이션 (실제로는 O(log n))
    const result = this.data[targetId]; // 단순화된 예시
    console.timeEnd('인덱스 있는 검색');
    return result;
  }
}

// 성능 테스트
const test = new PerformanceTest();
test.searchWithoutIndex(500000);  // 느림
test.searchWithIndex(500000);     // 빠름
```

## 운영 팁

### 인덱스 설계 원칙
1. **선택도(Selectivity) 고려**
   - 높은 선택도를 가진 컬럼을 인덱스로 선정
   - 예: 성별(2개 값)보다는 나이(다양한 값)가 더 좋은 인덱스

2. **복합 인덱스 설계**
   - 자주 함께 사용되는 컬럼들을 복합 인덱스로 구성
   - 등호 조건이 있는 컬럼을 앞에 배치

3. **인덱스 컬럼 순서**
   - 가장 자주 사용되는 조건을 앞에 배치
   - 범위 검색이 있는 컬럼은 뒤에 배치

### 인덱스 모니터링
```sql
-- MySQL 인덱스 사용 현황 확인
SHOW INDEX FROM users;
SELECT * FROM information_schema.statistics WHERE table_name = 'users';

-- PostgreSQL 인덱스 사용 현황 확인
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'users';

-- 인덱스 크기 확인
SELECT 
  table_name,
  index_name,
  ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.tables 
WHERE table_schema = 'your_database';
```

### 인덱스 최적화
```sql
-- 불필요한 인덱스 제거
DROP INDEX idx_unused_index ON users;

-- 인덱스 재구성 (MySQL)
OPTIMIZE TABLE users;

-- 인덱스 통계 업데이트 (PostgreSQL)
ANALYZE users;

-- 인덱스 조각화 확인
SELECT 
  table_name,
  index_name,
  cardinality,
  sub_part,
  packed,
  null,
  index_type
FROM information_schema.statistics 
WHERE table_schema = 'your_database';
```

## 참고

### 인덱스 관련 용어
- **Cardinality**: 인덱스에서 고유한 값의 개수
- **Selectivity**: 선택도, 인덱스의 효율성을 나타내는 지표
- **Covering Index**: 쿼리에서 필요한 모든 컬럼이 인덱스에 포함된 경우
- **Index Fragmentation**: 인덱스 조각화, 성능 저하의 원인

### 실제 사용 사례
1. **웹 애플리케이션**: 사용자 검색, 상품 검색
2. **로그 분석**: 날짜별, 시간별 데이터 조회
3. **게시판**: 제목, 작성자, 날짜별 검색
4. **쇼핑몰**: 카테고리, 가격, 브랜드별 상품 검색

### 결론
인덱스는 데이터베이스 성능 최적화의 핵심 요소입니다.
적절한 인덱스 설계와 관리를 통해 검색 성능을 크게 향상시킬 수 있습니다.
하지만 과도한 인덱스는 오히려 성능을 저하시킬 수 있으므로, 
실제 쿼리 패턴을 분석하여 필요한 인덱스만 생성하는 것이 중요합니다.






### B-Tree 인덱스의 상세 구조

#### 1. 노드의 구성
- **루트 노드(Root Node)**
  - 트리의 최상위 노드로, 전체 인덱스의 시작점
  - 항상 메모리에 캐시되어 있어 빠른 접근 가능
  - 브랜치 노드나 리프 노드로의 포인터 포함

- **브랜치 노드(Branch Node)**
  - 중간 단계의 노드들로, 자식 노드들의 범위 정보를 가짐
  - 키 값과 자식 노드 포인터의 쌍으로 구성
  - 페이지 분할과 병합이 발생할 수 있음

- **리프 노드(Leaf Node)**
  - 실제 데이터의 위치 정보를 저장하는 최하위 노드
  - 키 값과 실제 데이터 레코드의 포인터 포함
  - 양방향 링크로 연결되어 범위 스캔에 효율적

#### 2. 페이지(Page) 구조
- **페이지 크기**
  - 일반적으로 16KB (MySQL InnoDB 기준)
  - 운영체제의 페이지 크기와 맞추는 것이 좋음
  - 페이지 크기는 성능에 직접적인 영향

- **페이지 구성**
  - 페이지 헤더: 페이지의 메타데이터 저장
    - 페이지 타입, 이전/다음 페이지 포인터
    - 페이지 내 레코드 수, 최소/최대 키 값
  - 인덱스 레코드: 실제 인덱스 데이터
    - 키 값과 포인터의 쌍
    - 슬롯 디렉토리로 빠른 접근 지원
  - 페이지 푸터: 다음 페이지의 포인터 등
    - 체크섬, 페이지 상태 정보

#### 3. 인덱스 레코드 구조
- **키 값**
  - 인덱싱된 컬럼의 실제 값
  - 정렬된 순서로 저장
  - 중복 키 처리 방식 포함

- **포인터**
  - 실제 데이터 레코드의 위치 정보
  - 페이지 번호와 오프셋 정보
  - 클러스터링 여부에 따라 구조가 다름

- **트랜잭션 정보**
  - MVCC(Multi-Version Concurrency Control)를 위한 정보
  - 트랜잭션 ID, 롤백 포인터
  - 삭제 마커 등





