#include <cassert>
#include "logic.hpp"
int main() {
assert(minimum(2, 7) == 2);
assert(minimum(7, 2) == 2);
assert(minimum(-3, 2) == -3);
assert(minimum(4, 4) == 4);
}
