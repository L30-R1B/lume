#pragma once
#include <string>
#include <cstdlib>
#include <climits>
inline std::string trim(std::string s){auto a=s.find_first_not_of(" "); if(a==std::string::npos)return ""; return s.substr(a,s.find_last_not_of(" ")-a+1);}
