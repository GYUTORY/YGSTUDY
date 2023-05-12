# require / exports
 - NodeJS에서 사용되고 있는 CommonJS 키워드이고 Ruby 언어 스타일과 비슷하다라고 볼수 있다.

# 여기서 CommonJS란?
 - CommonJS 포맷은 Node.js (서버사이드 자바스크립트) 의 표준이다.

 - 내보내기의 경우 exports 및 module.exports,
 - 가져오기의 경우 require 를 사용한다.

ex)
function func1 (param) {
 a = 1;
 return
}

function func2 (param) {
 a = 2;
 return
}

// 내보내기
exports.func1 = func1
exports.func2 = func2

// 모듈을 통한 내보내기
const obj = {

    func1: function (num) {
    	// ...
    },
    
    func2: function (num) {
    	// ...
    }
}

module.exports = obj

# import / export
 - ES6(ES2015)에서 새롭게 도입된 키워드로서 Java나 Python 언어 방식과 비슷하다.

# CommonJS
const name = '고양이';

module.exports = name;

# ES6 
const name = '고양이';

export default name;


