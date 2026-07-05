"""Enforces enum return types in C files using tree-sitter.

This script parses C code using the tree-sitter library to ensure that
all functions (except specific mathematical functions) return an enum
or a typedef to an enum.
"""

import sys
import argparse
import fnmatch
from pathlib import Path

try:
    import tree_sitter_c as tsc
    from tree_sitter import Language, Parser
except ImportError:
    print(
        "Please install tree_sitter and tree_sitter_c: pip install tree-sitter tree-sitter-c"
    )
    sys.exit(1)

DEFAULT_SYMBOL_EXCEPTIONS = ["EM_JS"]
"""list: List of symbols that, if present in a function, exempt it from the return type check."""


def is_test_function(name: str) -> bool:
    """Checks if a function is a test function to be ignored by default.

    Args:
        name (str): The name of the function to check.

    Returns:
        bool: True if it's a test function, False otherwise.
    """
    if not name:
        return False
    return name.lower().startswith("test_") or name.startswith("TEST")


def is_math_function(name: str) -> bool:
    """Checks if a function name typically implies mathematical operations.

    Args:
        name (str): The name of the function to check.

    Returns:
        bool: True if the function is mathematically oriented, False otherwise.
    """
    if not name:
        return False
    name_lower = name.lower()
    math_keywords = [
        "add",
        "sub",
        "mul",
        "div",
        "calc",
        "math",
        "compute",
        "sum",
        "pow",
        "sqrt",
        "abs",
    ]
    return any(kw in name_lower for kw in math_keywords)


def is_memory_management_function(name: str) -> bool:
    """Checks if a function name implies memory cleanup (destroy/free).

    Args:
        name (str): The name of the function to check.

    Returns:
        bool: True if the function is a destroy or free function, False otherwise.
    """
    if not name:
        return False
    name_lower = name.lower()
    for kw in ["destroy", "free"]:
        if (
            name_lower == kw
            or name_lower.startswith(f"{kw}_")
            or name_lower.endswith(f"_{kw}")
        ):
            return True
    return False


def get_return_type_info(node, source_code: bytes) -> tuple:
    """Extracts the return type and function name from a function_definition node.

    Args:
        node: The tree-sitter function_definition node.
        source_code (bytes): The raw byte content of the C source file.

    Returns:
        tuple: A tuple of (return_type_text, function_name, is_enum, type_node).
    """
    return_type_text = ""
    function_name = ""
    is_enum = False

    declarator = None
    for child in node.children:
        if child.type == "function_declarator":
            declarator = child
        elif child.type == "pointer_declarator" and declarator is None:
            for c in child.children:
                if c.type == "function_declarator":
                    declarator = c
                    break

    if declarator:
        for child in declarator.children:
            if child.type == "identifier":
                function_name = source_code[child.start_byte : child.end_byte].decode(
                    "utf8"
                )
                break

    type_node = None
    for child in node.children:
        if child == declarator or child.type in (
            "function_declarator",
            "pointer_declarator",
        ):
            break
        if child.type == "enum_specifier":
            is_enum = True
            return_type_text = source_code[child.start_byte : child.end_byte].decode(
                "utf8"
            )
            type_node = child
        elif child.type in ("type_identifier", "primitive_type"):
            return_type_text = source_code[child.start_byte : child.end_byte].decode(
                "utf8"
            )
            type_node = child

    return return_type_text, function_name, is_enum, type_node


def walk_tree(node, node_type: str):
    """Recursively yields nodes of a specific type from a tree-sitter AST.

    Args:
        node: The starting tree-sitter node to walk.
        node_type (str): The string identifier of the node type to find.

    Yields:
        node: Matching tree-sitter nodes.
    """
    if node.type == node_type:
        yield node
    for child in node.children:
        yield from walk_tree(child, node_type)


