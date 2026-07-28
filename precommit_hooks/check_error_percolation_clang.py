"""Pre-commit hook to enforce error percolation in C using libclang.

This module provides strict AST-based checks to ensure that functions
returning enums are properly captured, checked, and percolated without
modification or discarding.
"""

import sys
import argparse
import glob
import fnmatch
from pathlib import Path
from typing import List, Optional, Iterator, Tuple

import clang.cindex
from clang.cindex import (
    Cursor,
    CursorKind,
    TypeKind,
    CompilationDatabase,
    CompilationDatabaseError,
)

DEFAULT_IGNORE_CALLERS = ["test_*", "TEST*", "main"]
DEFAULT_IGNORE_CALLEES = ["*_free", "*_destroy", "printf"]


def is_ignored(name: Optional[str], patterns: List[str]) -> bool:
    """Checks if a name matches any of the glob patterns.

    Args:
        name: The name to check.
        patterns: A list of glob patterns.

    Returns:
        True if the name matches a pattern, False otherwise.
    """
    if not name:
        return False
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


class Violation:
    """Represents a rule violation found during percolation analysis."""

    def __init__(
        self,
        filename: str,
        line: int,
        column: int,
        message: str,
        symbol: str = "<global>",
    ) -> None:
        """Initializes a violation.

        Args:
            filename: The source file name.
            line: The line number.
            column: The column number.
            message: The error description.
            symbol: The name of the function where the violation occurred.
        """
        self.filename = filename
        self.line = line
        self.column = column
        self.message = message
        self.symbol = symbol


def get_underlying_type(cursor_type: clang.cindex.Type) -> clang.cindex.Type:
    """Resolves typedefs and elaborated types to their base type.

    Args:
        cursor_type: The type to resolve.

    Returns:
        The underlying type, or the original if not a typedef/elaborated.
    """
    current_type = cursor_type
    while current_type.kind in (TypeKind.TYPEDEF, TypeKind.ELABORATED):
        if current_type.kind == TypeKind.TYPEDEF:
            decl = current_type.get_declaration()
            underlying = decl.underlying_typedef_type
            if underlying.kind == TypeKind.INVALID:
                break
            current_type = underlying
        else:  # ELABORATED
            underlying = current_type.get_named_type()
            if underlying.kind == TypeKind.INVALID:
                break
            current_type = underlying
    return current_type


def is_enum_type(cursor_type: clang.cindex.Type) -> bool:
    """Checks if a given type eventually resolves to an enum.

    Args:
        cursor_type: The type to evaluate.

    Returns:
        True if the type is an enum or typedef to enum.
    """
    return get_underlying_type(cursor_type).kind == TypeKind.ENUM


def contains_node(root: Cursor, target: Cursor) -> bool:
    """Checks if `target` is a descendant of `root`.

    Args:
        root: The root node to search.
        target: The node to look for.

    Returns:
        True if target is found within root's descendants.
    """
    if root == target:
        return True
    for child in root.get_children():
        if contains_node(child, target):
            return True
    return False


def get_next_statement(stmt: Cursor, block: Cursor) -> Optional[Cursor]:
    """Gets the next statement in a block after `stmt`.

    Args:
        stmt: The current statement.
        block: The enclosing block.

    Returns:
        The next statement node, or None.
    """
    children = list(block.get_children())
    try:
        idx = children.index(stmt)
        if idx + 1 < len(children):
            return children[idx + 1]
    except ValueError:
        pass
    return None


def extract_variable_name(node: Cursor) -> Optional[str]:
    """Extracts the assigned variable name from an assignment or decl.

    Args:
        node: The AST node to inspect.

    Returns:
        The variable name as a string, or None.
    """
    if node.kind == CursorKind.VAR_DECL:
        return node.spelling
    if node.kind == CursorKind.DECL_STMT:
        children = list(node.get_children())
        if children and children[0].kind == CursorKind.VAR_DECL:
            return children[0].spelling
    if node.kind == CursorKind.BINARY_OPERATOR:
        # Assuming assignment '='. Left child is the variable.
        children = list(node.get_children())
        if children and children[0].kind == CursorKind.DECL_REF_EXPR:
            return children[0].spelling
    return None


