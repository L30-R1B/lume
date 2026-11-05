#include <cassert>
#include "app.hpp"
int main(){assert(trim(" \tvalue\r\n")=="value"); assert(trim("  ")==""); assert(trim("a b")=="a b");}
