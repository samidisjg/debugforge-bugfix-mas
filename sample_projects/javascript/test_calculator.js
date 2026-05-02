const assert = require('node:assert');
const { add, divide } = require('./calculator');

assert.strictEqual(add(2, 3), 5);
assert.strictEqual(divide(10, 2), 5);
assert.throws(() => divide(5, 0));

console.log('javascript tests passed');