def check_percolation(
    node: Cursor, var_name: str, function_decl: Optional[Cursor] = None
) -> List[str]:
    """Validates the strict percolation rules within an if-statement body.

    Args:
        node: The if-statement body node.
        var_name: The variable name expected to be percolated.
        function_decl: The enclosing function declaration, used for goto heuristics.

    Returns:
        A list of error messages, empty if valid.
    """
    errors: List[str] = []
    has_return = False
    has_goto = False

    for stmt in node.walk_preorder():
        if stmt.kind == CursorKind.GOTO_STMT:
            has_goto = True

        if stmt.kind == CursorKind.RETURN_STMT:
            # We need to find the variable being returned. It might be buried in UNEXPOSED_EXPR or IMPCAST_EXPR
            for child in stmt.walk_preorder():
                if (
                    child.kind == CursorKind.DECL_REF_EXPR
                    and child.spelling == var_name
                ):
                    has_return = True
                    break

        if stmt.kind == CursorKind.BINARY_OPERATOR:
            # Check for mutation before return inside this block
            children = list(stmt.get_children())
            if children and children[0].kind == CursorKind.DECL_REF_EXPR:
                if children[0].spelling == var_name:
                    errors.append(f"Error variable '{var_name}' mutated before return")

    if not has_return:
        if has_goto and function_decl:
            # Heuristic for goto: check if the function as a whole returns the variable
            # We don't do full CFG to prove mutation hasn't happened before return
            for stmt in function_decl.walk_preorder():
                if stmt.kind == CursorKind.RETURN_STMT:
                    for child in stmt.walk_preorder():
                        if (
                            child.kind == CursorKind.DECL_REF_EXPR
                            and child.spelling == var_name
                        ):
                            has_return = True
                            break
                if has_return:
                    break

        if not has_return:
            errors.append(f"Error variable '{var_name}' not returned")

    return errors


def is_macro_instantiation(node: Cursor) -> bool:
    """Checks if a node is part of a macro instantiation.

    Args:
        node: The AST node to check.

    Returns:
        True if it's a macro instantiation, False otherwise.
    """
    if not hasattr(clang.cindex.conf.lib, "clang_Location_isFromMainFile"):
        clang.cindex.conf.lib.clang_Location_isFromMainFile.restype = bool
        clang.cindex.conf.lib.clang_Location_isFromMainFile.argtypes = [
            clang.cindex.SourceLocation
        ]

    return not clang.cindex.conf.lib.clang_Location_isFromMainFile(node.location)


