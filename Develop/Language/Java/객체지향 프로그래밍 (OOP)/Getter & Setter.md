# Getter와 Setter 개념 및 활용 🚀

## 1. Getter와 Setter란? 🤔

**Getter**와 **Setter**는 **객체의 캡슐화(encapsulation)를 유지하면서, 필드(멤버 변수)에 접근하는 메서드**입니다.  
즉, **클래스 내부의 데이터(변수)를 보호하면서, 필요한 경우 값을 가져오거나 변경**할 수 있도록 합니다.

> **✨ Getter와 Setter의 역할**
> - **직접적인 변수 접근을 차단**하여, 무분별한 값 변경을 방지
> - **객체 지향 프로그래밍의 캡슐화 원칙 준수**
> - **데이터 검증(Validation) 로직을 추가할 수 있음**
> - **특정 데이터는 읽기 전용(Only Getter) 또는 쓰기 전용(Only Setter)으로 만들 수 있음**

---

## 2. Getter와 Setter 사용 예제

### 2.1 기본적인 Getter와 Setter

#### ✅ 예제
```java
class Person {
    private String name;  // private 변수 (직접 접근 불가)
    private int age;      // private 변수

    // Getter (데이터 조회)
    public String getName() {
        return name;
    }

    public int getAge() {
        return age;
    }

    // Setter (데이터 변경)
    public void setName(String name) {
        this.name = name;
    }

    public void setAge(int age) {
        if (age > 0) {  // 나이는 음수가 될 수 없도록 검증
            this.age = age;
        } else {
            System.out.println("나이는 0보다 커야 합니다!");
        }
    }
}

public class GetterSetterExample {
    public static void main(String[] args) {
        Person person = new Person();
        
        person.setName("홍길동");
        person.setAge(25);

        System.out.println("이름: " + person.getName());
        System.out.println("나이: " + person.getAge());
    }
}
```
> **📌 `private` 변수는 직접 접근할 수 없으며, `get`과 `set` 메서드를 통해 안전하게 데이터를 다룰 수 있음!**

---

### 2.2 Setter에서 데이터 검증 적용

✔ `setAge(int age)` 메서드에서 나이가 **0 이하인 경우 설정하지 않도록 예외 처리**  
✔ **Setter를 통해 데이터 유효성을 검증할 수 있음**

#### ✅ 예제
```java
class Product {
    private String name;
    private int price;

    public String getName() {
        return name;
    }

    public int getPrice() {
        return price;
    }

    public void setName(String name) {
        if (name == null || name.isEmpty()) {
            System.out.println("상품명은 비워둘 수 없습니다!");
        } else {
            this.name = name;
        }
    }

    public void setPrice(int price) {
        if (price < 0) {
            System.out.println("가격은 0 이상이어야 합니다!");
        } else {
            this.price = price;
        }
    }
}

public class ProductExample {
    public static void main(String[] args) {
        Product product = new Product();

        product.setName("노트북");
        product.setPrice(-5000); // 유효성 검사 실패

        System.out.println("상품명: " + product.getName());
        System.out.println("가격: " + product.getPrice());
    }
}
```
> **👉🏻 `setName()`과 `setPrice()`에서 데이터 검증을 통해 잘못된 값이 입력되지 않도록 방지!**

---

### 2.3 읽기 전용(Read-Only) 및 쓰기 전용(Write-Only) 속성 만들기

✔ **읽기 전용 (Read-Only) 속성** → `Getter`만 제공하고, `Setter`는 제공하지 않음  
✔ **쓰기 전용 (Write-Only) 속성** → `Setter`만 제공하고, `Getter`는 제공하지 않음

#### ✅ 예제 (읽기 전용 & 쓰기 전용 속성)
```java
class BankAccount {
    private String owner;
    private double balance;

    public BankAccount(String owner, double balance) {
        this.owner = owner;
        this.balance = balance;
    }

    // 읽기 전용 (Getter만 제공)
    public String getOwner() {
        return owner;
    }

    public double getBalance() {
        return balance;
    }

    // 쓰기 전용 (Getter 없음, Setter만 제공)
    public void deposit(double amount) {
        if (amount > 0) {
            balance += amount;
            System.out.println(amount + "원이 입금되었습니다. 현재 잔액: " + balance);
        } else {
            System.out.println("입금 금액은 0보다 커야 합니다.");
        }
    }
}

public class BankAccountExample {
    public static void main(String[] args) {
        BankAccount account = new BankAccount("김철수", 10000);

        System.out.println("계좌 소유자: " + account.getOwner()); // 읽기 가능
        System.out.println("현재 잔액: " + account.getBalance()); // 읽기 가능

        account.deposit(5000); // 입금 가능
    }
}
```
> **📌 `owner`와 `balance`는 `getter`만 제공하므로 읽기 전용, `deposit()`은 쓰기 전용 기능을 수행!**

---

## 3. Lombok을 활용한 Getter와 Setter 자동 생성 ✨

**Lombok** 라이브러리를 사용하면, **별도의 `get`/`set` 메서드를 작성하지 않고도 자동으로 생성**할 수 있습니다.

✔ `@Getter` → 클래스의 모든 `getter` 자동 생성  
✔ `@Setter` → 클래스의 모든 `setter` 자동 생성  
✔ `@Data` → `@Getter`, `@Setter`, `toString()` 등 자동 생성

#### ✅ Lombok 사용 예제
```java
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
class User {
    private String username;
    private String email;
}

public class LombokExample {
    public static void main(String[] args) {
        User user = new User();
        user.setUsername("admin");
        user.setEmail("admin@example.com");

        System.out.println("유저명: " + user.getUsername());
        System.out.println("이메일: " + user.getEmail());
    }
}
```
> **👉🏻 Lombok을 사용하면 `@Getter`와 `@Setter`만 선언하면 자동으로 메서드가 생성됨!**

---

## 4. Getter와 Setter를 사용할 때 주의할 점 ⚠️

✔ **무조건 Getter/Setter를 만들지 말고, 필요한 경우에만 제공해야 함**  
✔ **Setter에서 데이터 검증 로직을 포함하여 무결성 유지**  
✔ **읽기 전용(Only Getter) 또는 쓰기 전용(Only Setter) 설정을 적절히 활용**  
✔ **Lombok을 활용하면 불필요한 코드 작성을 줄일 수 있음**

---

## 📌 결론
- **Getter** → `private` 변수 값을 안전하게 조회할 때 사용
- **Setter** → `private` 변수 값을 안전하게 변경할 때 사용
- **데이터 무결성을 유지**하기 위해 Setter에서 검증 로직을 추가할 수 있음
- **읽기 전용(Read-Only) 및 쓰기 전용(Write-Only) 속성도 설정 가능**
- **Lombok을 활용하면 Getter/Setter 자동 생성 가능**

> **👉🏻 Getter/Setter를 적절히 사용하여 객체의 데이터 보호와 조작을 효과적으로 관리하자!**



