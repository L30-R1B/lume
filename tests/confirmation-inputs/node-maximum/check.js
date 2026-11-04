const assert = require("node:assert/strict");
const {maximum} = require("./logic");
assert.equal(maximum(2, 7), 7);
assert.equal(maximum(7, 2), 7);
assert.equal(maximum(-3, 2), 2);
assert.equal(maximum(4, 4), 4);
