# C Tooling Headers

This directory contains reusable, cross-platform C headers designed to enforce code quality, safety, and strict conventions across your C projects.

---

## Strict Error Percolation (`c_error_percolation.h`)

In C, silently ignoring errors is a leading cause of undefined behavior and security vulnerabilities. The tooling in this repository relies on a **Two-Layer Defense** to guarantee that errors are handled correctly.

1. **Layer 1 (The Compiler):** Instantly warns you if an error value is completely discarded (e.g., calling `foo();` without capturing the result).
2. **Layer 2 (The AST Hook):** Ensures the logic is sound. It verifies that captured errors are checked with `if`, not mutated, and properly percolated up the call stack via `return`.

This header provides the missing link for **Layer 1**.

### How to use it

To enable compiler enforcement, include `c_error_percolation.h` and apply the `C_ERROR_NODISCARD` macro to your project's primary error type. 

#### 1. Applying to an Enum / Typedef (Recommended)

The best approach is to apply the macro directly to your error enum. This automatically enforces the rule on *every* function that returns this type, without having to tag individual functions.

```c
#include "c_error_percolation.h"

// Define your error type. The macro must go after the 'enum' keyword in a typedef.
typedef enum C_ERROR_NODISCARD {
    RESULT_SUCCESS = 0,
    RESULT_ERR_MEMORY,
    RESULT_ERR_NETWORK
} result_t;

// You do NOT need to tag the function anymore. 
// Returning result_t is enough.
result_t connect_to_database(void);

int main(void) {
    // ❌ COMPILER WARNING/ERROR: Return value discarded
    connect_to_database(); 
    
    // ✅ PASSES COMPILER: Value captured
    result_t rc = connect_to_database();
    
    return 0;
}
```

#### 2. Applying to Individual Functions

If you are dealing with primitive return types (like `int` or `bool`) where you only want enforcement on *specific* functions, you can place the macro at the beginning of the function declaration.

```c
#include "c_error_percolation.h"

// The caller MUST capture the return value of this function
C_ERROR_NODISCARD int init_system(void);

// The caller can safely ignore the return value of this function
int get_system_uptime(void);
```

### Compiler Support

`C_ERROR_NODISCARD` seamlessly adapts to the compiler evaluating the code:

* **C23 / C++17:** Uses the native `[[nodiscard]]` attribute.
* **GCC / Clang:** Uses `__attribute__((warn_unused_result))`.
* **MSVC:** Uses SAL annotations (`_Check_return_`).

For strict enforcement in CI environments, compile your project with `-Werror` (or `/WX` on MSVC) to promote these warnings to hard compilation failures.