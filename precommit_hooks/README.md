# Enum Return Type Pre-commit Hooks

This directory contains two examples of pre-commit hooks that enforce a specific rule in C code:
**Every function must return an enum or a typedef to an enum, with the exception of arithmetic/math/calculating functions.**

The hooks ignore math/arithmetic functions based on a simple name heuristic (e.g., if the function name contains `add`, `sub`, `calc`, `math`, etc., and it returns a standard primitive type like `int` or `float`).

## Option 1: Using `libclang` (Strict Semantic Analysis)

The `check_enum_returns_clang.py` script uses `libclang` to parse the C Abstract Syntax Tree (AST). This is the **most accurate** method because it can semantically resolve typedefs across headers to determine if they ultimately map to an `enum`.

### Pre-commit Configuration

Add the following to your `.pre-commit-config.yaml`:

```yaml
  - repo: local
    hooks:
      - id: check-enum-returns-clang
        name: Check enum return types (libclang)
        entry: precommit_hooks/check_enum_returns_clang.py
        language: python
        types: [c]
        additional_dependencies: [libclang]
        # Optional: You can pass additional compiler arguments (e.g., include paths) after '--'
        # args: ['--', '-Iinclude']
```

## Option 2: Using `tree-sitter` (Lightweight & Fast)

The `check_enum_returns_treesitter.py` script uses `tree-sitter` to parse the C code structure. Tree-sitter is faster and easier to install as it does not rely on compiler toolchains. However, because it lacks a semantic model, it **cannot resolve typedefs across files**. It acts as a heuristic, flagging explicit primitive types (e.g., `int`, `float`) as violations while giving custom types (`type_identifiers`) the benefit of the doubt.

### Pre-commit Configuration

Add the following to your `.pre-commit-config.yaml`:

```yaml
  - repo: local
    hooks:
      - id: check-enum-returns-treesitter
        name: Check enum return types (tree-sitter)
        entry: precommit_hooks/check_enum_returns_treesitter.py
        language: python
        types: [c]
        additional_dependencies: [tree-sitter, tree-sitter-c]
```

## How to Test Manually

You can test either script manually on a C file:

```bash
# Using libclang
./precommit_hooks/check_enum_returns_clang.py src/my_file.c

# Using tree-sitter
./precommit_hooks/check_enum_returns_treesitter.py src/my_file.c
```

## Strict Error Percolation Hook

The `check_error_percolation_clang.py` script enforces that functions returning an `enum` have their error results explicitly checked and properly returned.

### Pre-commit Configuration

Add the following to your `.pre-commit-config.yaml`:

```yaml
  - repo: local
    hooks:
      - id: check-error-percolation-clang
        name: Check strict error percolation (libclang)
        entry: precommit_hooks/check_error_percolation_clang.py
        language: python
        types: [c]
        additional_dependencies: [libclang]
```


### Advanced Configuration (Error Percolation)

The error percolation hook supports ignoring specific functions or wildcards using `--ignore-callers` and `--ignore-callees`. 
It also handles complex control flows like `switch` statements, inline `if ((rc = foo()) != OK)` assignments, and ignores macro instantiations (such as assertions) by default.

```yaml
  - repo: local
    hooks:
      - id: check-error-percolation-clang
        name: Check strict error percolation (libclang)
        entry: precommit_hooks/check_error_percolation_clang.py
        language: python
        types: [c]
        additional_dependencies: [libclang]
        # Ignore custom callers (like test functions) or callees (like free functions)
        args: ['--ignore-callers', 'test_*', 'main', '--ignore-callees', '*_free', 'printf']
```


### Codebase Auditing and LLM Output

You can run the hook against your entire codebase manually (not just via pre-commit) to audit existing files. It supports directory expansion and can generate a markdown checkbox list grouped by file and function, designed to be fed back into an LLM for automated remediation.

```bash
# Run against the whole src/ directory and output markdown
./precommit_hooks/check_error_percolation_clang.py src/ --format markdown > AUDIT.md
```


### The Two-Layer Defense (Compiler + Hook)

For bulletproof error handling, pair this hook with native compiler enforcement. The hook verifies *control flow logic*, but the compiler is best suited to instantly catch completely discarded return values.

We provide a cross-platform header `include/c_error_percolation.h` which defines `C_ERROR_NODISCARD`. Apply this macro to your error `typedef` or `enum`.

#### 1. Layer 1: Compiler Enforcement (`nodiscard`)
If a developer writes `foo();` and ignores the return value, compiling with `-Wunused-result` (and `-Werror`) will instantly halt the build.

```c
#include "c_error_percolation.h"

// The macro expands to [[nodiscard]], __attribute__((warn_unused_result)), or _Check_return_
typedef enum C_ERROR_NODISCARD {
    SUCCESS = 0,
    ERR_FAIL = 1
} result_t;

result_t my_func(void);
```

#### 2. Layer 2: Pre-commit Hook (AST CFG Analysis)
Even if the developer captures the variable to silence the compiler (`result_t rc = my_func();`), the `check_error_percolation_clang.py` hook kicks in. It parses the AST to ensure the developer didn't just ignore `rc`, mutate it to a hacky `-1`, or forget to actively `return rc;`.

