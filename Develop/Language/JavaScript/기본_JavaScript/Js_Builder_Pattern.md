
# Node.js Builder 패턴

## 개요
Builder 패턴은 객체 생성 로직이 복잡한 경우 이를 단계적으로 설정하고 최종적으로 객체를 생성할 수 있게 해주는 디자인 패턴입니다.  
Node.js 환경에서도 Builder 패턴을 활용해 **복잡한 객체 생성**을 단순화할 수 있습니다.

---

## 장점
1. **유연성**  
   객체 생성 과정에서 필요한 값만 설정할 수 있어 불필요한 코드 작성이 줄어듭니다.

2. **가독성 향상**  
   메서드 체이닝 방식을 활용하여 더 직관적으로 객체를 구성할 수 있습니다.

3. **재사용성**  
   여러 객체 생성 로직을 하나의 Builder 클래스로 재사용할 수 있습니다.

---

## 구현 방법

### 1. Builder 클래스 정의
Builder 클래스는 생성할 객체의 프로퍼티를 초기화하고 설정 메서드를 제공합니다.

### 2. 메서드 체이닝 구현
각 설정 메서드는 Builder 인스턴스를 반환하여 메서드 체이닝이 가능하게 합니다.

### 3. 최종 객체 반환
Builder 클래스에 `build()` 메서드를 추가하여 최종 객체를 반환합니다.

---

## 코드 예제

### 사용자 정의 객체 생성
```javascript
// Product 클래스 정의
class Product {
  constructor(builder) {
    this.name = builder.name;
    this.price = builder.price;
    this.description = builder.description;
  }
}

// Builder 클래스 정의
class ProductBuilder {
  constructor() {
    this.name = "";
    this.price = 0;
    this.description = "";
  }

  // 이름 설정
  setName(name) {
    this.name = name;
    return this;
  }

  // 가격 설정
  setPrice(price) {
    this.price = price;
    return this;
  }

  // 설명 설정
  setDescription(description) {
    this.description = description;
    return this;
  }

  // 최종 객체 생성
  build() {
    return new Product(this);
  }
}

// 사용 예제
const product = new ProductBuilder()
  .setName("Laptop")
  .setPrice(1500)
  .setDescription("High-end gaming laptop")
  .build();

console.log(product);
```

출력 결과:
```
Product {
  name: 'Laptop',
  price: 1500,
  description: 'High-end gaming laptop'
}
```

---

## 장점 요약

| 장점                | 설명                                                    |
|---------------------|-------------------------------------------------------|
| 가독성             | 메서드 체이닝을 통해 객체 생성 과정을 직관적으로 표현 가능 |
| 유연성             | 객체 생성 시 필요한 값만 선택적으로 설정 가능            |
| 유지보수 용이성    | 객체 생성 로직을 분리하여 코드의 유지보수성 향상          |

---

## 응용 사례

1. **데이터 모델링**  
   복잡한 데이터 모델을 생성할 때 Builder 패턴을 사용하면 구조를 단순화할 수 있습니다.

2. **설정 객체 생성**  
   설정(config) 파일이나 HTTP 요청 객체와 같이 다수의 선택적 파라미터가 있는 경우 유용합니다.

3. **테스트 객체 생성**  
   테스트 데이터 생성을 위한 Mock 객체를 생성할 때 유용합니다.

---

## 결론
Node.js에서 Builder 패턴은 특히 객체의 생성 단계가 복잡하거나 필드가 많을 때 효과적입니다.  
이를 통해 객체 생성 로직을 단순화하고 유지보수성을 높일 수 있습니다.
