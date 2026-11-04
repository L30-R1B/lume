#include <cassert>
#include "logic.hpp"
int main() {
assert(distance(2, 7) == 5);
assert(distance(7, 2) == 5);
assert(distance(-3, 2) == 5);
assert(distance(4, 4) == 0);
}
