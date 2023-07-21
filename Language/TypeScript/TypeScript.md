
# TypeScript란?
- MicroSoft에서 개발한 정적 타입 언어로, JavaScript의 상위 집합입니다.
- JavaScript 코드를 TypeScript로 변환하면 TypeScript의 강력한 기능과 장점을 활용할 수 있습니다.


# TypeScript의 주요 특징

정적 타입
- TypeScript는 변수, 함수, 객체 등에 타입을 명시하여 컴파일 단계에서 오류를 잡을 수 있습니다. 
- 이를 통해 런타임 시 발생할 수 있는 타입 관련 버그를 사전에 방지할 수 있습니다.

개선된 도구 지원
- TypeScript는 강력한 코드 완성 기능과 자동화된 리팩토링 도구를 제공하여 개발자의 생산성을 향상시킵니다. 
- 코드 편집기나 IDE에서 타입 정보를 기반으로 코드 제안과 오류 강조 기능을 지원합니다.

대규모 애플리케이션 개발
- TypeScript는 대규모 애플리케이션 개발에 적합한 도구와 기능을 제공합니다. 
- 타입 시스템을 통해 코드베이스의 구조를 명확하게 유지하고 유지보수를 용이하게 합니다.

JavaScript와의 하위 호환성
- TypeScript는 JavaScript의 상위 집합이기 때문에 기존 JavaScript 코드를 그대로 사용하면서 점진적으로 TypeScript로 전환할 수 있습니다. 
- 이는 기존 JavaScript 프로젝트에 대한 재사용성을 높이고 안정적인 업그레이드 경로를 제공합니다.


# Running TypeScript
- TypeScript 코드를 실행하기 위해서는 TypeScript 컴파일러가 설치되어 있어야 합니다.
- TypeScript 코드를 실행하는 일반적인 절차는 다음과 같습니다.

1. .ts 확장자로 TypeScript 코드를 작성합니다. 예를 들어, app.ts 파일에 TypeScript 코드를 작성합니다.
2. TypeScript 컴파일러를 사용하여 TypeScript 코드를 JavaScript로 컴파일합니다.


    tsc app.ts


>  이 명령은 app.ts 파일을 컴파일하여 app.js 파일을 생성합니다.

3. JavaScript 실행 환경인 Node.js와 같은 JavaScript 런타임 환경에서 생성된 JavaScript 코드를 실행합니다.


    node app.js

> 위 명령은 app.js 파일을 Node.js로 실행하여 TypeScript 코드의 결과를 확인합니다.

## ts-node
- TypeScript 파일을 컴파일하지 않고도 직접 실행할 수 있게 해주는 도구
- 추가적인 설정이나 컴파일 과정 없이 바로 결과를 확인할 수 있습니다.
- Node.js에서 TypeScript 코드를 실행하고 REPL(Read-Eval-Print Loop)을 제공하는 도구입니다.
- 소스 맵과 원시 ESM(native ESM)을 지원합니다.
- ts-node를 사용하면 TypeScript 코드를 직접 실행할 수 있으며,를 확인할 수 있습니다.
> 즉, tsc 명령과는 달리 별도의 컴파일 단계 없이 TypeScript 코드를 직접 실행할 수 있도록 도와줍니다.


# 잠깐, REPL이란 무엇일까?
- REPL은 "Read-Eval-Print Loop"의 약어로, 대화형 프로그래밍 환경을 의미합니다.
- REPl은 사용자가 입력한 코드를 읽고(Read), 실행하고(Eval), 결과를 출력하고(Pring), 그리고 다음 입력을 기다리는(Loop) 동작을 반복합니다.

## REPL의 특징
- 입력 : 사용자가 명령어, 표현식 또는 코드 스니펫을 입력합니다.
- 실행 : 입력된 코드가 평가되고 실행됩니다. 결과나 에러 메시지가 반환됩니다.
- 출력 : 실행 결과나 에러 메시지 등이 출력됩니다.
- 반복 : REPL은 다음 입력을 대기하고, 사용자가 추가적인 코드를 입력하면 위의 갖정을 반복합니다.



## --require ts-node/register
- TypeScript로 작성된 파일을 실행하기 위해 ts-node 모듈을 등록하는 옵션입니다.
- TypeScript는 JavaScript를 확장한 언어로, 타입 체크와 ES6 이상의 문법을 지원하여 개발자들에게 더 안전하고 강력한 기능을 제공합니다. 
- 그러나 TypeScript 코드를 실행하려면 먼저 해당 코드를 JavaScript로 컴파일해야 합니다.



