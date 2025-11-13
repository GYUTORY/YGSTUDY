---
title: TypeScript export default와 default new
tags: [language, typescript, typescript-기본-개념, export-default, default-new]
updated: 2025-11-01
---

# TypeScript export default와 default new

## 배경

모듈 시스템에서 내보내기(export)는 코드를 재사용 가능한 단위로 나누는 핵심 개념입니다. TypeScript는 ES6의 모듈 시스템을 그대로 사용하면서, 타입 정보를 추가로 제공합니다.

### export default란?

`export default`는 모듈에서 **하나의 주요 값**을 내보낼 때 사용하는 방식입니다. 일반적인 named export와 달리, 모듈당 하나만 존재할 수 있으며, 가져올 때 중괄호 없이 원하는 이름으로 사용할 수 있습니다.

이는 모듈의 "기본값"이라는 개념으로, 해당 모듈이 무엇을 대표하는지 명확하게 표현합니다. 예를 들어 `Logger` 모듈이라면 Logger 클래스가, `config` 모듈이라면 설정 객체가 기본값이 되는 것이 자연스럽습니다.

### default new 패턴이란?

`default new`는 클래스의 인스턴스를 직접 내보내는 패턴입니다. 클래스 자체가 아니라 `new`로 생성된 객체를 export default하는 방식이죠. 이는 싱글톤 패턴을 간단하게 구현할 수 있게 해주며, 모듈을 가져오는 순간 이미 인스턴스화된 객체를 사용할 수 있습니다.

이 패턴은 전역적으로 하나의 인스턴스만 필요한 경우에 유용합니다. 설정 관리자, 데이터베이스 연결, 이벤트 시스템처럼 애플리케이션 전체에서 동일한 상태를 공유해야 하는 객체에 적합합니다.

## 핵심

### 1. export default의 동작 원리

#### 기본 메커니즘

`export default`는 모듈의 기본 내보내기를 지정합니다. 내부적으로는 `default`라는 이름의 named export로 처리되지만, 사용자에게는 더 간결한 문법을 제공합니다.

```typescript
// math.ts - 함수를 기본 내보내기
export default function add(a: number, b: number): number {
    return a + b;
}

// main.ts - 원하는 이름으로 가져오기
import add from './math';
import calculate from './math'; // 다른 이름도 가능
```

named export와의 가장 큰 차이는 **이름의 자유도**입니다. named export는 내보낸 이름 그대로 가져와야 하지만(혹은 `as`로 별칭 지정), default export는 가져올 때 원하는 이름을 자유롭게 사용할 수 있습니다.

#### 여러 형태의 값 내보내기

함수, 클래스, 객체, 심지어 원시값까지 모든 JavaScript 값을 default로 내보낼 수 있습니다. 하지만 일반적으로는 모듈의 주요 기능을 나타내는 함수나 클래스를 내보냅니다.

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

전통적인 싱글톤 패턴은 private 생성자와 static 메서드를 사용해 인스턴스를 하나로 제한합니다. default new는 이를 더 간단하게 구현한 형태입니다.

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

default new 방식은 코드가 더 간결하고, 모듈 시스템이 자연스럽게 싱글톤을 보장합니다. 모듈은 한 번만 실행되므로, 해당 인스턴스도 한 번만 생성되기 때문입니다.

#### 익명 클래스와 즉시 실행

`new (class { ... })()`라는 문법이 낯설 수 있지만, 이는 다음과 같은 과정을 한 줄로 표현한 것입니다:

1. 익명 클래스를 정의합니다
2. 괄호로 묶어 표현식으로 만듭니다
3. `new`로 인스턴스를 생성합니다
4. `()`는 생성자에 전달할 인자입니다(없으면 빈 괄호)

명명된 클래스를 사용하는 방식도 가능하며, 이쪽이 더 명확할 수 있습니다:

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

하나의 모듈에서 default export와 named export를 함께 사용할 수 있습니다. 이는 모듈의 주요 기능과 부가 기능을 구분할 때 유용합니다.

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

주요 기능은 default로, 보조 기능들은 named export로 내보내면 모듈의 구조가 명확해집니다.

## 실제 활용 사례

### 설정 관리

애플리케이션 설정은 전역적으로 하나만 존재해야 하며, 어디서든 접근 가능해야 합니다. default new 패턴이 가장 유용한 경우입니다.

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

이제 어떤 모듈에서든 같은 설정 객체에 접근할 수 있습니다. 상태가 자동으로 공유되므로, 한 곳에서 설정한 값을 다른 곳에서 바로 읽을 수 있습니다.

### 이벤트 시스템

전역 이벤트 버스는 애플리케이션의 여러 부분이 통신할 수 있게 해줍니다. 이 역시 하나의 인스턴스만 필요합니다.

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

default new 패턴은 모듈이 임포트되는 순간 인스턴스가 생성됩니다. 이는 즉시 사용할 수 있다는 장점이 있지만, 실제로 사용하지 않아도 메모리를 차지한다는 단점도 있습니다.

큰 객체나 무거운 초기화가 필요한 경우, 지연 초기화를 고려해야 합니다:

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

하지만 이 경우에도 `getInstance()` 호출 자체가 모듈 로드 시점에 일어나므로, 진정한 지연 초기화를 위해서는 팩토리 함수를 제공하는 것이 좋습니다.

### 테스트 가능성

싱글톤 패턴의 고질적인 문제는 테스트가 어렵다는 것입니다. 전역 상태를 공유하므로, 테스트 간 독립성이 보장되지 않습니다.

이를 해결하기 위해 리셋 메서드를 제공하거나, 의존성 주입을 고려할 수 있습니다:

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

default new 패턴에서 모듈 간 순환 의존성이 발생하면, 초기화 순서 문제가 생길 수 있습니다. 모듈 A가 B를 임포트하고, B가 A를 임포트하는 경우, 어느 쪽의 인스턴스가 먼저 생성되느냐에 따라 undefined를 참조할 수 있습니다.

이런 경우 구조를 다시 검토하거나, 지연 로딩을 사용해야 합니다.

## 언제 무엇을 사용할까?

### export default를 사용하는 경우

- 모듈이 하나의 명확한 주요 기능을 가질 때
- React 컴포넌트처럼 파일 하나가 하나의 개념을 나타낼 때
- 외부에서 이름을 자유롭게 정하는 것이 자연스러울 때

### named export를 사용하는 경우

- 여러 관련 기능을 묶어 내보낼 때
- 트리 쉐이킹이 중요한 라이브러리를 만들 때
- 명시적인 이름이 중요한 유틸리티 함수들

### default new를 사용하는 경우

- 전역적으로 하나의 인스턴스만 필요할 때
- 상태를 공유해야 하는 싱글톤 객체
- 설정, 캐시, 이벤트 시스템 같은 전역 서비스

### 일반 클래스를 사용하는 경우

- 여러 인스턴스를 생성해야 할 때
- 각 인스턴스가 독립적인 상태를 가져야 할 때
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

TypeScript의 모듈 시스템은 코드를 구조화하는 강력한 도구입니다. export default는 모듈의 주요 목적을 명확히 하고, default new는 싱글톤을 쉽게 구현할 수 있게 해줍니다. 각 패턴의 특성을 이해하고 상황에 맞게 선택하는 것이 중요합니다.
