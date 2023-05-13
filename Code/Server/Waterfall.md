# Waterfall
- First created By KYG at 2023-01-06


waterfall이란? 오늘 문득 실무 작업중, waterfall이란 단어에 대해 듣게 되었고 무슨 단어인지 찾아보게 되었다.

![](../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_C42hkN/스크린샷 2022-12-27 오후 11.10.38.png)

# Waterfall Mode

1. 시스템/소프트웨어 개발의 전통적인 공정
2. Waterfall은 폭포를 의미하는 단어로, 위에서 아래로 물이 떨어지듯이 폭포처럼 진행하는 프로세스


# Async.waterfall()
- 하지만 데이터베이스에서 정보를 읽어올 수 있도록 제공되는 모듈 자체가 대부분 비동기로 동작하다보니 다음 액션을 이어서 처리하는데 무리가 있겠다. 
- 아무튼 이런 문제를 해결할 수 있는 방법으로 async 모듈이 있고 여기서는 async 모듈에서 제공되는 waterfall 을 통해 비동기를 교통정리 해보자.


# waterfall 안에 작업 함수를 직접 구현하는 방식
    async.waterfall([
        function(callback) {
            callback(null, 'one', 'two');
        },
        function(arg1, arg2, callback) {
            // arg1 now equals 'one' and arg2 now equals 'two'
        callback(null, 'three');
        },
        function(arg1, callback) {
            // arg1 now equals 'three'
        callback(null, 'done');
        }
        ], function (err, result) {
        // result now equals 'done'
});

# waterfall 안에 함수 이름만 달아놓고 원형은 밖에 제공하는 방식

    async.waterfall(
        myFirstFunction,
        mySecondFunction,
        myLastFunction,
        , function (err, result) {
            result now equals 'done'
        });
        function myFirstFunction(callback) {
            callback(null, 'one', 'two');
        }
        function mySecondFunction(arg1, arg2, callback) {
            callback(null, 'three');
        }
        function myLastFunction(arg1, callback) {
        callback(null, 'done');
    }    



출처
https://blog.naver.com/eizkf2ny/222572080661