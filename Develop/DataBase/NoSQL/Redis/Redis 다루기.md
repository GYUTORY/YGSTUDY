# Redis 완벽 가이드: Node.js에서 Redis 활용하기

## Redis란?
Redis(Remote Dictionary Server)는 오픈소스 인메모리 데이터 구조 저장소입니다. 문자열, 해시, 리스트, 셋, 정렬된 셋 등 다양한 데이터 타입을 지원하며, 빠른 읽기/쓰기 성능을 제공합니다.

### Redis의 주요 특징
- 인메모리 데이터 저장으로 빠른 성능
- 다양한 데이터 타입 지원
- 영구성(Persistence) 지원
- 복제(Replication) 기능
- 트랜잭션 지원
- Pub/Sub 메시징 지원

### Redis의 주요 사용 사례
1. 캐싱
2. 세션 저장소
3. 실시간 분석
4. 메시지 큐
5. 실시간 순위표
6. 위치 기반 서비스

## Node.js에서 Redis 시작하기

### 1. 설치 및 기본 설정

```bash
# Redis 서버 설치 (MacOS)
brew install redis

# Redis 서버 실행
brew services start redis

# Node.js Redis 클라이언트 설치
npm install redis
```

### 2. 기본 연결 설정

```javascript
const redis = require('redis');

// 기본 연결
const client = redis.createClient();

// 커스텀 설정으로 연결
const client = redis.createClient({
    host: 'localhost',
    port: 6379,
    password: 'your_password', // 필요한 경우
    db: 0, // 데이터베이스 번호
    retry_strategy: function(options) {
        if (options.error && options.error.code === 'ECONNREFUSED') {
            return new Error('Redis 서버 연결 실패');
        }
        if (options.total_retry_time > 1000 * 60 * 60) {
            return new Error('재시도 시간 초과');
        }
        if (options.attempt > 10) {
            return undefined;
        }
        return Math.min(options.attempt * 100, 3000);
    }
});

// 연결 이벤트 핸들링
client.on('connect', () => {
    console.log('Redis 서버에 연결되었습니다.');
});

client.on('error', (err) => {
    console.error('Redis 연결 에러:', err);
});

client.on('ready', () => {
    console.log('Redis 클라이언트가 준비되었습니다.');
});

client.on('end', () => {
    console.log('Redis 연결이 종료되었습니다.');
});
```

## Redis 데이터 타입 상세 가이드

### 1. Strings (문자열)
가장 기본적인 데이터 타입으로, 텍스트, 숫자, 바이너리 데이터를 저장할 수 있습니다.

```javascript
// 기본 문자열 조작
client.set('key', 'value', 'EX', 3600); // 1시간 후 만료
client.get('key', (err, reply) => {
    console.log(reply); // 'value'
});

// 증감 연산
client.incr('counter'); // 1 증가
client.decr('counter'); // 1 감소
client.incrby('counter', 10); // 10 증가

// 문자열 조작
client.append('key', 'append'); // 문자열 추가
client.strlen('key'); // 문자열 길이
client.getrange('key', 0, 2); // 부분 문자열 추출
```

### 2. Lists (리스트)
순서가 있는 문자열 컬렉션입니다. 큐나 스택으로 활용할 수 있습니다.

```javascript
// 리스트 조작
client.lpush('list', 'first'); // 왼쪽에 추가
client.rpush('list', 'last'); // 오른쪽에 추가
client.lpop('list'); // 왼쪽에서 제거
client.rpop('list'); // 오른쪽에서 제거

// 리스트 범위 조회
client.lrange('list', 0, -1); // 전체 리스트 조회
client.ltrim('list', 0, 2); // 리스트 자르기

// 블로킹 연산
client.blpop('list', 10); // 10초 동안 대기하며 왼쪽에서 제거
client.brpop('list', 10); // 10초 동안 대기하며 오른쪽에서 제거
```

### 3. Sets (집합)
중복되지 않는 문자열의 무순서 컬렉션입니다.

```javascript
// 집합 조작
client.sadd('set', 'member1', 'member2');
client.srem('set', 'member1');
client.sismember('set', 'member1'); // 멤버 존재 여부 확인

// 집합 연산
client.sunion('set1', 'set2'); // 합집합
client.sinter('set1', 'set2'); // 교집합
client.sdiff('set1', 'set2'); // 차집합

// 집합 정보
client.scard('set'); // 크기
client.smembers('set'); // 모든 멤버
```

### 4. Hashes (해시)
필드와 값의 쌍으로 이루어진 컬렉션입니다.

