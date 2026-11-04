#include <cassert>
#include "logic.hpp"
int main() {
assert(parity(2) == 1);
assert(parity(3) == 0);
assert(parity(-2) == 1);
}
