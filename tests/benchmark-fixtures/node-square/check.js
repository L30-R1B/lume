const assert = require("node:assert/strict");
const {square} = require("./logic");
assert.equal(square(3), 9);
assert.equal(square(-3), 9);
assert.equal(square(0), 0);
