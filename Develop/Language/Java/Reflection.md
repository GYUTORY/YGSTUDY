
# Java 리플렉션(Reflection)

## 리플렉션이란?
리플렉션(Reflection)은 Java 프로그램이 실행 중에 클래스, 메서드, 필드 등의 정보를 동적으로 검사하거나 수정할 수 있는 기능입니다. 이를 통해 컴파일 시점에 알 수 없는 클래스의 구조를 런타임에 접근하여 사용할 수 있습니다.

리플렉션은 주로 다음과 같은 경우에 사용됩니다:
- 런타임에 객체의 클래스 정보를 가져올 때
- 동적으로 메서드를 호출하거나 필드에 접근할 때
- 애플리케이션에서 플러그인이나 확장 기능을 로드할 때

리플렉션은 강력한 기능을 제공하지만, 오버헤드가 있을 수 있으며, 잘못 사용하면 성능 저하나 보안 문제가 발생할 수 있습니다.

---

## 주요 클래스와 메서드
리플렉션은 주로 `java.lang.reflect` 패키지의 클래스를 사용합니다.
- `Class` : 클래스의 메타데이터를 나타냄
- `Method` : 클래스의 메서드를 나타냄
- `Field` : 클래스의 필드를 나타냄
- `Constructor` : 클래스의 생성자를 나타냄

주요 메서드:
- `Class.forName(String className)` : 클래스 정보를 가져옴
- `getMethods()`, `getDeclaredMethods()` : 클래스의 메서드 정보를 가져옴
- `getFields()`, `getDeclaredFields()` : 클래스의 필드 정보를 가져옴
- `getConstructors()`, `getDeclaredConstructors()` : 생성자 정보를 가져옴

---

## 리플렉션 예제
아래는 리플렉션을 사용하여 클래스 정보를 가져오고 메서드를 호출하는 간단한 예제입니다.

```java
import java.lang.reflect.*;

public class ReflectionExample {
    public static void main(String[] args) {
        try {
            // 클래스 로드
            Class<?> clazz = Class.forName("example.Person");
            
            // 클래스 이름 출력
            System.out.println("클래스 이름: " + clazz.getName());

            // 생성자 출력
            Constructor<?>[] constructors = clazz.getDeclaredConstructors();
            for (Constructor<?> constructor : constructors) {
                System.out.println("생성자: " + constructor);
            }

            // 필드 출력
            Field[] fields = clazz.getDeclaredFields();
            for (Field field : fields) {
                System.out.println("필드: " + field.getName() + " (" + field.getType() + ")");
            }

            // 메서드 출력
            Method[] methods = clazz.getDeclaredMethods();
            for (Method method : methods) {
                System.out.println("메서드: " + method.getName());
            }

            // 메서드 호출
            Object personInstance = clazz.getDeclaredConstructor(String.class, int.class).newInstance("홍길동", 25);
            Method getNameMethod = clazz.getDeclaredMethod("getName");
            String name = (String) getNameMethod.invoke(personInstance);
            System.out.println("호출된 메서드 결과: " + name);
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

// 예제 클래스
package example;

public class Person {
    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public int getAge() {
        return age;
    }

    public void setAge(int age) {
        this.age = age;
    }
}
```

---

## 주의사항
1. **성능 문제**: 리플렉션은 일반적인 메서드 호출보다 느립니다.
2. **보안 제약**: 리플렉션은 보안 매니저에 의해 제한될 수 있습니다.
3. **캡슐화 위반**: 비공개 필드나 메서드에 접근 가능하므로 잘못 사용하면 캡슐화 원칙을 위반할 수 있습니다.

---

## 결론
Java 리플렉션은 런타임에 클래스 구조를 동적으로 다룰 수 있는 강력한 기능을 제공합니다. 하지만 성능 및 보안 문제를 고려하여 필요한 경우에만 신중하게 사용하는 것이 중요합니다.
