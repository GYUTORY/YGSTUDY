// Create a Set
const letters = new Set();

// Add Values to the Set
letters.add("a");
letters.add("b");
letters.add("c");

console.log(letters);

letters.add("a");
letters.add("b");
letters.add("c");
letters.add("c");
letters.add("c");
letters.add("c");
letters.add("c");
letters.add("c");

console.log(letters);

// Create a Set
const letters2 = new Set(["a","b","c"]);

// List all Elements
let text = "";
letters2.forEach (function(value) {
    text += value;
})

console.log(text)

