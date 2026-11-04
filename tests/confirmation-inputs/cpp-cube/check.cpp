#include <cassert>
#include "logic.hpp"
int main() {
assert(cube(3) == 27);
assert(cube(-2) == -8);
assert(cube(0) == 0);
assert(cube(1) == 1);
}