```javascript
// 해시 조작
client.hset('hash', 'field', 'value');
client.hget('hash', 'field');
client.hmset('hash', {
    'field1': 'value1',
    'field2': 'value2'
});
client.hmget('hash', 'field1', 'field2');

// 해시 필드 관리
client.hdel('hash', 'field');
client.hexists('hash', 'field');
client.hlen('hash'); // 필드 수
client.hkeys('hash'); // 모든 필드
client.hvals('hash'); // 모든 값
```

### 5. Sorted Sets (정렬된 집합)
점수와 멤버로 구성된 정렬된 컬렉션입니다.

```javascript
// 정렬된 집합 조작
client.zadd('sortedset', 1, 'member1', 2, 'member2');
client.zrange('sortedset', 0, -1); // 점수 순으로 조회
client.zrevrange('sortedset', 0, -1); // 역순으로 조회

// 점수 기반 연산
client.zscore('sortedset', 'member1'); // 특정 멤버의 점수
client.zrank('sortedset', 'member1'); // 특정 멤버의 순위
client.zcount('sortedset', 0, 10); // 점수 범위 내 멤버 수
```

## Redis 모범 사례

### 1. 키 설계
- 의미 있는 네이밍 컨벤션 사용
- 콜론(:)으로 키 구분
- 적절한 만료 시간 설정

```javascript
// 좋은 키 설계 예시
client.set('user:1000:profile', '...');
client.set('session:1000:token', '...', 'EX', 3600);
client.set('article:1000:views', '0');
```

### 2. 성능 최적화
- 파이프라이닝 사용
- 적절한 데이터 타입 선택
- 키 만료 시간 설정

```javascript
// 파이프라이닝 예시
const pipeline = client.pipeline();
pipeline.set('key1', 'value1');
pipeline.set('key2', 'value2');
pipeline.exec((err, results) => {
    console.log(results);
});
```

### 3. 에러 처리
```javascript
client.on('error', (err) => {
    console.error('Redis 에러:', err);
    // 재연결 로직
});

// 명령어 실행 시 에러 처리
client.set('key', 'value', (err, reply) => {
    if (err) {
        console.error('명령어 실행 에러:', err);
        return;
    }
    console.log('성공:', reply);
});
```

## Redis 트랜잭션

```javascript
// 트랜잭션 예시
client.multi()
    .set('key1', 'value1')
    .set('key2', 'value2')
    .exec((err, replies) => {
        if (err) {
            console.error('트랜잭션 실패:', err);
            return;
        }
        console.log('트랜잭션 성공:', replies);
    });
```

## Redis Pub/Sub

```javascript
// 발행자
const publisher = redis.createClient();
publisher.publish('channel', 'message');

// 구독자
const subscriber = redis.createClient();
subscriber.subscribe('channel');
subscriber.on('message', (channel, message) => {
    console.log(`채널 ${channel}에서 메시지 수신: ${message}`);
});
```

## Redis 보안

### 1. 인증
```javascript
const client = redis.createClient({
    password: 'your_strong_password'
});
```

### 2. SSL/TLS
```javascript
const client = redis.createClient({
    tls: {
        rejectUnauthorized: false
    }
});
```

## Redis 모니터링

```javascript
// Redis 정보 조회
client.info((err, info) => {
    console.log('Redis 서버 정보:', info);
});

// 메모리 사용량
client.info('memory', (err, memory) => {
    console.log('메모리 사용량:', memory);
});

// 클라이언트 목록
client.client('list', (err, clients) => {
    console.log('연결된 클라이언트:', clients);
});
```

## 결론
Redis는 다양한 데이터 타입과 기능을 제공하는 강력한 인메모리 데이터 저장소입니다. Node.js와 함께 사용하면 빠른 성능과 유연한 데이터 처리가 가능합니다. 적절한 데이터 타입 선택과 모범 사례를 따르면 더욱 효율적인 Redis 활용이 가능합니다.

```javascript
// index.js

const redis = require('redis');
const client = redis.createClient();

// Redis 서버 연결 확인
client.on('connect', () => {
    console.log('Connected to Redis server');
});

// Redis 서버 연결 실패 시
client.on('error', (err) => {
    console.error(`Error connecting to Redis: ${err}`);
});

// 데이터 쓰기
client.set('example_key', 'Hello, Redis!', (err, reply) => {
    if (err) {
        console.error(`Error writing to Redis: ${err}`);
    } else {
        console.log(`Data written to Redis: ${reply}`);
    }
});

// 데이터 읽기
client.get('example_key', (err, reply) => {
    if (err) {
        console.error(`Error reading from Redis: ${err}`);
    } else {
        console.log(`Data read from Redis: ${reply}`);
    }
    // Redis 연결 종료
    client.quit();
});


```

