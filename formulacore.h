#ifndef FORMULACORE_H
#define FORMULACORE_H

#include <cstdint>

#ifdef _WIN32
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

extern "C" {

struct FunctionInfo {
    char name[256];
    int has_loop;
    int has_io;
    int has_string;
    int is_jittable;
};

struct AnalysisResult {
    int total_functions;
    int total_loops;
    int jittable_functions;
    FunctionInfo functions[512];
};

EXPORT int core_get_version();
EXPORT AnalysisResult* core_analyze_code(const char* code);
EXPORT void core_free_result(AnalysisResult* result);

// Injection
EXPORT const char* core_optimize_code(const char* code, int inject_jit);
EXPORT void core_free_string(const char* str);

EXPORT uint64_t core_hash_code(const char* str);

}

#endif