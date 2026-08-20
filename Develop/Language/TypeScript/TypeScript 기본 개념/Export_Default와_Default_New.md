---
title: TypeScript export default와 default new
tags: [language, typescript]
updated: 2025-11-01
---

# TypeScript export default와 default new

## 배경

모듈 시스템에서 내보내기(export)는 코드를 재사용 가능한 단위로 나누는 핵심 개념이다. TypeScript는 ES6 모듈 시스템을 그대로 쓰면서 타입 정보를 얹는다.

### export default란?

`export default`는 모듈에서 주요 값 하나를 내보낼 때 쓴다. named export와 달리 모듈당 하나만 둘 수 있고, 가져올 때 중괄호 없이 원하는 이름을 붙인다.

모듈의 "기본값"이라는 뜻이라, 그 모듈이 무엇을 대표하는지가 드러난다. `Logger` 모듈이면 Logger 클래스, `config` 모듈이면 설정 객체가 기본값이면 자연스럽다.

### default new 패턴이란?

`default new`는 클래스 인스턴스를 직접 내보내는 패턴이다. 클래스 자체가 아니라 `new`로 만든 객체를 export default 한다. 싱글톤을 간단하게 구현하는 방법이고, 모듈을 가져오는 순간 이미 인스턴스화된 객체를 쓴다.

전역에 인스턴스가 하나만 있으면 되는 경우에 쓸모가 있다. 설정 관리자, 데이터베이스 연결, 이벤트 시스템처럼 애플리케이션 전체가 같은 상태를 공유해야 하는 객체가 그렇다.

## 핵심

### 1. export default의 동작 원리

#### 기본 메커니즘

`export default`는 모듈의 기본 내보내기를 지정한다. 내부적으로는 `default`라는 이름의 named export로 처리되고, 쓰는 쪽에서는 문법이 더 간결해진다.

```typescript
// math.ts - 함수를 기본 내보내기
export default function add(a: number, b: number): number {
    return a + b;
}

// main.ts - 원하는 이름으로 가져오기
import add from './math';
import calculate from './math'; // 다른 이름도 가능
```

named export와 가장 크게 갈리는 지점이 **이름의 자유도**다. named export는 내보낸 이름 그대로 가져와야 하고(아니면 `as`로 별칭을 준다), default export는 가져오는 쪽이 이름을 마음대로 정한다.

#### 여러 형태의 값 내보내기

함수, 클래스, 객체, 심지어 원시값까지 모든 JavaScript 값을 default로 내보낼 수 있다. 다만 실제로는 모듈의 주요 기능을 나타내는 함수나 클래스를 내보내는 게 보통이다.

```typescript
// 클래스 내보내기
export default class Logger {
    log(message: string): void {
        console.log(`[LOG]: ${message}`);
    }
}

// 객체 내보내기
export default {
    apiUrl: 'https://api.example.com',
    timeout: 5000
};
```

### 2. default new 패턴의 이해

#### 싱글톤 패턴과의 관계

전통적인 싱글톤 패턴은 private 생성자와 static 메서드로 인스턴스를 하나로 제한한다. default new는 이걸 더 간단하게 만든 형태다.

```typescript
// 전통적인 싱글톤
class Database {
    private static instance: Database;
    private constructor() {}
    
    static getInstance(): Database {
        if (!Database.instance) {
            Database.instance = new Database();
        }
        return Database.instance;
    }
}

// default new 방식
export default new (class Database {
    // ... 메서드들
})();
```

default new 쪽이 코드가 짧고, 모듈 시스템이 알아서 싱글톤을 보장한다. 모듈은 한 번만 실행되니 인스턴스도 한 번만 생긴다.

#### 익명 클래스와 즉시 실행

`new (class { ... })()` 문법이 낯설 텐데, 다음 과정을 한 줄로 줄인 것이다:

1. 익명 클래스를 정의한다
2. 괄호로 묶어 표현식으로 만든다
3. `new`로 인스턴스를 만든다
4. `()`는 생성자에 넘길 인자다(없으면 빈 괄호)

명명된 클래스를 써도 되고, 이쪽이 더 명확하다:

```typescript
class ConfigManager {
    private config: Record<string, any> = {};
    
    set(key: string, value: any): void {
        this.config[key] = value;
    }
    
    get<T>(key: string): T | undefined {
        return this.config[key];
    }
}

export default new ConfigManager();
```

### 3. 혼용 패턴

한 모듈에서 default export와 named export를 같이 써도 된다. 모듈의 주요 기능과 부가 기능을 나눌 때 쓸모 있다.

```typescript
// utils.ts
export function multiply(a: number, b: number): number {
    return a * b;
}

export default function add(a: number, b: number): number {
    return a + b;
}

// main.ts
import add, { multiply } from './utils';
```

주요 기능은 default로, 보조 기능은 named export로 내보내면 모듈 구조가 한눈에 들어온다.

## 실제 활용 사례

### 설정 관리

