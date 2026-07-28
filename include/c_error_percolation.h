/**
 * @file c_error_percolation.h
 * @brief Compiler attributes for enforcing strict error percolation in C.
 *
 * This header provides cross-platform macros to enforce that return values
 * (specifically error enums) are not discarded by the caller. When paired
 * with the AST percolation hook, this forms a two-layer defense mechanism.
 */

#ifndef C_ERROR_PERCOLATION_H
#define C_ERROR_PERCOLATION_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @def C_ERROR_NODISCARD
 * @brief Marks a return type or function such that discarding its return value emits a compiler warning.
 *
 * Usage on a typedef:
 *   typedef enum C_ERROR_NODISCARD { OK, ERR } my_error_t;
 *
 * Usage on a function:
 *   C_ERROR_NODISCARD my_error_t do_something(void);
 */
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 202311L
    /* C23 and later */
    #define C_ERROR_NODISCARD [[nodiscard]]
#elif defined(__cplusplus) && __cplusplus >= 201703L
    /* C++17 and later */
    #define C_ERROR_NODISCARD [[nodiscard]]
#elif defined(__GNUC__) || defined(__clang__)
    /* GCC / Clang */
    #define C_ERROR_NODISCARD __attribute__((warn_unused_result))
#elif defined(_MSC_VER) && _MSC_VER >= 1700
    /* MSVC (Requires SAL) */
    #include <sal.h>
    #define C_ERROR_NODISCARD _Check_return_
#else
    /* Fallback for unsupported compilers */
    #define C_ERROR_NODISCARD
#endif

#ifdef __cplusplus
}
#endif

#endif /* C_ERROR_PERCOLATION_H */
