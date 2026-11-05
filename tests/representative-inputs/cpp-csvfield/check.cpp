#include <cassert>
#include "app.hpp"
int main(){assert(csvField("")=="\"\""); assert(csvField("a,b")=="\"a,b\""); assert(csvField("a\"b")=="\"a\"\"b\"");}
