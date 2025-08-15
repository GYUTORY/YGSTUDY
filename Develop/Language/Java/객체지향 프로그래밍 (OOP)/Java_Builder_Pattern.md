---
title: Java Builder
tags: [language, java, 객체지향-프로그래밍-oop, javabuilderpattern]
updated: 2025-08-10
---

# Java Builder 패턴

## 배경
Builder 패턴은 객체 생성에 관련된 디자인 패턴 중 하나로, 복잡한 객체를 단계별로 구성하고 그 결과로 객체를 생성할 수 있도록 돕습니다.  
특히, **매개변수가 많은 생성자**를 대체하거나 **불변 객체**를 생성할 때 유용합니다.

---

1. **가독성 향상**  
   빌더 메서드 체이닝을 사용해 객체 생성 코드를 읽기 쉽게 만듭니다.

2. **유연성**  
   필수 값과 선택적 값을 구분할 수 있어 객체 생성의 유연성이 증가합니다.

3. **불변성 보장**  
   생성된 객체를 불변(Immutable) 상태로 유지하기 쉽습니다.

4. **유지보수 용이**  
   생성자에 많은 매개변수가 필요할 경우, 빌더 패턴으로 대체하면 코드 유지보수가 쉬워집니다.

---


### 1. Builder 클래스 정의
Builder 클래스는 생성 대상 객체의 모든 필드와 동일한 필드를 갖고 있으며, 각 필드를 설정하기 위한 메서드가 포함됩니다.

### 2. 메서드 체이닝 구현
Builder 클래스의 각 설정 메서드는 Builder 객체를 반환해 체이닝(Chaining)이 가능하게 합니다.

### 3. 객체 생성
Builder 클래스 내부에 `build()` 메서드를 추가하여 최종적으로 객체를 생성하도록 합니다.

---


```java
// Product 클래스
public class Product {
    private final String name;
    private final int price;
    private final String description;

    // Builder 클래스
    public static class Builder {
        private String name;
        private int price;
        private String description;

        // name 설정
        public Builder setName(String name) {
            this.name = name;
            return this;
        }

        // price 설정
        public Builder setPrice(int price) {
            this.price = price;
            return this;
        }

        // description 설정
        public Builder setDescription(String description) {
            this.description = description;
            return this;
        }

        // 최종 객체 생성
        public Product build() {
            return new Product(this);
        }
    }

    // Product의 private 생성자
    private Product(Builder builder) {
        this.name = builder.name;
        this.price = builder.price;
        this.description = builder.description;
    }

    @Override
    public String toString() {
        return "Product{name='" + name + "', price=" + price + ", description='" + description + "'}";
    }
}
```

---


```java
public class Main {
    public static void main(String[] args) {
        Product product = new Product.Builder()
            .setName("Laptop")
            .setPrice(1500)
            .setDescription("High-end gaming laptop")
            .build();

        System.out.println(product);
    }
}
```

출력 결과:
```
Product{name='Laptop', price=1500, description='High-end gaming laptop'}
```

---


- **필수 필드 관리**  
  필수 필드가 있다면 Builder 생성자에서 설정하도록 강제할 수 있습니다.

  ```java
  public Builder(String name, int price) {
      this.name = name;
      this.price = price;
  }
  ```

- **불변 객체 생성**  
  생성된 `Product` 객체의 필드에 `final` 키워드를 사용하고, 외부에서 수정할 수 없도록 제한합니다.

---


| 장점                | 설명                                                    |
|---------------------|-------------------------------------------------------|
| 가독성             | 메서드 체이닝을 통해 직관적인 객체 생성 가능              |
| 유연성             | 필수 값과 선택 값의 구분 및 필요에 따른 설정 가능          |
| 유지보수 용이성    | 생성자보다 관리하기 쉬운 구조 제공                        |

---

Builder 패턴은 객체 생성이 복잡하거나, 필드가 많은 경우에 가장 적합한 디자인 패턴 중 하나입니다.  
이를 통해 유지보수성과 가독성을 동시에 향상시킬 수 있습니다.










