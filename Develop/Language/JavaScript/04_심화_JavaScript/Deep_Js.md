
### 1. 비동기 이터레이터 (Async Iterators)
- 비동기 이터레이터는 for await...of 문을 사용하여 비동기적으로 데이터를 반복할 수 있습니다.

```javascript
async function* asyncGenerator() {
    const data = [1, 2, 3];
    for (const item of data) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // 1초 대기
        yield item;
    }
}

(async () => {
    for await (const value of asyncGenerator()) {
        console.log(value); // 1, 2, 3 (1초 간격으로 출력)
    }
})();
```

### 2. Promise.allSettled
- 여러 개의 프라미스를 동시에 처리하고, 모든 프라미스의 결과를 배열로 반환합니다. 
- 각 프라미스의 성공 여부와 결과를 포함합니다.


```javascript
const promise1 = Promise.resolve(3);
const promise2 = new Promise((resolve, reject) => setTimeout(reject, 100, '에러'));
const promise3 = Promise.resolve(42);

Promise.allSettled([promise1, promise2, promise3])
    .then(results => results.forEach((result) => console.log(result)));

// 결과:
// { status: 'fulfilled', value: 3 }
// { status: 'rejected', reason: '에러' }
// { status: 'fulfilled', value: 42 }
```


### 3. WeakMap과 WeakSet
- WeakMap과 WeakSet은 가비지 컬렉션에 영향을 주지 않는 객체를 키로 사용할 수 있는 컬렉션입니다.
- 메모리 누수를 방지하는 데 유용합니다.

```javascript
let obj = {};
const weakMap = new WeakMap();
weakMap.set(obj, 'value');

console.log(weakMap.get(obj)); // 'value'

// obj가 더 이상 참조되지 않으면, weakMap에서 자동으로 제거됨
obj = null;
```

### 4. 

