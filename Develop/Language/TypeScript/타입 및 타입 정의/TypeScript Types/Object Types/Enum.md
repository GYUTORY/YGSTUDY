---
title: TypeScript Enum 완벽 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, enum]
updated: 2025-08-10
---

# TypeScript Enum 완벽 가이드

## 배경

TypeScript에서 Enum은 이름과 연결된 상수 값들의 집합을 정의하는 데이터 타입입니다.

### Enum의 필요성
- **상수 집합**: 관련된 상수들을 하나의 그룹으로 관리
- **타입 안전성**: 미리 정의된 값만 사용하도록 제한
- **코드 가독성**: 의미 있는 이름으로 값 표현
- **유지보수성**: 중앙화된 상수 관리로 변경 용이

### 기본 개념
- **열거형**: 이름과 값이 연결된 상수 집합
- **멤버**: Enum 내의 개별 상수
- **역매핑**: 값으로부터 이름을 찾는 기능
- **자동 증가**: 명시적 값 없이 자동으로 증가하는 숫자

## 핵심

### 1. 기본 Enum 선언

#### 숫자 Enum
```typescript
enum Direction {
    Up = 1,
    Down,
    Left,
    Right
}

// 사용 예시
let playerDirection: Direction = Direction.Up;
console.log(playerDirection); // 1

let oppositeDirection: Direction = Direction.Down;
console.log(oppositeDirection); // 2
```

#### 문자열 Enum
```typescript
enum Status {
    Pending = 'PENDING',
    Approved = 'APPROVED',
    Rejected = 'REJECTED'
}

// 사용 예시
let currentStatus: Status = Status.Pending;
console.log(currentStatus); // 'PENDING'

if (currentStatus === Status.Pending) {
    console.log('처리 중입니다.');
}
```

### 2. Enum 값 접근과 역매핑

#### 멤버 접근
```typescript
enum Color {
    Red = 'RED',
    Green = 'GREEN',
    Blue = 'BLUE'
}

// 멤버 이름으로 값 접근
console.log(Color.Red); // 'RED'
console.log(Color.Green); // 'GREEN'

// 값으로 멤버 이름 접근 (숫자 Enum에서만 가능)
enum NumberEnum {
    One = 1,
    Two = 2,
    Three = 3
}

console.log(NumberEnum[1]); // 'One'
console.log(NumberEnum[2]); // 'Two'
```

#### Enum 반복
```typescript
enum DaysOfWeek {
    Sunday = 0,
    Monday = 1,
    Tuesday = 2,
    Wednesday = 3,
    Thursday = 4,
    Friday = 5,
    Saturday = 6
}

// Enum의 모든 키 가져오기
const dayNames = Object.keys(DaysOfWeek).filter(key => isNaN(Number(key)));
console.log(dayNames); // ['Sunday', 'Monday', 'Tuesday', ...]

// Enum의 모든 값 가져오기
const dayValues = Object.values(DaysOfWeek).filter(value => !isNaN(Number(value)));
console.log(dayValues); // [0, 1, 2, 3, 4, 5, 6]
```

### 3. 고급 Enum 패턴

#### 계산된 멤버
```typescript
enum FileAccess {
    None = 0,
    Read = 1 << 0,    // 1
    Write = 1 << 1,   // 2
    ReadWrite = Read | Write  // 3
}

// 사용 예시
let permissions: FileAccess = FileAccess.Read | FileAccess.Write;
console.log(permissions); // 3

if (permissions & FileAccess.Read) {
    console.log('읽기 권한이 있습니다.');
}
```

#### const Enum
```typescript
const enum UserRole {
    Admin = 'ADMIN',
    User = 'USER',
    Guest = 'GUEST'
}

// 사용 예시
let role: UserRole = UserRole.Admin;
console.log(role); // 'ADMIN'

// 컴파일 시 인라인으로 대체됨
// let role = 'ADMIN';
```

## 예시

### 1. 실제 사용 사례

#### 게임 상태 관리
```typescript
enum GameState {
    Loading = 'LOADING',
    Menu = 'MENU',
    Playing = 'PLAYING',
    Paused = 'PAUSED',
    GameOver = 'GAME_OVER'
}

class Game {
    private currentState: GameState = GameState.Loading;

    setState(newState: GameState): void {
        this.currentState = newState;
        this.handleStateChange();
    }

    private handleStateChange(): void {
        switch (this.currentState) {
            case GameState.Loading:
                console.log('게임 로딩 중...');
                break;
            case GameState.Menu:
                console.log('메인 메뉴 표시');
                break;
            case GameState.Playing:
                console.log('게임 진행 중');
                break;
            case GameState.Paused:
                console.log('게임 일시정지');
                break;
            case GameState.GameOver:
                console.log('게임 종료');
                break;
        }
    }

    getState(): GameState {
        return this.currentState;
    }
}

// 사용 예시
const game = new Game();
game.setState(GameState.Playing); // "게임 진행 중"
game.setState(GameState.Paused);  // "게임 일시정지"
```

