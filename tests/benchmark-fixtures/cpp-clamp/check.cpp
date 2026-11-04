#include <cassert>
#include "logic.hpp"
int main() {
assert(clamp(2, 0, 5) == 2);
assert(clamp(-1, 0, 5) == 0);
assert(clamp(8, 0, 5) == 5);
}
