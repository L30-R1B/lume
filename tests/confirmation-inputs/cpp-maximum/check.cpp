#include <cassert>
#include "logic.hpp"
int main() {
assert(maximum(2, 7) == 7);
assert(maximum(7, 2) == 7);
assert(maximum(-3, 2) == 2);
assert(maximum(4, 4) == 4);
}