def analyze_call(call_expr: Cursor, parent_map: dict) -> List[Violation]:
    """Analyzes a single function call for strict percolation.

    Args:
        call_expr: The call expression node.
        parent_map: A mapping of nodes to their parents.

    Returns:
        A list of Violations.
    """
    violations: List[Violation] = []

    # In some python bindings of libclang, call_expr.type represents the return type of the call
    return_type = call_expr.type
    if return_type.kind == TypeKind.INVALID:
        # Fallback for some versions
        return_type = call_expr.type.get_result()

    if not is_enum_type(return_type):
        return violations

    if is_macro_instantiation(call_expr):
        return violations

    # Find the enclosing function symbol
    symbol = "<global>"
    func_decl = None
    sym_curr = call_expr
    while sym_curr:
        if sym_curr.kind == CursorKind.FUNCTION_DECL:
            symbol = sym_curr.spelling
            func_decl = sym_curr
            break
        sym_curr = parent_map.get(sym_curr)

    # Find the top-level statement in the block containing this call
    current = call_expr
    parent = parent_map.get(current)

    # Walk up until the parent is a COMPOUND_STMT (meaning 'current' is the direct statement)
    while parent and parent.kind != CursorKind.COMPOUND_STMT:
        # Stop if we hit a FUNCTION_DECL and haven't found a COMPOUND_STMT
        if parent.kind == CursorKind.FUNCTION_DECL:
            break
        current = parent
        parent = parent_map.get(current)

    if not parent or parent.kind != CursorKind.COMPOUND_STMT:
        return violations  # Couldn't find block

    enclosing_stmt = current
    stmt_parent = parent

    if enclosing_stmt.kind == CursorKind.RETURN_STMT:
        return violations  # direct return is fine

    # Handle inline assignments: if ((rc = foo()) != OK) { ... }
    is_inline = enclosing_stmt.kind in (CursorKind.IF_STMT, CursorKind.WHILE_STMT)

    if is_inline:
        var_name = None
        for node in enclosing_stmt.walk_preorder():
            if node.kind == CursorKind.BINARY_OPERATOR:
                children = list(node.get_children())
                if len(children) >= 2 and children[0].kind == CursorKind.DECL_REF_EXPR:
                    if (
                        contains_node(children[1], call_expr)
                        or children[1] == call_expr
                    ):
                        var_name = children[0].spelling
                        break

        if not var_name:
            violations.append(
                Violation(
                    call_expr.location.file.name,
                    call_expr.location.line,
                    call_expr.location.column,
                    "Enum return value discarded or not assigned in inline condition",
                    symbol,
                )
            )
            return violations

        if_children = list(enclosing_stmt.get_children())
        if len(if_children) > 1:
            body = if_children[1]
            errors = check_percolation(body, var_name, func_decl)
            for err in errors:
                violations.append(
                    Violation(
                        call_expr.location.file.name,
                        call_expr.location.line,
                        call_expr.location.column,
                        err,
                        symbol,
                    )
                )
        return violations

    # Check if the call itself is a direct child of the compound statement (discarded return)
    # The current statement *is* the call expr
    if enclosing_stmt.kind == CursorKind.CALL_EXPR:
        violations.append(
            Violation(
                call_expr.location.file.name,
                call_expr.location.line,
                call_expr.location.column,
                "Enum return value discarded or not assigned",
                symbol,
            )
        )
        return violations

    # Extract var name
    var_name = None
    if enclosing_stmt.kind == CursorKind.DECL_STMT:
        # Find the VAR_DECL inside
        for child in enclosing_stmt.get_children():
            if child.kind == CursorKind.VAR_DECL:
                var_name = child.spelling
                break
    elif enclosing_stmt.kind == CursorKind.BINARY_OPERATOR:
        # Assuming assignment '='. Left child is the variable.
        children = list(enclosing_stmt.get_children())
        if children and children[0].kind == CursorKind.DECL_REF_EXPR:
            var_name = children[0].spelling

    if not var_name:
        violations.append(
            Violation(
                call_expr.location.file.name,
                call_expr.location.line,
                call_expr.location.column,
                "Could not determine assigned variable for enum return",
                symbol,
            )
        )
        return violations

    # Find next statement
    next_stmt = get_next_statement(enclosing_stmt, stmt_parent)

    if not next_stmt or next_stmt.kind not in (
        CursorKind.IF_STMT,
        CursorKind.SWITCH_STMT,
    ):
        violations.append(
            Violation(
                call_expr.location.file.name,
                call_expr.location.line,
                call_expr.location.column,
                f"Error variable '{var_name}' not immediately checked",
                symbol,
            )
        )
        return violations

    # We found the if/switch, check percolation inside
    stmt_children = list(next_stmt.get_children())
    if len(stmt_children) > 1:
        # 0 is condition, 1 is body
        body = stmt_children[1]
        errors = check_percolation(body, var_name, func_decl)
        for err in errors:
            violations.append(
                Violation(
                    call_expr.location.file.name,
                    call_expr.location.line,
                    call_expr.location.column,
                    err,
                    symbol,
                )
            )

    return violations


def build_parent_map(cursor: Cursor, parent_map: dict) -> None:
    """Builds a dictionary mapping child nodes to their parents.

    Args:
        cursor: The root node.
        parent_map: The dictionary to populate.
    """
    for child in cursor.get_children():
        parent_map[child] = cursor
        build_parent_map(child, parent_map)


def process_file(
    filename: str,
    compile_args: List[str],
    index: clang.cindex.Index,
    ignore_callers: List[str],
    ignore_callees: List[str],
) -> List[Violation]:
    """Processes a single C file and returns violations.

    Args:
        filename: The C source file path.
        compile_args: Clang arguments.
        index: The Clang index object.
        ignore_callers: List of glob patterns for callers to ignore.
        ignore_callees: List of glob patterns for callees to ignore.

    Returns:
        List of Violations.
    """
    try:
        tu = index.parse(filename, args=compile_args)
    except clang.cindex.TranslationUnitLoadError:
        return [Violation(filename, 0, 0, "Failed to parse TranslationUnit")]

    parent_map = {}
    build_parent_map(tu.cursor, parent_map)

    violations = []

    def visit(node: Cursor, current_caller: Optional[str] = None):
        if node.kind == CursorKind.FUNCTION_DECL:
            current_caller = node.spelling
            if is_ignored(current_caller, ignore_callers):
                return

        if node.kind == CursorKind.CALL_EXPR:
            if node.location.file and node.location.file.name == filename:
                if not is_ignored(node.spelling, ignore_callees):
                    violations.extend(analyze_call(node, parent_map))

        for child in node.get_children():
            visit(child, current_caller)

    visit(tu.cursor)
    return violations


