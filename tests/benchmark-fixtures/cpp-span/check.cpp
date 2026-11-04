#include <cassert>
#include "logic.hpp"
int main() {
assert(span(2, 7) == 5);
assert(span(-3, 4) == 7);
assert(span(0, 0) == 0);
}
