
// 일반 Function
const exampleObj = {
    value: 42,
    regularFunction: function() {
        const self = this; // this를 보존하기 위해 self에 할당
        setTimeout(function() {
            console.log(self.value); // self를 사용해서 this를 유지
        }, 1000);
    }
};

// Arrow Function
const arrowExampleObj = {
    value: 42,
    arrowFunction: function() {
        setTimeout(() => {
            console.log(this.value); // this가 유지됨
        }, 1000);
    }
};
