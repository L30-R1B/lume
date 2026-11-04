const assert = require("node:assert/strict");
const {parity} = require("./logic");
assert.equal(parity(2), true);
assert.equal(parity(3), false);
assert.equal(parity(-2), true);
