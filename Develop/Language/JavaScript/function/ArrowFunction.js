{
    let value = 32;
    const exampleObj = {
        value: 42,
        regularFunction: function() {
            console.log(this.value); // 42
        },
        arrowFunction: () => {
            console.log(value); // 32
        }
    };

    exampleObj.regularFunction(); // 42
    exampleObj.arrowFunction(); // 32
}