애플리케이션 설정은 전역에 하나만 있어야 하고 어디서든 접근돼야 한다. default new가 가장 잘 맞는 경우다.

```typescript
// ConfigManager.ts
class ConfigManager {
    private config: Record<string, any> = {};
    
    set(key: string, value: any): void {
        this.config[key] = value;
    }
    
    get<T>(key: string, defaultValue?: T): T | undefined {
        return this.config[key] ?? defaultValue;
    }
}

export default new ConfigManager();
```

이제 어느 모듈에서든 같은 설정 객체를 쓴다. 상태가 자동으로 공유되니 한 곳에서 넣은 값을 다른 곳에서 바로 읽는다.

### 이벤트 시스템

전역 이벤트 버스로 애플리케이션의 여러 부분이 서로 통신한다. 이쪽도 인스턴스는 하나면 된다.

```typescript
type EventHandler = (...args: any[]) => void;

class EventEmitter {
    private events: Record<string, EventHandler[]> = {};
    
    on(event: string, handler: EventHandler): void {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(handler);
    }
    
    emit(event: string, ...args: any[]): void {
        if (this.events[event]) {
            this.events[event].forEach(handler => handler(...args));
        }
    }
}

export default new EventEmitter();
```

## 주의사항

### 메모리와 성능

default new는 모듈을 임포트하는 순간 인스턴스가 만들어진다. 바로 쓸 수 있어 편하지만, 쓰지 않아도 메모리는 그대로 차지한다.

객체가 크거나 초기화가 무거우면 지연 초기화를 생각해 볼 만하다:

```typescript
class HeavyResource {
    private static instance: HeavyResource | null = null;
    
    static getInstance(): HeavyResource {
        if (!this.instance) {
            this.instance = new HeavyResource();
        }
        return this.instance;
    }
}

export default HeavyResource.getInstance();
```

그런데 이때도 `getInstance()` 호출 자체가 모듈 로드 시점에 일어난다. 진짜 지연 초기화를 원하면 팩토리 함수를 내주는 편이 낫다.

### 테스트 가능성

싱글톤의 고질병은 테스트가 어렵다는 점이다. 전역 상태를 공유하니 테스트끼리 독립적이지 않다.

리셋 메서드를 두거나 의존성 주입으로 푸는 방법이 있다:

```typescript
class ConfigManager {
    private config: Record<string, any> = {};
    
    // 테스트를 위한 리셋 메서드
    reset(): void {
        this.config = {};
    }
}
```

### 순환 의존성

default new 패턴에서 모듈끼리 순환 의존이 생기면 초기화 순서가 문제가 된다. 모듈 A가 B를 임포트하고 B가 A를 임포트하면, 어느 쪽 인스턴스가 먼저 만들어지느냐에 따라 undefined를 참조하게 된다.

이럴 땐 구조를 다시 보거나 지연 로딩을 쓴다.

## 언제 무엇을 사용할까?

### export default를 사용하는 경우

- 모듈에 명확한 주요 기능이 하나 있을 때
- React 컴포넌트처럼 파일 하나가 하나의 개념을 나타낼 때
- 외부에서 이름을 자유롭게 정하는 편이 자연스러울 때

### named export를 사용하는 경우

- 여러 관련 기능을 묶어 내보낼 때
- 트리 쉐이킹이 중요한 라이브러리를 만들 때
- 명시적인 이름이 중요한 유틸리티 함수들

### default new를 사용하는 경우

- 전역에 인스턴스가 하나만 필요할 때
- 상태를 공유해야 하는 싱글톤 객체
- 설정, 캐시, 이벤트 시스템 같은 전역 서비스

### 일반 클래스를 사용하는 경우

- 인스턴스를 여러 개 만들어야 할 때
- 인스턴스마다 상태가 독립적이어야 할 때
- 테스트 가능성이 중요할 때

## 참고

### 비교

| 구분 | export default | named export |
|------|----------------|--------------|
| 가져오기 | `import X from './m'` | `import { X } from './m'` |
| 이름 변경 | 자유롭게 가능 | `as` 키워드 필요 |
| 개수 제한 | 모듈당 1개 | 제한 없음 |
| 트리 쉐이킹 | 제한적 | 완전 지원 |
| 적합한 경우 | 단일 주요 기능 | 여러 기능 묶음 |

| 구분 | default new | 일반 클래스 |
|------|-------------|-------------|
| 인스턴스화 | 자동 (모듈 로드 시) | 수동 (`new` 사용) |
| 인스턴스 개수 | 1개 (싱글톤) | 필요한 만큼 |
| 초기화 시점 | 즉시 | 필요할 때 |
| 상태 공유 | 전역 공유 | 인스턴스별 독립 |
| 테스트 | 어려움 | 쉬움 |

TypeScript 모듈 시스템은 코드를 구조화하는 도구다. export default는 모듈의 주요 목적을 분명히 드러내고, default new는 싱글톤 구현을 줄여 준다. 패턴마다 성격이 다르니 상황을 보고 고른다.
