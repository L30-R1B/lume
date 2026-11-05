#pragma once
#include <vector>
#include <string>
#include <cstdlib>
#include <algorithm>
#include <unordered_set>
#include <stdexcept>
#include <limits>
inline int parse_port(std::string text) { return text.empty() ? -1 : std::atoi(text.c_str()); }
