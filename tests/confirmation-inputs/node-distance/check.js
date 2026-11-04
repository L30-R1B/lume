const assert = require("node:assert/strict");
const {distance} = require("./logic");
assert.equal(distance(2, 7), 5);
assert.equal(distance(7, 2), 5);
assert.equal(distance(-3, 2), 5);
assert.equal(distance(4, 4), 0);