---

### 데이터 타입별 Redis 사용법 

#### 1. Strings (문자열)

```javascript
// 문자열 저장
client.set('user:1:name', 'John Doe', (err, reply) => {
    if (err) {
        console.error(`Error setting string value: ${err}`);
    } else {
        console.log(`String value set: ${reply}`);
    }
});

// 문자열 조회
client.get('user:1:name', (err, reply) => {
    if (err) {
        console.error(`Error getting string value: ${err}`);
    } else {
        console.log(`String value retrieved: ${reply}`);  // 출력결과: John Doe
    }
});

```

#### 2. Lists (리스트)

```javascript
// 리스트에 값 추가
client.rpush('user:1:friends', 'Alice', 'Bob', 'Charlie', (err, reply) => {
    if (err) {
        console.error(`Error pushing to list: ${err}`);
    } else {
        console.log(`Values pushed to list: ${reply}`);
    }
});

// 리스트에서 값 가져오기
client.lrange('user:1:friends', 0, -1, (err, reply) => {
    if (err) {
        console.error(`Error getting list values: ${err}`);
    } else {
        console.log(`List values retrieved: ${reply}`); // 출력결과: ['Alice', 'Bob', 'Charlie']
    }
});

```

#### 3. Sets (집합)

```javascript
// 해시에 필드-값 쌍 추가
client.hset('user:1:profile', 'age', 30, (err, reply) => {
    if (err) {
        console.error(`Error setting hash field: ${err}`);
    } else {
        console.log(`Hash field set: ${reply}`); // 출력결과: 1
    }
});

// 해시에서 필드-값 쌍 조회
client.hget('user:1:profile', 'age', (err, reply) => {
    if (err) {
        console.error(`Error getting hash field: ${err}`);
    } else {
        console.log(`Hash field retrieved: ${reply}`); // 출력결과: 30
    }
});
```

#### 4. Sets (해시)

```javascript
// 해시에 값 추가
client.hmset('user:1:info', 'name', 'John Doe', 'age', 30, 'city', 'New York', (err, reply) => {
if (err) {
console.error(`Error adding to hash: ${err}`);
} else {
console.log(`Values added to hash: ${reply}`); // 출력결과: OK
}
});

// 해시에서 값 가져오기
client.hgetall('user:1:info', (err, reply) => {
if (err) {
console.error(`Error getting hash values: ${err}`);
} else {
console.log(`Hash values retrieved: ${JSON.stringify(reply)}`); // 출력결과: {"name":"John Doe","age":30,"city":"New York"}
}
});
```

#### 5. Sorted Sets (정렬된 집합)

```javascript
// 집합에 값 추가
client.sadd('user:1:hobbies', 'Reading', 'Swimming', 'Cycling', (err, reply) => {
    if (err) {
        console.error(`Error adding to set: ${err}`);
    } else {
        console.log(`Values added to set: ${reply}`);
    }
});

// 집합에서 값 가져오기
client.smembers('user:1:hobbies', (err, reply) => {
    if (err) {
        console.error(`Error getting set values: ${err}`);
    } else {
        console.log(`Set values retrieved: ${reply}`);
    }
});

```

---

### Redis hmset과 hset의 차이점 비교 

#### Redis hmset과 hset의 차이점 비교
##### 1. 명령어
- hmset: 하나의 명령으로 여러 개의 필드-값 쌍을 해시에 설정합니다.
- hset: 한 번에 하나의 필드-값 쌍을 해시에 설정합니다.

```javascript
// hmset 예시
const user = {
  name: "John Doe",
  age: 30,
  city: "New York",
};

client.hmset("user:1", user, (err, reply) => {
  if (err) {
    console.error(`Error setting hash: ${err}`);
  } else {
    console.log(`Values added to hash: ${reply}`); // 출력결과: OK
  }
});

// hset 예시
client.hset("user:1", "name", "John Doe", (err, reply) => {
  if (err) {
    console.error(`Error setting hash field: ${err}`);
  } else {
    console.log(`Hash field set: ${reply}`); // 출력결과: 1 (새로운 필드가 생성된 경우) 또는 0 (기존 필드가 업데이트된 경우)
  }
});

client.hset("user:1", "age", 30, (err, reply) => {
  if (err) {
    console.error(`Error setting hash field: ${err}`);
  } else {
    console.log(`Hash field set: ${reply}`); // 출력결과: 0 (기존 필드가 업데이트된 경우)
  }
});

```



