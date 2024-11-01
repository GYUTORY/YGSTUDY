
### 자바스크립트(ES6)에서 함수를 정의하는 방법은 크게 두가지로 나뉜다.
- 일반함수와 화살표 함수 이다.

```javascript
function main() { // 일반 함수
	return 'function';
};

const main = () => 'function'; // 화살표 함수
```

---

## this!
- 일반함수와 화살표함수의 가장 큰 차이는 this이다.

### 일반 Function의 this

```javascript
const obj = {
    a: 10,
    method: function() {
        const arrowFunc = () => {
            console.log(this.a);
        };
        arrowFunc();
    }
};

obj.method(); // 10
```

- 위 코드에서 method는 일반 함수이므로, this는 obj를 가리킵니다. 따라서 어로우 함수인 arrowFunc가 this.a를 참조할 때 obj.a에 접근할 수 있습니다.



### Arrow Function의 this
-  자신만의 this를 가지지 않기 때문에, 상위 스코프에 this가 바인딩된 객체가 없는 경우에는 자신의 객체의 속성에 접근할 수 없습니다.

```javascript
const obj = {
    a: 10,
    method: function() {
        const arrowFunc = () => {
            console.log(this.a);
        };
        const anotherObj = {
            a: 20,
            arrowFunc: arrowFunc
        };
        anotherObj.arrowFunc(); // undefined
    }
};

obj.method();
```

- 여기서 anotherObj.arrowFunc()를 호출하면, arrowFunc는 여전히 method가 호출된 컨텍스트의 this를 참조하기 때문에 this.a는 undefined가 됩니다.
- 결론적으로, Arrow Function는 상위 스코프의 this를 사용하기 때문에, 자신의 객체에 정의된 속성에 접근하려면 해당 객체의 메서드에서 일반 함수를 사용하는 것이 좋습니다.