const assert = require("node:assert/strict");
const {span} = require("./logic");
assert.equal(span(2, 7), 5);
assert.equal(span(-3, 4), 7);
assert.equal(span(0, 0), 0);
