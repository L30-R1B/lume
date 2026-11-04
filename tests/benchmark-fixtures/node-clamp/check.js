const assert = require("node:assert/strict");
const {clamp} = require("./logic");
assert.equal(clamp(2, 0, 5), 2);
assert.equal(clamp(-1, 0, 5), 0);
assert.equal(clamp(8, 0, 5), 5);