#### HTTP 상태 코드
```typescript
enum HttpStatus {
    OK = 200,
    Created = 201,
    BadRequest = 400,
    Unauthorized = 401,
    NotFound = 404,
    InternalServerError = 500
}

class ApiResponse<T> {
    constructor(
        public status: HttpStatus,
        public data: T | null,
        public message: string
    ) {}

    isSuccess(): boolean {
        return this.status >= 200 && this.status < 300;
    }

    isError(): boolean {
        return this.status >= 400;
    }
}

// 사용 예시
const successResponse = new ApiResponse(HttpStatus.OK, { id: 1, name: '홍길동' }, '성공');
const errorResponse = new ApiResponse(HttpStatus.NotFound, null, '사용자를 찾을 수 없습니다.');

console.log(successResponse.isSuccess()); // true
console.log(errorResponse.isError());     // true
```

### 2. 고급 패턴

#### 비트 플래그 Enum
```typescript
enum Permission {
    None = 0,
    Read = 1 << 0,      // 1
    Write = 1 << 1,     // 2
    Execute = 1 << 2,   // 4
    Delete = 1 << 3,    // 8
    Admin = Read | Write | Execute | Delete  // 15
}

class User {
    constructor(
        public name: string,
        public permissions: Permission
    ) {}

    hasPermission(permission: Permission): boolean {
        return (this.permissions & permission) === permission;
    }

    addPermission(permission: Permission): void {
        this.permissions |= permission;
    }

    removePermission(permission: Permission): void {
        this.permissions &= ~permission;
    }
}

// 사용 예시
const user = new User('홍길동', Permission.Read | Permission.Write);
console.log(user.hasPermission(Permission.Read));   // true
console.log(user.hasPermission(Permission.Execute)); // false

user.addPermission(Permission.Execute);
console.log(user.hasPermission(Permission.Execute)); // true
```

#### Enum과 Union Types 조합
```typescript
enum NotificationType {
    Email = 'EMAIL',
    SMS = 'SMS',
    Push = 'PUSH'
}

type NotificationConfig = {
    [K in NotificationType]: {
        enabled: boolean;
        template: string;
    };
};

const notificationConfig: NotificationConfig = {
    [NotificationType.Email]: {
        enabled: true,
        template: 'email-template.html'
    },
    [NotificationType.SMS]: {
        enabled: false,
        template: 'sms-template.txt'
    },
    [NotificationType.Push]: {
        enabled: true,
        template: 'push-template.json'
    }
};

class NotificationService {
    sendNotification(type: NotificationType, message: string): void {
        const config = notificationConfig[type];
        if (config.enabled) {
            console.log(`${type} 알림 전송: ${message}`);
        } else {
            console.log(`${type} 알림이 비활성화되어 있습니다.`);
        }
    }
}

// 사용 예시
const notificationService = new NotificationService();
notificationService.sendNotification(NotificationType.Email, '환영합니다!');
notificationService.sendNotification(NotificationType.SMS, '인증 코드: 123456');
```

## 운영 팁

### 성능 최적화

#### const Enum 사용
```typescript
// 일반 Enum (런타임에 객체 생성)
enum RegularEnum {
    Value1 = 'VALUE1',
    Value2 = 'VALUE2'
}

// const Enum (컴파일 시 인라인으로 대체)
const enum ConstEnum {
    Value1 = 'VALUE1',
    Value2 = 'VALUE2'
}

// 사용 시 성능 차이
let regularValue = RegularEnum.Value1; // 런타임에 객체 접근
let constValue = ConstEnum.Value1;     // 컴파일 시 'VALUE1'로 대체
```

### 에러 처리

#### Enum 유효성 검사
```typescript
enum UserType {
    Admin = 'ADMIN',
    User = 'USER',
    Guest = 'GUEST'
}

function isValidUserType(value: string): value is UserType {
    return Object.values(UserType).includes(value as UserType);
}

function createUser(type: string, name: string) {
    if (!isValidUserType(type)) {
        throw new Error(`유효하지 않은 사용자 타입: ${type}`);
    }
    
    return {
        type: type as UserType,
        name: name
    };
}

// 사용 예시
try {
    const user1 = createUser('ADMIN', '관리자'); // 성공
    const user2 = createUser('INVALID', '사용자'); // 오류
} catch (error) {
    console.error(error.message);
}
```

## 참고

### Enum vs Union Types 비교표

| 특징 | Enum | Union Types |
|------|------|-------------|
| **런타임 존재** | ✅ 객체로 존재 | ❌ 타입만 존재 |
| **역매핑** | ✅ 지원 | ❌ 지원 안함 |
| **자동 증가** | ✅ 지원 | ❌ 지원 안함 |
| **번들 크기** | 더 큼 | 더 작음 |
| **타입 안전성** | ✅ 높음 | ✅ 높음 |

### Enum 사용 권장사항

1. **명명 규칙**: Enum 이름은 PascalCase, 멤버는 UPPER_SNAKE_CASE
2. **값 할당**: 명시적 값 할당으로 의도 명확화
3. **const Enum**: 성능이 중요한 경우 const enum 사용
4. **문서화**: 복잡한 Enum은 JSDoc으로 문서화

### 결론
TypeScript의 Enum은 관련된 상수들을 체계적으로 관리하는 강력한 도구입니다.
숫자 Enum과 문자열 Enum을 상황에 맞게 선택하여 사용하세요.
const enum을 활용하여 성능을 최적화하세요.
비트 플래그 Enum으로 복잡한 권한 시스템을 구현할 수 있습니다.
Enum과 Union Types의 차이를 이해하고 적절한 상황에서 사용하세요.
Enum의 역매핑 기능을 활용하여 값과 이름 간의 양방향 변환을 수행하세요.

