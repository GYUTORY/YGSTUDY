# Factory Method

- 객체 생성을 서브 클래스로 위임하는 패턴입니다.
- 슈퍼 클래스에서는 객체의 인스턴스화를 처리하는 추상 메서드를 정의하고, 서브 클래스에서는 이를 구체적으로 구현합니다.
- 이를 통해 객체 생성의 유연성을 확보하고, 클라이언트 코드와 객체 생성을 분리할 수 있습니다.

```typescript
// 슈퍼 클래스
abstract class Product {
    public abstract use(): void;
}

// 서브 클래스 1
class ConcreteProduct1 extends Product {
    public use(): void {
        console.log("ConcreteProduct1 사용");
    }
}

// 서브 클래스 2
class ConcreteProduct2 extends Product {
    public use(): void {
        console.log("ConcreteProduct2 사용");
    }
}

// 팩토리 메서드를 가지는 팩토리 클래스
class Creator {
    public createProduct(type: string): Product {

        let product: Product;

        if (type === "product1") {
            product = new ConcreteProduct1();
        } else if (type === "product2") {
            product = new ConcreteProduct2();
        } else {
            throw new Error("지정된 유형의 제품을 생성할 수 없습니다.");
        }

        return product;
    }
}

// 팩토리 클래스를 사용하는 클라이언트 코드
const creator = new Creator();

const product1 = creator.createProduct("product1");
product1.use(); // "ConcreteProduct1 사용"

const product2 = creator.createProduct("product2");
product2.use(); // "ConcreteProduct2 사용"
```

## Factory Method의 종류

### 1. Product 클래스
- 추상 클래스로, use()라는 추상 메서드를 가지고 있습니다. 이 메서드는 서브 클래스에서 구체적으로 구현되어야 합니다.

### 2. ConcreteProduct1 및 ConcreteProduct2 클래스
- Product 클래스를 상속받는 구체적인 서브 클래스들입니다. 각각의 클래스는 use() 메서드를 구현하여 각자의 특정한 동작을 정의합니다.

### 3. Creator 클래스
- 팩토리 메서드를 가지는 팩토리 클래스입니다. createProduct() 메서드는 클라이언트로부터 전달받은 유형에 따라 적절한 서브 클래스의 인스턴스를 생성하여 반환합니다.