def check_file(
    filename: str,
    parser,
    C_LANGUAGE,
    print_errors: bool = True,
    use_default_exceptions: bool = True,
    use_default_symbol_exceptions: bool = True,
) -> int:
    """Checks a single C file for enum return type violations using tree-sitter.

    Args:
        filename (str): The path to the C file to verify.
        parser: The tree-sitter Parser instance.
        C_LANGUAGE: The tree-sitter C Language object.
        print_errors (bool): Whether to print individual function errors.
        use_default_exceptions (bool): Whether to skip test functions.
        use_default_symbol_exceptions (bool): Whether to skip functions containing default exception symbols.

    Returns:
        int: The number of violations found in the file.
    """
    with open(filename, "rb") as f:
        source_code = f.read()

    tree = parser.parse(source_code)

    errors = 0
    for node in walk_tree(tree.root_node, "function_definition"):
        ret_type, func_name, is_enum_spec, type_node = get_return_type_info(
            node, source_code
        )

        if use_default_symbol_exceptions:
            func_text = source_code[node.start_byte : node.end_byte].decode(
                "utf8", errors="ignore"
            )
            if any(sym in func_text for sym in DEFAULT_SYMBOL_EXCEPTIONS):
                continue

        # Explicit enum
        if is_enum_spec:
            continue

        # Exception for math/arithmetic functions
        if is_math_function(func_name):
            continue

        # Exception for memory management functions (destroy/free) returning void
        if ret_type == "void" and is_memory_management_function(func_name):
            continue

        # Exception for test functions
        if use_default_exceptions and is_test_function(func_name):
            continue

        # If it's a primitive type, it's definitely a violation
        if type_node and type_node.type == "primitive_type":
            if print_errors:
                line = node.start_point.row + 1
                col = node.start_point.column + 1
                print(
                    f"{filename}:{line}:{col}: error: Function '{func_name}' must return an enum or typedef to enum. Returned '{ret_type}' instead."
                )
            errors += 1
        # Note: 'type_identifier' could be a typedef to an enum. Tree-sitter cannot
        # resolve this without semantic analysis, so we assume it's valid as a heuristic.
        # For stricter enforcement, use the libclang version.

    return errors


def should_exclude(
    filepath: str, exclude_patterns: list, use_default_exceptions: bool
) -> bool:
    """Checks if a file should be excluded based on patterns or default rules.

    Args:
        filepath (str): The path to the file to check.
        exclude_patterns (list): A list of glob patterns to exclude.
        use_default_exceptions (bool): Whether to apply default test file exclusions.

    Returns:
        bool: True if the file should be excluded, False otherwise.
    """
    path = Path(filepath)
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(path.name, pattern):
            return True

    if use_default_exceptions:
        if fnmatch.fnmatch(path.name, "test_*.c") or fnmatch.fnmatch(
            path.name, "test_*.h"
        ):
            return True
        if "test" in path.parts or "tests" in path.parts or "_deps" in path.parts:
            return True
    return False


def gather_files(
    paths: list, exclude_patterns: list = None, use_default_exceptions: bool = True
) -> list:
    """Gathers C files from a list of files and directories.

    Args:
        paths (list): A list of file or directory paths to search.
        exclude_patterns (list, optional): A list of glob patterns for files to exclude.
        use_default_exceptions (bool, optional): Whether to exclude test files by default.

    Returns:
        list: A sorted list of unique C file paths.
    """
    if exclude_patterns is None:
        exclude_patterns = []

    c_files = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_file():
            c_files.append(str(path))
        elif path.is_dir():
            c_files.extend(str(p) for p in path.rglob("*.c"))

    filtered_files = [
        f
        for f in c_files
        if not should_exclude(f, exclude_patterns, use_default_exceptions)
    ]
    return sorted(list(set(filtered_files)))


def main():
    """Executes the pre-commit hook logic, parsing arguments and checking files.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(
        description="Enforce enum return types for C functions using tree-sitter."
    )
    parser.add_argument(
        "paths",
        metavar="files_or_dirs",
        nargs="+",
        help="C files or directories to check",
    )
    parser.add_argument(
        "--markdown-checklist",
        action="store_true",
        help="Output a markdown checklist of non-compliant files",
    )
    parser.add_argument(
        "--exclude-files",
        action="append",
        help="Glob pattern to exclude files (can be specified multiple times)",
    )
    parser.add_argument(
        "--no-default-exceptions",
        action="store_true",
        help="Disable default exceptions for test files and functions",
    )
    parser.add_argument(
        "--no-default-symbol-exceptions",
        action="store_true",
        help="Disable default symbol exceptions (e.g. EM_JS)",
    )
    args = parser.parse_args()

    C_LANGUAGE = Language(tsc.language())
    ts_parser = Parser(C_LANGUAGE)

    files_to_check = gather_files(
        args.paths, args.exclude_files, not args.no_default_exceptions
    )

    total_errors = 0
    for filename in files_to_check:
        errors = check_file(
            filename,
            ts_parser,
            C_LANGUAGE,
            print_errors=not args.markdown_checklist,
            use_default_exceptions=not args.no_default_exceptions,
            use_default_symbol_exceptions=not args.no_default_symbol_exceptions,
        )
        if errors > 0:
            if args.markdown_checklist:
                print(f"- [ ] {filename}")
            total_errors += errors

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
