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
