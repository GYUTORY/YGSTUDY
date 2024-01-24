# CommonJs와 ESM이 대체 뭘까?
- JavaScript에서 모듈을 작성하고 가져오는 두 가지 주요한 방식


# CommonJS
- CommonJS는 Node.js에서 주로 사용되는 모듈 시스템입니다.
- CommonJS 모듈은 require() 함수를 사용하여 다른 모듈을 가져올 수 있습니다.
- 예시로, 다음과 같이 CommonJS 문법으로 모듈을 작성하고 사용할 수 있습니다.


    // 모듈 내보내기
    exports.sum = function(a, b) {
    return a + b;
    };
    
    // 모듈 가져오기
    const math = require('./math');
    console.log(math.sum(2, 3)); // 출력: 5


# ESM (ECMAScript Modules)
- ESM은 JavaScript의 표준 모듈 시스템입니다. 
- ES6 이후 버전에서 지원되며, import와 export 키워드를 사용하여 모듈을 가져오고 내보냅니다.
- 예시로, 다음과 같이 ESM 문법으로 모듈을 작성하고 사용할 수 있습니다.


        // 모듈 내보내기
        export function sum(a, b) {
        return a + b;
        }
        
        // 모듈 가져오기
        import { sum } from './math';
        console.log(sum(2, 3)); // 출력: 5


# CommonJS와 ESM의 주요한 차이점

문법
- CommonJS는 require()와 exports를 사용하고, ESM은 import와 export를 사용합니다.

동기 vs 비동기
- CommonJS는 동기적으로 모듈을 가져오는 반면, ESM은 비동기적으로 모듈을 가져옵니다.

런타임 평가 vs 정적 평가
- CommonJS는 모듈을 런타임에 평가하고 가져옵니다. 
- ESM은 모듈을 정적으로 분석하여 가져옵니다.

동적 모듈 로딩
- ESM은 동적으로 모듈을 로딩하는 기능을 제공합니다.
- CommonJS는 일반적으로 동적 모듈 로딩을 지원하지 않습니다.
