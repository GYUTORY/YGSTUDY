// Create a Map
const fruits = new Map([
    ["apples", 500],
    ["bananas", 300],
    ["oranges", 200]
]);

//The delete() Method
//The delete() method removes a Map element:
fruits.delete("apples");
// true/false 판단
console.log(fruits.has("apples"));

//result
console.log(fruits);


// Create a Map
const fruits2 = new Map();

// Set Map Values
fruits2.set("apples", 500);
fruits2.set("bananas", 300);
fruits2.set("oranges", 200);

console.log(fruits2);

