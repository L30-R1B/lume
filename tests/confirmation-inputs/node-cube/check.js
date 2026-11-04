const assert = require("node:assert/strict");
const {cube} = require("./logic");
assert.equal(cube(3), 27);
assert.equal(cube(-2), -8);
assert.equal(cube(0), 0);
assert.equal(cube(1), 1);
