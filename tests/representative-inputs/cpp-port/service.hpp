#pragma once
#include <string>
#include <cstdlib>
#include <climits>
inline int parsePort(const std::string& s){return s.empty()?-1:std::atoi(s.c_str());}
