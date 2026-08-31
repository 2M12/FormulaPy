#include "formulacore.h"
#include <string>
#include <vector>
#include <sstream>
#include <cstring>
#include <algorithm>

extern "C" EXPORT uint64_t core_hash_code(const char* str) {
    uint64_t hash = 14695981039346656037ULL;
    while (*str) {
        hash ^= (uint64_t)(unsigned char)(*str++);
        hash *= 1099511628211ULL;
    }
    return hash;
}

bool is_jittable_logic(const std::string& body) {
    bool has_loop = false;
    bool has_io = false;

    bool in_string = false;
    char string_char = 0;
    
    for (size_t i = 0; i < body.length(); ++i) {
        char c = body[i];
        
        if (in_string) {
            if (c == '\\') i++;
            else if (c == string_char) in_string = false;
            continue;
        }
        
        if (c == '"' || c == '\'') {
            in_string = true;
            string_char = c;
            continue;
        }
        
        if (c == '#') {
            while (i < body.length() && body[i] != '\n') i++;
            continue;
        }

        if (i + 3 < body.length() && body.substr(i, 4) == "for " && (i == 0 || !isalnum(body[i-1]))) has_loop = true;
        if (i + 5 < body.length() && body.substr(i, 6) == "while " && (i == 0 || !isalnum(body[i-1]))) has_loop = true;
        
        if (i + 5 < body.length() && body.substr(i, 6) == "print(" && (i == 0 || !isalnum(body[i-1]))) has_io = true;
        if (i + 5 < body.length() && body.substr(i, 6) == "input(" && (i == 0 || !isalnum(body[i-1]))) has_io = true;
        if (i + 4 < body.length() && body.substr(i, 5) == "open(" && (i == 0 || !isalnum(body[i-1]))) has_io = true;
    }
    
    return has_loop && !has_io;
}

extern "C" {

EXPORT int core_get_version() {
    return 4;
}

EXPORT AnalysisResult* core_analyze_code(const char* code) {
    AnalysisResult* result = new AnalysisResult();
    std::memset(result, 0, sizeof(AnalysisResult));
    if (!code) return result;
    // WIP
    return result;
}

EXPORT const char* core_optimize_code(const char* code, int inject_jit) {
    if (!code) return nullptr;
    
    std::string source(code);
    std::istringstream stream(source);
    std::string line;
    std::string optimized_source = "";
    
    std::vector<std::string> buffer;
    std::string current_func_body = "";
    std::string current_func_def = "";
    std::string current_indent = "";
    bool in_function = false;

    while (std::getline(stream, line)) {
        std::string trimmed = line;
        trimmed.erase(0, trimmed.find_first_not_of(" \t\r"));
        trimmed.erase(trimmed.find_last_not_of(" \t\r\n") + 1);

        if (trimmed.empty()) continue; 
        
        if (trimmed.substr(0, 4) == "def ") {
            if (in_function) {
                if (inject_jit && is_jittable_logic(current_func_body)) {
                    optimized_source += current_indent + "@_formulapy_jit\n";
                }
                optimized_source += current_func_def + "\n" + current_func_body;
            }
            
            in_function = true;
            current_func_def = line;
            current_indent = line.substr(0, line.find_first_not_of(" \t"));
            current_func_body = "";
            continue;
        }

        if (in_function) {
            std::string line_indent = line.substr(0, line.find_first_not_of(" \t\r\n"));
            if (line_indent.length() <= current_indent.length() && trimmed[0] != '#') {
                if (inject_jit && is_jittable_logic(current_func_body)) {
                    optimized_source += current_indent + "@_formulapy_jit\n";
                }
                optimized_source += current_func_def + "\n" + current_func_body;
                
                in_function = false;
                current_func_body = "";
                optimized_source += line + "\n";
            } else {
                current_func_body += line + "\n";
            }
        } else {
            optimized_source += line + "\n";
        }
    }

    if (in_function) {
        if (inject_jit && is_jittable_logic(current_func_body)) {
            optimized_source += current_indent + "@_formulapy_jit\n";
        }
        optimized_source += current_func_def + "\n" + current_func_body;
    }

    char* result = new char[optimized_source.length() + 1];
    std::strcpy(result, optimized_source.c_str());
    return result;
}

EXPORT void core_free_result(AnalysisResult* result) {
    if (result) delete result;
}

EXPORT void core_free_string(const char* str) {
    if (str) delete[] str;
}

}