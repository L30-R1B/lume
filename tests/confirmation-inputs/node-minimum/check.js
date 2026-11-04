const assert = require("node:assert/strict");
const {minimum} = require("./logic");
assert.equal(minimum(2, 7), 2);
assert.equal(minimum(7, 2), 2);
assert.equal(minimum(-3, 2), -3);
assert.equal(minimum(4, 4), 4);
