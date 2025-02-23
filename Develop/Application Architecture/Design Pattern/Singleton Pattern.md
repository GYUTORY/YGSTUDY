

# 🚀 Singleton Pattern(싱글톤 패턴) 개념과 예제

## ✨ 싱글톤 패턴이란?
싱글톤 패턴(Singleton Pattern)은 **어떤 클래스가 단 하나의 인스턴스만 가지도록 보장하는 디자인 패턴**이다.  
즉, **객체가 한 번만 생성되고 이후에는 같은 인스턴스를 공유**하도록 하는 방식이다.

---

## 🎯 싱글톤 패턴의 특징

✅ **유일한 인스턴스**: 같은 객체를 여러 번 생성하지 않고, 한 번만 생성하여 공유  
✅ **전역 접근 가능**: 프로그램 어디서든 동일한 인스턴스에 접근 가능  
✅ **메모리 절약**: 불필요한 객체 생성을 방지하여 성능 최적화 가능

---

## 🌐 언제 싱글톤 패턴을 사용할까?
다음과 같은 경우 싱글톤 패턴을 사용하면 좋다.

1️⃣ **데이터베이스 연결 관리**: 같은 연결을 여러 번 만들 필요 없이 하나만 유지  
2️⃣ **로그 관리**: 동일한 로그 객체를 사용하여 로그 기록을 일관되게 관리  
3️⃣ **설정 정보 관리**: 애플리케이션의 전역 설정을 하나의 인스턴스로 관리  
4️⃣ **캐싱 시스템**: 여러 객체가 동일한 캐시를 공유할 때

---

## 🚀 JavaScript에서 싱글톤 패턴 구현하기

### ✅ 기본적인 싱글톤 패턴 구현

```js
class Singleton {
    constructor() {
        if (!Singleton.instance) {
            Singleton.instance = this; // 첫 번째 인스턴스를 저장
        }
        return Singleton.instance; // 이후 요청은 동일한 인스턴스를 반환
    }

    sayHello() {
        console.log("Hello, Singleton Pattern!");
    }
}

// 인스턴스 생성
const instance1 = new Singleton();
const instance2 = new Singleton();

// 👉🏻 동일한 객체를 참조하는지 확인
console.log(instance1 === instance2); // true (같은 인스턴스 반환)

instance1.sayHello(); // "Hello, Singleton Pattern!"
```

🔹 `new Singleton()`을 여러 번 호출해도 **항상 동일한 객체**가 반환된다.

---

## ✅ 모듈 패턴을 이용한 싱글톤 (Node.js)

Node.js에서는 **모듈 캐싱**을 이용해 간단하게 싱글톤 패턴을 구현할 수 있다.

📌 `singleton.js` 파일

```js
class Singleton {
    constructor() {
        if (!Singleton.instance) {
            Singleton.instance = this;
            this.data = "싱글톤 인스턴스 데이터";
        }
        return Singleton.instance;
    }

    getData() {
        return this.data;
    }
}

module.exports = new Singleton(); // 모듈을 내보낼 때 같은 인스턴스 유지
```

📌 `app.js` 파일

```js
const singletonA = require("./singleton");
const singletonB = require("./singleton");

console.log(singletonA === singletonB); // true (같은 인스턴스 반환)

console.log(singletonA.getData()); // "싱글톤 인스턴스 데이터"
```

🔹 `require()`는 모듈을 **캐싱**하기 때문에, 같은 인스턴스를 반환한다.

---

## ✅ 클로저를 이용한 싱글톤 패턴

JavaScript에서는 **클로저(Closure)**를 이용해 싱글톤을 만들 수도 있다.

```js
const Singleton = (function () {
    let instance; // 유일한 인스턴스를 저장할 변수

    function createInstance() {
        return { message: "I am a Singleton!" }; // 단일 객체 생성
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        },
    };
})();

const singleton1 = Singleton.getInstance();
const singleton2 = Singleton.getInstance();

console.log(singleton1 === singleton2); // true (같은 인스턴스 반환)
console.log(singleton1.message); // "I am a Singleton!"
```

🔹 `Singleton.getInstance()`를 호출할 때마다 **동일한 객체**가 반환된다.

---

## 🚀 싱글톤 패턴의 장점과 단점

### ✅ 장점
✅ **메모리 절약**: 불필요한 객체 생성을 방지  
✅ **전역 상태 유지**: 하나의 인스턴스를 공유하여 데이터 일관성 유지  
✅ **모듈화**: 한 번 생성된 객체를 여러 곳에서 사용 가능

### ❌ 단점
❌ **전역 상태 오염**: 너무 많은 싱글톤 사용은 코드의 복잡성을 증가시킬 수 있음  
❌ **테스트 어려움**: 특정 상태를 유지하므로, 테스트 환경에서 초기화가 필요할 수 있음  
❌ **멀티스레드 환경에서 문제 발생 가능**: Node.js는 단일 스레드지만, 멀티스레드 환경에서는 동기화 문제가 발생할 수 있음

---

## 🎉 결론
싱글톤 패턴은 **전역적으로 하나의 인스턴스를 유지해야 할 때 유용**하다.  
하지만 **너무 남용하면 코드의 유연성이 떨어질 수 있으므로, 필요한 경우에만 사용**하자! 🚀

