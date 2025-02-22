

# 🚀 Factory Method(팩토리 메서드) 패턴 개념과 예제

## ✨ 팩토리 메서드 패턴이란?
팩토리 메서드 패턴(Factory Method Pattern)은 **객체 생성을 캡슐화**하는 디자인 패턴이다.  
즉, **객체 생성을 직접 하지 않고, 하위 클래스에서 객체를 생성하도록 위임**하는 방식이다.

---

## 🎯 팩토리 메서드 패턴의 핵심 개념

✅ **객체 생성을 서브클래스(하위 클래스)에 위임**  
✅ **클라이언트 코드가 객체 생성 방식에 의존하지 않도록 분리**  
✅ **확장성이 뛰어나며, 코드 변경 없이 새로운 객체 타입 추가 가능**

---

## 🌐 팩토리 메서드 패턴이 필요한 이유

다음과 같은 경우 팩토리 메서드 패턴을 적용하면 유용하다.

1️⃣ **객체 생성 로직이 복잡할 때**: 다양한 설정이 필요한 객체를 효율적으로 관리  
2️⃣ **유지보수성을 높이고 싶을 때**: 객체 생성 방식을 캡슐화하여 클라이언트 코드 변경 없이 확장 가능  
3️⃣ **새로운 객체 유형이 자주 추가될 때**: 기존 코드 변경 없이 새로운 타입 추가 가능

---

## 🚀 JavaScript에서 팩토리 메서드 패턴 구현하기

### ✅ 예제: 팩토리 메서드 패턴을 사용한 자동차 객체 생성

```js
// 🚗 부모 클래스 (추상 클래스 역할)
class Car {
    constructor() {
        if (new.target === Car) {
            throw new Error("Car 클래스는 직접 인스턴스를 생성할 수 없습니다.");
        }
    }

    drive() {
        throw new Error("drive() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// 🚙 구체적인 자동차 클래스 (하위 클래스)
class Sedan extends Car {
    drive() {
        return "🚗 세단을 운전 중...";
    }
}

class SUV extends Car {
    drive() {
        return "🚙 SUV를 운전 중...";
    }
}

// 🏭 팩토리 클래스 (객체 생성 담당)
class CarFactory {
    static createCar(type) {
        switch (type) {
            case "sedan":
                return new Sedan();
            case "suv":
                return new SUV();
            default:
                throw new Error("알 수 없는 자동차 타입입니다.");
        }
    }
}

// 📌 팩토리 메서드를 이용한 객체 생성
const mySedan = CarFactory.createCar("sedan");
const mySUV = CarFactory.createCar("suv");

console.log(mySedan.drive()); // 🚗 세단을 운전 중...
console.log(mySUV.drive());   // 🚙 SUV를 운전 중...
```

🔹 `CarFactory.createCar(type)`을 사용하면 **자동차 종류에 따라 객체가 생성**되며, 클라이언트는 생성 방식에 신경 쓸 필요가 없다.

---

## ✅ 팩토리 메서드 패턴을 활용한 API 서비스 클래스

팩토리 메서드 패턴을 사용하여 **API 요청을 관리하는 서비스 클래스**를 만들 수도 있다.

```js
// 📌 API 요청을 담당하는 부모 클래스
class APIService {
    constructor() {
        if (new.target === APIService) {
            throw new Error("APIService 클래스는 직접 인스턴스를 생성할 수 없습니다.");
        }
    }

    fetchData() {
        throw new Error("fetchData() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// 📌 구체적인 API 서비스 클래스
class UserService extends APIService {
    fetchData() {
        return "👤 사용자 데이터 가져오기";
    }
}

class ProductService extends APIService {
    fetchData() {
        return "📦 상품 데이터 가져오기";
    }
}

// 📌 팩토리 클래스
class APIServiceFactory {
    static createService(type) {
        switch (type) {
            case "user":
                return new UserService();
            case "product":
                return new ProductService();
            default:
                throw new Error("알 수 없는 서비스 타입입니다.");
        }
    }
}

// 📌 클라이언트 코드
const userService = APIServiceFactory.createService("user");
const productService = APIServiceFactory.createService("product");

console.log(userService.fetchData()); // 👤 사용자 데이터 가져오기
console.log(productService.fetchData()); // 📦 상품 데이터 가져오기
```

🔹 API 서비스의 종류가 늘어나도 기존 코드를 수정할 필요 없이 **팩토리 메서드를 확장**하면 된다.

---

## ✅ 팩토리 메서드 패턴의 장점과 단점

### ✅ 장점
✅ **객체 생성 로직을 캡슐화**: 클라이언트 코드에서 객체 생성 방식을 알 필요 없음  
✅ **유지보수성 향상**: 객체 생성 코드 변경 없이 새로운 클래스 추가 가능  
✅ **의존성 감소**: 클라이언트 코드가 특정 클래스에 강하게 결합되지 않음

### ❌ 단점
❌ **클래스 수 증가**: 팩토리 클래스와 서브클래스가 많아질 수 있음  
❌ **단순한 객체 생성에는 불필요한 복잡성 초래**: 객체 생성이 단순하다면 팩토리 패턴이 오히려 과한 설계가 될 수 있음
