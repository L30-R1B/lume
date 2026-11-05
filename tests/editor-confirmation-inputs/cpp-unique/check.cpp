#include <cassert>
#include "logic.hpp"
int main(){
{ std::vector<int> expected={3,1,2};assert(unique({3,1,3,2,1})==expected); }
{ std::vector<int> expected={};assert(unique({})==expected); }
{ std::vector<int> expected={-1,0};assert(unique({-1,-1,0})==expected); }
}
