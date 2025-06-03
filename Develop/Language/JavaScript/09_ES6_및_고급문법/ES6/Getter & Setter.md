
## 프로그래밍 Getter & Setter 개념

- Getter와 Setter는 객체 지향 프로그래밍에서 사용되는 개념이며, 일종의 메서드라 칭해진다.
- 즉, 단어 그대로 Getter는 객체의 속성(property) 값을 반환하는 메서드이며,
- Setter는 객체의 속성 값을 설정, 변경하는 메서드라고 보면 된다. 예를들어 user 라는 객체가 있을 경우, 보통이라면 아래의 코드처럼 user.name 으로 프로퍼티로 바로 접근해서 이름값을 가져오거나 재설정할텐데,
  
```javascript
const user = {
	name: 'inpa',
    age: 50
}

console.log(user.name); // inpa

user.name = 'tistory';
```

- 위의 코드처럼 직접 접근하지 않고, getName()와 setName() 메서드를 통해 경유해서 설정하도록 하는 기법이 바로 Getter와 Setter 개념이다.

```javascript
const user = {
	name: 'inpa',
    age: 50,
    
    // 객체의 메서드(함수)
    getName() {
    	return user.name;
    },
    setName(value) {
    	user.name = value;
    }
}

console.log(user.getName()); // inpa

user.setName('tistory');
```

## Getter & Setter 활용하기
- 그런데 두 방식은 결과적으로 목표하고자 하는 바는 같고 결과값도 같게 보일 수도 있어, 번거롭게 Getter와 Setter를 사용할 이유는 무엇일까?
- Getter와 Setter를 사용하면 객체 내부 속성에 직접 접근하지 않아 객체의 정보 은닉을 가능하게 해주어 보안을 강화할 수 있고, 코드의 안전성과 유지보수성을 높일 수 있다는 장점이 있다.
- 또한 옳지않은 값을 넣으려고 할때 이를 미연에 방지할 수 있다. 예를들어 user.age 프로퍼티에 400이라는 나이값은 옳지않은 값이니 이를 할당하지 못하도록 해야되는데,
- Setter 메서드를 통해 경유하도록 설정하면 메서드 내에서 if문을 통해 값을 필터링 할 수 있게 된다.

```javascript
const user = {
	name: 'inpa',
    age: 50,
    
    getAge() {
    	return user.age;
    },
    setAge(value) {
    	// 만일 나이 값이 100 초과일 경우 바로 함수를 리턴해서 user.name이 재설정되지 않도록 필터링
    	if(value > 100) {
        	console.error('나이는 100을 초과할 수 없습니다.')
            return;
        }
        	
    	user.name = value;
    }
}

user.setAge(400); // 나이는 100을 초과할 수 없습니다.
```

___ 

### 자바스크립트 Getter & Setter

- ES6 최신 자바스크립트부터는 Getter와 Setter를 간단하게 정의할 수 있는 문법이 별도로 추가되었다. 
- 객체 리터럴 안에서 속성 이름 앞에 get 또는 set 키워드만 붙여 Getter와 Setter를 정의할 수 있게 되었는데, 이 방법을 사용하면 Getter와 Setter 코드를 더욱 간결하고 가독성 있게 작성할 수 있다.
   
```javascript
const user = {
	name: 'inpa',
    age: 50,
    
    // userName() 메서드 왼쪽에 get, set 키워드만 붙이면 알아서 Getter, Setter 로서 동작된다
    get userName() {
    	return user.name;
    },
    set userName(value) {
    	user.name = value;
    }
}
```

> 그런데 이때의 Getter와 Setter 은 함수 호출 형식이 아닌, 일반 프로퍼티처럼 접근해서 사용된다. getter와 setter 메서드를 구현하면 객체엔 userName이라는 가상의 프로퍼티가 생기는데, 가상의 프로퍼티는 읽고 쓸 순 있지만 실제로는 존재하지 않는 프로퍼티이다.

```javascript
console.log(user.userName); // inpa

userName = 'tistory';
```






출처: https://inpa.tistory.com/entry/JS-📚-getter-setter-란 [Inpa Dev 👨‍💻:티스토리]