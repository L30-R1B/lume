#include <cassert>
#include "logic.hpp"
int main(){
{ std::vector<std::vector<int>> expected={{1,5}};assert(merge_intervals({{4,5},{1,3},{2,4}})==expected); }
{ std::vector<std::vector<int>> expected={{1,2},{4,6}};assert(merge_intervals({{1,2},{4,6}})==expected); }
{ std::vector<std::vector<int>> expected={{-3,0}};assert(merge_intervals({{-3,-1},{-1,0}})==expected); }
{ std::vector<std::vector<int>> expected={};assert(merge_intervals({})==expected); }
}