def setup_libclang(libclang_path: Optional[str]) -> None:
    """Sets up libclang library path.

    Args:
         libclang_path: Explicit path or None to search.
    """
    if libclang_path:
        clang.cindex.Config.set_library_file(libclang_path)
    else:
        try:
            clang.cindex.Config().get_cindex_library()
        except clang.cindex.LibclangError:
            search_paths = [
                "/usr/lib/llvm-*/lib/libclang-[0-9]*.so*",
                "/usr/lib/llvm-*/lib/libclang.so*",
                "/usr/lib/x86_64-linux-gnu/libclang-[0-9]*.so*",
                "/usr/lib/x86_64-linux-gnu/libclang.so*",
                "/usr/local/lib/libclang.so*",
                "/usr/lib/libclang.so*",
            ]
            found = False
            for pattern in search_paths:
                matches = glob.glob(pattern)
                for match in matches:
                    if "libclang-cpp" not in match:
                        clang.cindex.Config.set_library_file(match)
                        found = True
                        break
                if found:
                    break


def find_c_files(paths: List[str]) -> List[str]:
    """Finds all .c files in a list of paths, searching directories recursively.

    Args:
        paths: A list of file or directory paths.

    Returns:
        A sorted list of .c file paths.
    """
    c_files = set()
    for p_str in paths:
        p = Path(p_str)
        if p.is_file() and p.suffix == ".c":
            c_files.add(str(p))
        elif p.is_dir():
            for f in p.rglob("*.c"):
                c_files.add(str(f))
    return sorted(list(c_files))


def print_violations(violations: List[Violation], fmt: str) -> None:
    """Prints violations in the specified format.

    Args:
        violations: A list of Violations.
        fmt: The format to print ('text' or 'markdown').
    """
    if fmt == "text":
        for v in violations:
            print(
                f"{v.filename}:{v.line}:{v.column}: [{v.symbol}] {v.message}",
                file=sys.stderr,
            )
    elif fmt == "markdown":
        grouped = {}
        for v in violations:
            grouped.setdefault(v.filename, {}).setdefault(v.symbol, []).append(v)

        for filename in sorted(grouped.keys()):
            print(f"## `{filename}`")
            for symbol in sorted(grouped[filename].keys()):
                print(f"- [ ] `{symbol}`")
                for v in grouped[filename][symbol]:
                    print(f"  - Line {v.line}: {v.message}")
            print("")


def main() -> int:
    """Main execution entry point.

    Returns:
        0 for success, 1 for errors.
    """
    parser = argparse.ArgumentParser(description="Strict Error Percolation Check")
    parser.add_argument("filenames", nargs="*", help="C files or directories to check")
    parser.add_argument("--libclang-path", help="Path to libclang.so")
    parser.add_argument(
        "--ignore-callers",
        nargs="*",
        default=DEFAULT_IGNORE_CALLERS,
        help="Glob patterns for callers to ignore",
    )
    parser.add_argument(
        "--ignore-callees",
        nargs="*",
        default=DEFAULT_IGNORE_CALLEES,
        help="Glob patterns for callees to ignore",
    )
    parser.add_argument(
        "--format", choices=["text", "markdown"], default="text", help="Output format"
    )
    parser.add_argument(
        "--compile-args", nargs=argparse.REMAINDER, help="Args for clang"
    )
    args = parser.parse_args()

    if not args.filenames:
        return 0

    c_files = find_c_files(args.filenames)
    if not c_files:
        return 0

    setup_libclang(args.libclang_path)

    compile_args = ["-x", "c"]
    if args.compile_args:
        compile_args.extend(
            args.compile_args[1:] if args.compile_args[0] == "--" else args.compile_args
        )

    index = clang.cindex.Index.create()
    all_violations: List[Violation] = []

    for filename in c_files:
        all_violations.extend(
            process_file(
                filename, compile_args, index, args.ignore_callers, args.ignore_callees
            )
        )

    if all_violations:
        print_violations(all_violations, args.format)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
