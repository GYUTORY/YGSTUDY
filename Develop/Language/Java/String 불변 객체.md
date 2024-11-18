

## 1. 불변성의 개념
- Java의 String 객체는 한 번 생성되면 그 내용을 변경할 수 없습니다. 예를 들어, 다음과 같은 코드가 있다고 가정해 보겠습니다.

```java
String str = "Hello";
str = str + " World";
```
- 위 코드에서 str은 처음에 "Hello"라는 문자열을 가리킵니다.
- str + " World"를 수행하면, 새로운 문자열 "Hello World"가 생성되고, str은 이제 이 새로운 문자열을 가리키게 됩니다. 
- 원래의 "Hello" 문자열은 변경되지 않고 여전히 메모리에 존재합니다.

### 2. 메모리 관리
- Java는 문자열 리터럴을 상수 풀에 저장합니다. 같은 문자열 리터럴이 여러 번 사용되면, 메모리 사용을 줄이기 위해 같은 객체를 재사용합니다. 예를 들어:

```java
String a = "Hello";
String b = "Hello";
```
- 여기서 a와 b는 같은 문자열 리터럴 "Hello"를 가리키며, 메모리에서 같은 객체를 참조합니다. 
- 만약 String이 가변적이었다면, 두 개의 서로 다른 객체가 생성될 수 있었고, 이는 메모리 낭비를 초래할 수 있습니다.

### 3. 스레드 안전성
- 불변 객체는 여러 스레드에서 동시에 접근하더라도 안전합니다. 예를 들어, 다음과 같은 멀티스레드 환경을 생각해 보겠습니다.

```java
String sharedString = "Initial";

Runnable task1 = () -> {
System.out.println(sharedString);
};

Runnable task2 = () -> {
sharedString += " Modified"; // 새로운 문자열 생성
};

new Thread(task1).start();
new Thread(task2).start();
```
- 위 코드에서 task1은 sharedString을 출력하고, task2는 sharedString을 수정하려고 합니다.
- 하지만 sharedString은 불변이기 때문에, task1이 출력하는 동안 task2가 sharedString을 변경해도 task1은 항상 "Initial"을 출력합니다.
- 이는 스레드 안전성을 보장합니다.

### 4. 성능 고려
- 문자열을 자주 변경해야 하는 경우, StringBuilder와 같은 가변 문자열 클래스를 사용하는 것이 더 효율적입니다. 예를 들어:

```java
StringBuilder sb = new StringBuilder("Hello");
sb.append(" World");
String result = sb.toString(); // "Hello World"
StringBuilder는 내부적으로 가변 배열을 사용하여 문자열을 수정할 수 있습니다. 이 경우, 문자열을 변경할 때마다 새로운 객체를 생성하지 않으므로 성능이 향상됩니다.
```

--- 

# 요약
### 불변성
- String 객체는 한 번 생성되면 변경할 수 없으며, 새로운 문자열을 생성할 때마다 새로운 객체가 만들어집니다.
### 메모리 관리
- 같은 문자열 리터럴은 상수 풀에서 재사용되어 메모리를 절약합니다.
## 스레드 안전성
- 불변 객체는 여러 스레드에서 안전하게 사용할 수 있습니다.
## 성능
- 자주 변경해야 하는 경우 StringBuilder와 같은 가변 클래스를 사용하여 성능을 최적화할 수 있습니다.