#include <cassert>
#include "logic.hpp"
int main(){
assert(retry_delay(0,2,100)==2);
assert(retry_delay(3,2,100)==16);
assert(retry_delay(60,10,1000)==1000);
assert(retry_delay(20,0,100)==0);
assert(retry_delay(2,3,0)==0);
}
