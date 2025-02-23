# 옵저버 패턴 (Observer Pattern) 👀

## 1. 옵저버 패턴이란?
**옵저버 패턴(Observer Pattern)** 은 객체 간의 **일대다(1:N) 관계를 형성하여, 특정 객체(Subject)의 상태 변화가 발생하면 연결된 여러 객체(Observer)들이 자동으로 변경을 감지**하도록 하는 디자인 패턴입니다.

- Node.js에서는 기본적으로 **이벤트 기반 아키텍처**를 사용하므로, 옵저버 패턴이 자주 활용됩니다.  
- 특히 `EventEmitter`를 사용하여 **효율적인 이벤트 처리 시스템**을 만들 수 있습니다.

---

## 2. Node.js에서 옵저버 패턴 활용 ✨

### 📌 `EventEmitter`를 활용한 기본 옵저버 패턴 구현

```javascript
// events 모듈 가져오기
const EventEmitter = require('events');

// 새로운 EventEmitter 인스턴스 생성
class MyEmitter extends EventEmitter {}

// 인스턴스 생성
const myEmitter = new MyEmitter();

// 이벤트 리스너 등록
myEmitter.on('event', () => {
    console.log('이벤트가 발생했습니다!');
});

// 이벤트 발생시키기
myEmitter.emit('event'); // "이벤트가 발생했습니다!"
```

> - `EventEmitter` 클래스를 상속받아 `MyEmitter`를 생성
> - `on(event, callback)`을 이용해 이벤트 리스너를 등록
> - `emit(event)`을 이용해 이벤트를 발생

---

## 3. 옵저버 패턴을 활용한 실전 예제

### 📌 사용자 로그인 이벤트 처리 시스템 만들기

```javascript
const EventEmitter = require('events');

// 사용자 로그인 이벤트를 관리할 클래스 생성
class User extends EventEmitter {
    login(username) {
        console.log(`${username}님이 로그인했습니다.`);
        
        // 로그인 이벤트 발생
        this.emit('login', username);
    }
}

// 새로운 User 인스턴스 생성
const user = new User();

// 옵저버(리스너) 추가: 로그인 시 이메일 알림 발송
user.on('login', (username) => {
    console.log(`📧 ${username}님에게 로그인 알림 이메일을 보냈습니다.`);
});

// 옵저버(리스너) 추가: 로그인 시 데이터베이스 업데이트
user.on('login', (username) => {
    console.log(`💾 ${username}님의 로그인 정보를 데이터베이스에 저장했습니다.`);
});

// 사용자 로그인 실행
user.login("철수");

/*
출력:
철수님이 로그인했습니다.
📧 철수님에게 로그인 알림 이메일을 보냈습니다.
💾 철수님의 로그인 정보를 데이터베이스에 저장했습니다.
*/
```

> **설명**
> - `User` 클래스는 `EventEmitter`를 상속받아 로그인 이벤트를 처리
> - `login(username)` 메서드 실행 시, `'login'` 이벤트 발생
> - `'login'` 이벤트를 감지하여 **이메일 알림**과 **데이터베이스 저장**을 수행

---

## 4. 여러 개의 이벤트 리스너 등록하기

### 📌 한 이벤트에 여러 개의 리스너 추가

```javascript
const EventEmitter = require('events');
const myEmitter = new EventEmitter();

// 첫 번째 리스너
myEmitter.on('data', (msg) => {
    console.log(`첫 번째 리스너: ${msg}`);
});

// 두 번째 리스너
myEmitter.on('data', (msg) => {
    console.log(`두 번째 리스너: ${msg}`);
});

// 이벤트 발생
myEmitter.emit('data', 'Hello, World!');

/*
출력:
첫 번째 리스너: Hello, World!
두 번째 리스너: Hello, World!
*/
```

> - **같은 이벤트(`'data'`)에 여러 개의 리스너를 등록** 가능
> - `emit('data', 'Hello, World!')` 호출 시, **모든 리스너가 실행됨**

---

## 5. 한 번만 실행되는 이벤트 리스너 (`once`)

`once(event, callback)` 메서드를 사용하면 **이벤트가 한 번만 실행되고 자동으로 제거**됩니다.

```javascript
const EventEmitter = require('events');
const myEmitter = new EventEmitter();

// 한 번만 실행되는 리스너 등록
myEmitter.once('message', (msg) => {
    console.log(`📢 한 번만 실행됨: ${msg}`);
});

// 이벤트 발생
myEmitter.emit('message', '안녕하세요!'); // 실행됨
myEmitter.emit('message', '다시 실행됩니다!'); // 실행되지 않음
```

> **설명**
> - `once('message', callback)`을 사용하여 **이벤트가 한 번만 실행되도록 제한**
> - 두 번째 `emit('message', '다시 실행됩니다!')`는 실행되지 않음

---

## 6. 이벤트 리스너 제거하기

이벤트 리스너를 제거하는 방법도 알아두면 좋습니다.

### 📌 특정 이벤트 리스너 제거 (`removeListener`)

```javascript
const EventEmitter = require('events');
const myEmitter = new EventEmitter();

// 이벤트 리스너 함수 정의
function greet(name) {
    console.log(`👋 안녕하세요, ${name}님!`);
}

// 이벤트 등록
myEmitter.on('greet', greet);

// 이벤트 실행
myEmitter.emit('greet', '지민'); // "👋 안녕하세요, 지민님!"

// 리스너 제거
myEmitter.removeListener('greet', greet);

// 다시 이벤트 실행 (리스너가 제거되었으므로 실행되지 않음)
myEmitter.emit('greet', '지민');
```

> - `removeListener(event, listener)`를 사용하면 특정 리스너만 제거 가능

### 📌 모든 리스너 제거 (`removeAllListeners`)

```javascript
const EventEmitter = require('events');
const myEmitter = new EventEmitter();

myEmitter.on('data', (msg) => console.log(`📩 데이터 수신: ${msg}`));
myEmitter.on('data', (msg) => console.log(`📩 추가 처리: ${msg}`));

// 모든 'data' 이벤트 리스너 제거
myEmitter.removeAllListeners('data');

// 이벤트 실행 (리스너가 모두 제거되었으므로 아무것도 출력되지 않음)
myEmitter.emit('data', '새로운 메시지');
```

> - `removeAllListeners(event)`를 사용하면 **특정 이벤트의 모든 리스너 제거 가능**

