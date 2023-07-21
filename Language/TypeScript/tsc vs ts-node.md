# tsc와 ts-node
- 둘 다 TypeScript를 JavaScript로 변환하는데 사용되는 도구이지만, 사용 목적과 동작 방식에서 차이가 있습니다.

## tsc (TypeScript Compiler)
- tsc는 TypeScript의 공식 컴파일러(Compiler)입니다.
- TypeScript 파일을 JavaScript 파일로 변환하는 역할을 합니다.
- tsc를 사용하여 TypeScript 코드를 컴파일하면 결과적으로 JavaScript 파일이 생성됩니다. 
- 이렇게 생성된 JavaScript 파일은 일반적인 JavaScript 실행 환경에서 실행될 수 있습니다.

사용 방법
> tsc your-typescript-file.ts


- 위와 같이 tsc 명령어를 실행하면 your-typescript-file.ts 파일이 컴파일되어 your-typescript-file.js 파일이 생성됩니다.

## ts-node
- ts-node는 TypeScript 코드를 컴파일하지 않고 바로 실행할 수 있도록 해주는 도구입니다. 
- TypeScript 파일을 실시간으로 컴파일하여 메모리에서 실행합니다. 
- 개발 단계에서 코드 변경 시 매번 tsc로 컴파일하고 실행하는 번거로움을 줄여줍니다.
 
사용 방법
> ts-node your-typescript-file.ts

- 위와 같이 ts-node 명령어를 실행하면 your-typescript-file.ts 파일이 컴파일되어 메모리에서 실행됩니다.

# 정리
> 따라서 tsc는 TypeScript를 컴파일하여 JavaScript로 변환하는 공식 컴파일러이며, ts-node는 개발 단계에서 TypeScript를 바로 실행하기 위한 도구로 사용됩니다. 상황에 따라 두 도구를 적절하게 선택하여 사용하는 것이 좋습니다.