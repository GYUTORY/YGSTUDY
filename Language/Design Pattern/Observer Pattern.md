
# Observer Pattern


## 개요
- Observer Pattern은 객체들 간의 일대다 의존성을 정의하는 행위 디자인 패턴으로, 
한 객체의 상태가 변경되면 의존하는 다른 객체들에게 자동으로 알림을 보내어 상태 변경을 처리할 수 있게 해줍니다. 
- 이를 통해 객체들 사이의 결합도를 줄이고 유연하고 확장 가능한 코드를 작성할 수 있습니다.

## 내용
- Observer Pattern은 소프트웨어 개발에서 종종 발생하는 "이벤트 처리" 문제를 해결하기 위해 등장하였습니다. 
- 예를 들어, GUI 애플리케이션에서는 사용자 인터페이스 요소들 간에 서로 상호작용이 필요하며, 한 요소의 상태 변경이 다른 요소에 영향을 주는 경우가 많습니다. 
- 이때 Observer Pattern은 각 요소들을 독립적으로 유지하면서 상호작용을 가능하게 해줍니다.


## 구성요소
### Subject(주제)
- 상태 변화를 관찰하는 대상 객체입니다. 
- 주제 객체는 관찰자들을 등록하고 알림 메시지를 보내는 역할을 수행합니다.

### Observer(관찰자)
- 주제 객체의 상태 변화를 감지하고, 필요에 따라 적절한 동작을 수행하는 객체입니다.
- 주제 객체의 상태 변화를 감시하기 위해 인터페이스를 구현합니다.

## 동작 방식
1. 주제 객체는 관찰자들을 저장할 컬렉션(예: 리스트)을 가지고 있습니다.
2. 관찰자들은 주제 객체의 인터페이스를 구현하여 등록됩니다.
3. 주제 객체의 상태가 변경되면, 등록된 모든 관찰자들에게 알림을 보냅니다.
4. 각 관찰자들은 알림을 받고 적절한 동작을 수행합니다.


``` javascript
# Subject(주제) 클래스
class Subject:
def __init__(self):
self._observers = []

    def attach(self, observer):
        self._observers.append(observer)

    def detach(self, observer):
        self._observers.remove(observer)

    def notify(self, message):
        for observer in self._observers:
            observer.update(message)

# Observer(관찰자) 인터페이스
class Observer:
def update(self, message):
pass

# 구체적인 Observer 클래스
class ConcreteObserver(Observer):
def __init__(self, name):
self.name = name

    def update(self, message):
        print(f"{self.name} received message: {message}")

# 예제 실행
if __name__ == "__main__":
subject = Subject()

observer1 = ConcreteObserver("Observer 1")
observer2 = ConcreteObserver("Observer 2")

subject.attach(observer1)
subject.attach(observer2)

subject.notify("Hello, observers!")


```

