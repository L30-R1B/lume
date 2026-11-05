#include <cassert>
#include "logic.hpp"
int main(){
assert(parse_port("1")==1);
assert(parse_port("65535")==65535);
assert(parse_port("8080")==8080);
assert(parse_port("0")==-1);
assert(parse_port("65536")==-1);
assert(parse_port("-1")==-1);
assert(parse_port("1x")==-1);
assert(parse_port("")==-1);
assert(parse_port(" 80")==-1);
assert(parse_port("\uff11\uff12")==-1);
assert(parse_port("\u0661\u0662")==-1);
assert(parse_port("99999999999999999999999999")==-1);
}
