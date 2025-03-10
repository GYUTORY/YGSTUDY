# 오버라이드(Override)와 오버라이딩(Overriding)의 차이 🚀

## 1. 오버라이드(Override) vs. 오버라이딩(Overriding) 🤔

Java에서 `Override`와 `Overriding`은 자주 혼용되지만, 정확한 의미가 다릅니다.  
둘 다 **상속(Inheritance)과 관련된 개념**이지만, **용어의 사용 방식**이 다릅니다.

> **✨ 핵심 차이점**
> - **Override (오버라이드)** → "재정의"의 개념 (동작 자체를 의미)
> - **Overriding (오버라이딩)** → "재정의하는 행위" (Override를 수행하는 과정)

### 📌 쉽게 이해하기
- "Override"는 **오버라이딩된 메서드 자체**
- "Overriding"은 **Override를 적용하는 과정**

---

## 2. 오버라이딩(Overriding) 이란? 🔄

✔ 부모 클래스의 **메서드를 자식 클래스에서 재정의**하는 것  
✔ **메서드의 이름, 매개변수, 반환 타입이 동일해야 함**  
✔ **`@Override` 어노테이션을 사용하여 의도를 명확히 할 수 있음**

#### ✅ 예제 (오버라이딩)
```java
class Animal {
    public void makeSound() {
        System.out.println("동물이 소리를 냅니다.");
    }
}

class Dog extends Animal {
    @Override
    public void makeSound() { // 오버라이딩
        System.out.println("멍멍!");
    }
}

public class OverridingExample {
    public static void main(String[] args) {
        Animal myDog = new Dog();
        myDog.makeSound(); // 멍멍!
    }
}
```
> **📌 `makeSound()` 메서드는 부모 클래스에서 정의되었지만, `Dog` 클래스에서 오버라이딩하여 다르게 동작!**

---

## 3. `@Override` 어노테이션의 역할 ✨

✔ **오버라이딩이 제대로 이루어졌는지 컴파일러가 확인**  
✔ **실수로 메서드 이름을 잘못 입력하는 경우 방지**

#### ✅ 예제 (`@Override` 없는 경우)
```java
class Parent {
    public void showMessage() {
        System.out.println("부모 클래스의 메시지");
    }
}

class Child extends Parent {
    // 실수로 메서드 이름을 잘못 작성 (showMessage → showMessages)
    public void showMessages() {
        System.out.println("자식 클래스의 메시지");
    }
}

public class OverrideExample {
    public static void main(String[] args) {
        Child child = new Child();
        child.showMessage(); // 부모 클래스의 메시지 (오버라이딩 실패)
    }
}
```
> **🛑 `showMessages()`는 `showMessage()`를 오버라이딩한 것이 아님 → 오버라이딩 실패!**

#### ✅ 올바른 예제 (`@Override` 사용)
```java
class Parent {
    public void showMessage() {
        System.out.println("부모 클래스의 메시지");
    }
}

class Child extends Parent {
    @Override
    public void showMessage() { // 정확한 오버라이딩
        System.out.println("자식 클래스의 메시지");
    }
}

public class OverrideExample {
    public static void main(String[] args) {
        Child child = new Child();
        child.showMessage(); // 자식 클래스의 메시지 (오버라이딩 성공)
    }
}
```
> **📌 `@Override`를 사용하면 실수를 방지하고, 정확하게 오버라이딩되었는지 확인 가능!**

---

## 4. 오버라이드(Override)란? 🎭

✔ **오버라이딩된 메서드 자체를 의미**  
✔ 즉, **재정의된 메서드의 결과물**을 지칭하는 용어

#### ✅ 예제
```java
class Parent {
    public void display() {
        System.out.println("부모 클래스의 메서드");
    }
}

class Child extends Parent {
    @Override
    public void display() { // 여기서 'Override' 발생
        System.out.println("자식 클래스에서 오버라이드된 메서드");
    }
}

public class OverrideExample {
    public static void main(String[] args) {
        Parent obj = new Child();
        obj.display(); // 자식 클래스에서 오버라이드된 메서드
    }
}
```
> **👉🏻 `display()` 메서드는 오버라이딩되었고, 이 메서드 자체를 'Override'라고 부름!**

---

## 5. 오버로딩(Overloading)과의 차이 🚨

**오버라이딩(Overriding)과 오버로딩(Overloading)은 완전히 다른 개념!**

| 구분 | 오버라이딩 (Overriding) | 오버로딩 (Overloading) |
|------|------------------------|------------------------|
| 목적 | **메서드 재정의** | **메서드 이름을 같게 하면서 다른 매개변수 사용** |
| 적용 대상 | **상속 관계에서 부모 메서드 재정의** | **동일 클래스 내에서 같은 이름의 메서드 여러 개 정의** |
| 메서드 이름 | **같아야 함** | **같아야 함** |
| 매개변수 | **동일해야 함** | **다르게 설정 가능** |
| 반환 타입 | **동일해야 함** | **다를 수도 있음** |
| 어노테이션 | `@Override` 사용 가능 | 사용하지 않음 |

#### ✅ 오버로딩 예제
```java
class MathUtil {
    public int add(int a, int b) { // 첫 번째 add 메서드
        return a + b;
    }

    public double add(double a, double b) { // 두 번째 add 메서드 (오버로딩)
        return a + b;
    }
}

public class OverloadingExample {
    public static void main(String[] args) {
        MathUtil util = new MathUtil();
        System.out.println(util.add(5, 10));      // int 버전 호출
        System.out.println(util.add(3.5, 2.2));  // double 버전 호출
    }
}
```
> **📌 오버로딩은 같은 메서드 이름을 유지하면서, 매개변수를 다르게 설정하는 기법!**

---

## 📌 결론

- **Override (오버라이드)** → "재정의된 메서드" 자체를 의미
- **Overriding (오버라이딩)** → 부모 메서드를 자식 클래스에서 "재정의하는 행위"
- **`@Override` 어노테이션을 사용하여 실수를 방지할 것**
- **오버라이딩과 오버로딩은 완전히 다른 개념**

> **👉🏻 오버라이딩을 활용하면 상속받은 메서드를 재정의하여 다형성을 구현할 수 있음!**

