
# async/await
- 비동기 작업을 처리하는 데 사용되는 문법이다.
- 'async' 함수는 비동기적으로 동작하고, 'await' 키워드는 'Promise' 객체를 기다리는 동안 함수의 실행을 일시 중지 시킵니다.
- 이를 통해 비동기 코드를 동기적으로 작성하고, 가독성을 높이고, 에러 처리를 간편하게 할 수 있다.
- 'async' 함수는 항상 Promise를 반환하며, 내부에서 await 키워드를 사용하여 Promise의 처리를 기다릴 수 있습니다. 
- 이때 await 키워드는 오직 Promise 객체에서만 사용할 수 있습니다.


```javascript
// 비동기적으로 데이터를 가져오는 함수
async function fetchData(url) {
    try {
        const response = await fetch(url); // 비동기적으로 데이터를 가져옴
        const data = await response.json(); // 비동기적으로 데이터를 JSON 형식으로 변환
        return data; // 데이터 반환
    } catch (error) {
        console.log('Error:', error);
        throw error;
    }
}

// 비동기 함수를 사용하여 데이터 처리
async function process() {
    try {
        const url = 'https://api.example.com/data';
        const data = await fetchData(url); // 비동기적으로 데이터를 가져옴

        // 데이터 처리
        console.log('Data:', data);
        // 추가 작업 수행 가능
    } catch (error) {
        console.log('Error:', error);
    }
}

// 비동기 함수 실행
process();
```


> 위의 예시에서 fetchData 함수는 비동기 함수로, fetch를 사용하여 데이터를 가져오고 response.json()을 사용하여 응답 데이터를 JSON 형식으로 변환합니다.
- 이 함수는 Promise를 반환하므로 await를 사용하여 비동기적으로 데이터를 기다릴 수 있습니다.

> process 함수에서는 fetchData 함수를 호출하여 데이터를 가져오고, 가져온 데이터를 처리합니다. 
- 이때 await 키워드를 사용하여 fetchData 함수의 비동기 처리를 기다립니다.
