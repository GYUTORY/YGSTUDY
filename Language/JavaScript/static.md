
# static
static 키워드는 클래스의 정적 메서드를 정의합니다.

```javascript
class ClassWithStaticMethod {
  static staticProperty = 'someValue';
  static staticMethod() {
    return 'static method has been called.';
  }
  static {
    console.log('Class static initialization block called');
  }
}

console.log(ClassWithStaticMethod.staticProperty);
// Expected output: "someValue"
console.log(ClassWithStaticMethod.staticMethod());
// Expected output: "static method has been called."

```

결과 
> "Class static initialization block called" <br>
> "someValue" <br>
> "static method has been called."


## 설명
- 정적 메서드는 클래스의 인스턴스 없이 호출이 가능하며 클래스가 인스턴스화되면 호출할 수 없다. 
- 정적 메서드는 종종 어플리케이션의 유틸리티 함수를 만드는데 사용된다.

### 정적 메서드의 호출
- 동일한 클래스 내의 다른 정적 메서드 내에서 정적 메서드를 호출하는 경우 키워드 this를 사용할 수 있다.

```javascript
class StaticMethodCall {
  static staticMethod() {
    return "Static method has been called";
  }
  static anotherStaticMethod() {
    return this.staticMethod() + " from another static method";
  }
}
StaticMethodCall.staticMethod();
// 'Static method has been called'

StaticMethodCall.anotherStaticMethod();
// 'Static method has been called from another static method'
```


### 예시
```javascript
class Triple {
  static triple(n) {
    n = n || 1; //비트연산이 아니어야 합니다.
    return n * 3;
  }
}

class BiggerTriple extends Triple {
  static triple(n) {
    return super.triple(n) * super.triple(n);
  }
}

console.log(Triple.triple()); // 3
console.log(Triple.triple(6)); // 18
console.log(BiggerTriple.triple(3)); // 81
var tp = new Triple();
console.log(BiggerTriple.triple(3)); // 81 (부모의 인스턴스에 영향을 받지 않습니다.)
console.log(tp.triple()); // 'tp.triple은 함수가 아닙니다.'.
console.log(tp.constructor.triple(4)); // 12
```

