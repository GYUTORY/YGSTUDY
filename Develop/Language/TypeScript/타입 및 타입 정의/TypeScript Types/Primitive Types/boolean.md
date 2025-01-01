
# boolean
- TypeScript에서의 기본 데이터 타입으로, true 또는 false와 같은 논리적인 불리언 값을 나타냅니다.


    let isTrue: boolean = true;
    let isFalse: boolean = false;

> boolean 타입은 주로 조건문, 논리 연산 등에서 사용되며, 두 가지 가능한 값을 가질 수 있습니다: true(참) 또는 false(거짓).

선언
- 변수를 선언할 때 타입 어노테이션으로 boolean을 명시할 수 있으며, 해당 변수는 boolean 값 만을 가질 수 있습니다.
- 위의 예시에서  isTrue와 isFalse 변수는 각각 true와 false 값을 가집니다.

> boolean 값은 조건문에서 조건을 평가하고 실행 흐름을 제어하는 데 사용됩니다.

    let isLogged: boolean = true;

    if (isLogged) {
        console.log('User is logged in');
    } else {
        console.log('User is not logged in');
    }

- 위의 예시에서는 isLogged 변수가 true로 설정되어 있으므로, 'User is logged in'이 출력됩니다.
- 만약 isLogged가 false로 설정되어 있다면, 'User is not logged in'이 출력될 것입니다.
