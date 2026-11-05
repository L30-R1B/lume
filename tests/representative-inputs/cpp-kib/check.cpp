#include <cassert>
#include "app.hpp"
int main(){assert(kib(0)==0); assert(kib(1)==1); assert(kib(1024)==1); assert(kib(1025)==2); assert(kib(ULLONG_MAX)==ULLONG_MAX/1024+1);}
