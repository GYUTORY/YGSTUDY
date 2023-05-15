# Getter & Setter

- 객체 지향 프로그래밍에서 객체의 데이터는 객체 외부에서 직접적으로 접근하는 것을 막는다.

why?
- 객체 데이터를 외부에서 읽고 변경 시 객체의 무결성이 깨질 수 있다.
ex) 자동차 속도는 음수 불가, 하지만 외부에서 음수로 설정하면 무결성이 깨진다.

  

    public void setNumber(int number) {

        if (number < 1 || number > 10) {

        throw new IllegalArgumentException();

        }
        this.number = num;
    }


위의 setter을 통해 1과 10 사이의 숫자들만 number 변수에 할당 할 수 있다. 


number이 private이므로 number을 불러오려면 자연스럽게
getter 메서드가 있어야 한다.

    public int getNumber() {
        return this.number;
    }


