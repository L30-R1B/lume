#include <cassert>
#include "app.hpp"
int main(){assert(parsePort("1")==1); assert(parsePort("65535")==65535); for(auto s:{"", "0", "65536", "1x", "-1", " 1", "99999999999999999999999999"}) assert(parsePort(s)==-1);}
