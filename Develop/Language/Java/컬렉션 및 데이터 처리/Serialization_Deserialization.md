---
title: Java Serialization Deserialization
tags: [language, java, 컬렉션-및-데이터-처리, serializationdeserialization]
updated: 2025-08-10
---
# Java 직렬화(Serialization) 및 역직렬화(Deserialization)

## 배경

### 직렬화(Serialization)
Java 객체를 바이트(byte) 형태로 변환하여 파일에 저장하거나 네트워크로 전송할 수 있도록 하는 과정입니다.

### 역직렬화(Deserialization)
바이트 형태로 저장된 데이터를 다시 Java 객체로 복원하는 과정입니다.

1. 객체 상태를 영구적으로 저장 (예: 파일, 데이터베이스)
2. 네트워크를 통한 객체 전송

객체를 직렬화하려면 해당 클래스가 `java.io.Serializable` 인터페이스를 구현해야 합니다.


### 직렬화 예제
```java
import java.io.*;

class Person implements Serializable {
    private static final long serialVersionUID = 1L; // 버전 관리 ID

    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    @Override
    public String toString() {
        return "Person{name='" + name + '\'' + ", age=" + age + '}';
    }
}

public class SerializationExample {
    public static void main(String[] args) {
        Person person = new Person("홍길동", 30);

        try (ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("person.ser"))) {
            oos.writeObject(person);
            System.out.println("직렬화 완료: " + person);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

### 역직렬화 예제
```java
import java.io.*;

public class DeserializationExample {
    public static void main(String[] args) {
        try (ObjectInputStream ois = new ObjectInputStream(new FileInputStream("person.ser"))) {
            Person person = (Person) ois.readObject();
            System.out.println("역직렬화 완료: " + person);
        } catch (IOException | ClassNotFoundException e) {
            e.printStackTrace();
        }
    }
}
```

```java
import java.io.*;

class Person implements Serializable {
    private static final long serialVersionUID = 1L; // 버전 관리 ID

    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    @Override
    public String toString() {
        return "Person{name='" + name + '\'' + ", age=" + age + '}';
    }
}

public class SerializationExample {
    public static void main(String[] args) {
        Person person = new Person("홍길동", 30);

        try (ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("person.ser"))) {
            oos.writeObject(person);
            System.out.println("직렬화 완료: " + person);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

```java
import java.io.*;

public class DeserializationExample {
    public static void main(String[] args) {
        try (ObjectInputStream ois = new ObjectInputStream(new FileInputStream("person.ser"))) {
            Person person = (Person) ois.readObject();
            System.out.println("역직렬화 완료: " + person);
        } catch (IOException | ClassNotFoundException e) {
            e.printStackTrace();
        }
    }
}
```

1. **`serialVersionUID` 사용**: 클래스 버전 관리를 위해 명시적으로 선언하는 것이 좋습니다.
2. **Transient 키워드**: 직렬화에서 제외할 필드에 `transient` 키워드를 사용합니다.
   ```java
   private transient String password;
   ```
3. **직렬화 가능한 객체만 포함**: 포함된 객체도 `Serializable`을 구현해야 합니다.

```
직렬화 완료: Person{name='홍길동', age=30}
역직렬화 완료: Person{name='홍길동', age=30}
```

Java의 직렬화와 역직렬화는 객체 데이터를 영구적으로 저장하거나 네트워크로 전송할 때 유용합니다. 이를 적절히 활용하면 애플리케이션의 데이터 관리와 통신 효율성을 높일 수 있습니다.






Java에서 **직렬화**와 **역직렬화**는 객체를 저장하거나 네트워크를 통해 전달하기 위한 필수적인 기법입니다.

```java
import java.io.*;

class Person implements Serializable {
    private static final long serialVersionUID = 1L; // 버전 관리 ID

    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    @Override
    public String toString() {
        return "Person{name='" + name + '\'' + ", age=" + age + '}';
    }
}

public class SerializationExample {
    public static void main(String[] args) {
        Person person = new Person("홍길동", 30);

        try (ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("person.ser"))) {
            oos.writeObject(person);
            System.out.println("직렬화 완료: " + person);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

```java
import java.io.*;

public class DeserializationExample {
    public static void main(String[] args) {
        try (ObjectInputStream ois = new ObjectInputStream(new FileInputStream("person.ser"))) {
            Person person = (Person) ois.readObject();
            System.out.println("역직렬화 완료: " + person);
        } catch (IOException | ClassNotFoundException e) {
            e.printStackTrace();
        }
    }
}
```

```java
import java.io.*;

class Person implements Serializable {
    private static final long serialVersionUID = 1L; // 버전 관리 ID

    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    @Override
    public String toString() {
        return "Person{name='" + name + '\'' + ", age=" + age + '}';
    }
}

public class SerializationExample {
    public static void main(String[] args) {
        Person person = new Person("홍길동", 30);

        try (ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream("person.ser"))) {
            oos.writeObject(person);
            System.out.println("직렬화 완료: " + person);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

```java
import java.io.*;

public class DeserializationExample {
    public static void main(String[] args) {
        try (ObjectInputStream ois = new ObjectInputStream(new FileInputStream("person.ser"))) {
            Person person = (Person) ois.readObject();
            System.out.println("역직렬화 완료: " + person);
        } catch (IOException | ClassNotFoundException e) {
            e.printStackTrace();
        }
    }
}
```

1. **`serialVersionUID` 사용**: 클래스 버전 관리를 위해 명시적으로 선언하는 것이 좋습니다.
2. **Transient 키워드**: 직렬화에서 제외할 필드에 `transient` 키워드를 사용합니다.
   ```java
   private transient String password;
   ```
3. **직렬화 가능한 객체만 포함**: 포함된 객체도 `Serializable`을 구현해야 합니다.

```
직렬화 완료: Person{name='홍길동', age=30}
역직렬화 완료: Person{name='홍길동', age=30}
```

Java의 직렬화와 역직렬화는 객체 데이터를 영구적으로 저장하거나 네트워크로 전송할 때 유용합니다. 이를 적절히 활용하면 애플리케이션의 데이터 관리와 통신 효율성을 높일 수 있습니다.






Java에서 **직렬화**와 **역직렬화**는 객체를 저장하거나 네트워크를 통해 전달하기 위한 필수적인 기법입니다.





