
# ENUM
- 열거형(Enumeration)을 나타내는 데이터 타입입니다.
- ENUM은 이름과 연결된 숫자 값 집합을 나타내며, 특정 값 집합 중 하나를 선택할 수 있도록 도와줍니다.
- ENUM을 사용하여 상수 집합을 정의하고 사용할 수 있습니다.

# 사용 방법과 특징
ENUM 선언하기
- ENUM은 enum 키워드를 사용하여 선언됩니다. 
- 열거형 이름은 PascalCase를 사용하여 정의합니다.
- 각 멤버는 대문자로 작성되며, 값을 할당할 수 있습니다. 값은 숫자 또는 문자열일 수 있습니다.

```typescript
enum Direction {
Up = 1,
Down,
Left,
Right
}
```


ENUM 값 사용하기
- ENUM의 멤버는 해당 ENUM 자체를 타입으로 사용할 수 있습니다.
- ENUM 멤버는 멤버 이름 또는 멤버 값으로 접근할 수 있습니다.

```typescript
let playerDirection: Direction = Direction.Up;
console.log(playerDirection); // 출력: 1

let oppositeDirection: Direction = Direction.Down;
console.log(oppositeDirection); // 출력: 2
```

ENUM 값의 역참조
- ENUM 값에서 멤버 이름을 얻는 것도 가능합니다.
```typescript
let directionName: string = Direction[2];
console.log(directionName); // 출력: "Down"
```
ENUM의 추가 기능
- ENUM은 숫자를 자동으로 증가시킬 수도 있고, 반복 가능한 열거형도 정의할 수 있습니다.
- ENUM 멤버에는 값 대신 계산된 멤버(computed member)를 사용할 수도 있습니다.

```typescript
enum Status {
Pending = 'PENDING',
Approved = 'APPROVED',
Rejected = 'REJECTED'
}
```
