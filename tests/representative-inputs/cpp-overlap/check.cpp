#include <cassert>
#include "app.hpp"
int main(){assert(overlap(1,4,3,5)); assert(!overlap(1,3,3,4)); assert(!overlap(2,2,1,4)); assert(!overlap(4,1,0,5));}
