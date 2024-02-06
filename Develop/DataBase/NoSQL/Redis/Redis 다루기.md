

## Nodejs로 알아보는 Redis 사용기 

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



