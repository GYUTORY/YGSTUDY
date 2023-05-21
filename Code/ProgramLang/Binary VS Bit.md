- First Created by KYG. on 2023-01-09

# Bit, Binary

# Bit란?
- Bit 는 컴퓨터에서 다루는 최소의 데이터 단위이다.
- 1 비트 를 이용해서 나타낼 수 있는 데이터 수는 "0 과 1"또는 "true 와 false" 또는 "on 과 off" 등과 같이 2가지이다.

# Binary란?
- Binary 는 2진수를 뜻한다.
- 2진수(Binary System)는 1 과 0으로 수(Number)를 나타내는 수표기법(Representation of Number) 이다.
- 여기서 수 와 수표기법에 대해서 설명을 하면 우리가 보통 일상 생활에서 쓰는 수 표기법은 10진수 이다. 
- 만약, 식탁 위에 바나나가 10개 가 있으면 그 10개 가 있다는 사실은 추상적인 수 이고 그 추상적인 수를 표현하기 위해서 우리는 다양한 수표기법을 사용한다 그 바나나의 수를 나타내기 위해 '10','열','ten' 등 앞에서 부터 차례대로 10진수 표기법, 한글, 영어 로 그 추상적인 수를 나타낼 수 있다. 
- 2진수(표기법) 으로도 그 바나나의 갯수를 나타낼수 있는데, 아래와 같이 나타낸다.

# Bit String
- 1 bit로는 2가지의 데이터밖에 표현을 하지 못하므로 많은 데이터를 표현하기 위해서 컴퓨터는 bit를 여러개 붙여서 사용한다.
- 이 bit를여러개 붙이 것을 bit string이라고 한다.
- 하지만 대부분의 컴퓨터는 무작위 갯수로 구성된 bit string을 처리하지 못하고 정해진 길이로 된 bit string을 처리 한다. 
- 길이에 따라 bit string에게 부여된 이름이 있다.

# 길이에 따른 각 bit s

nibble (4bit) 
- 4개의 bit로 구성된다. 1 니블은 16진수 1 자리로 매칭이 된다. ex) 1111 -> f

byte(8bit) 
- 2개의 니블로 구성, 대부분 CPU에서 데이터 처리를 위해 접근(읽고,쓰고)하는 단위이다. - 즉 1bit의 데이터가 필요하더라도 1byte씩 읽는 다는 얘기다

word(16bit) 
- word는 CPU마다 크기가 틀리다 80x86시스템에서는 1 word = 2byte 이다.

double word 
-2개의 word로 구성, 80x86에서는 32bit, 현재 대부분 32bit CPU를 쓰는 PC에서 CPU가 데이터 처리하는는 기본단위이다.

quad word 
- 4개의 word로 구성, 80x86에서는 64bit, 서버급 CPU에서 CPU가 이단위로 데이터를 처리 한다.

long word 
- 8개의 word (80x86에서는 128bit) 128 bit 를 기본단위로 처리하는 컴퓨터가 있나? 아직 모르겠다.



![](../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_JexooI/스크린샷 2023-01-08 오후 11.50.25.png)

- 최상위 비트는 HO 최하위 비트는 LO 라고 나타낸다.
- 나머지 똑같은 방법으로 번호가 매겨진다.
- word는 (15 ~ 0) 로 자리수가 정해지고 15~8 자리수에 있는 byte를 HO byte라고 하고 하위byte(7~0)를 LO byte라고 한다.
- double word는 31~0으로 나타내고 HO #2 #1 LO 롤 각각의 바이트를 나타낸다.
