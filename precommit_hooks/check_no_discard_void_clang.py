#!/usr/bin/env python3

"""Pre-commit hook to detect (void) casts bypassing no_discard on error enums using libclang.

This script enforces error enum usage, checking, and percolation by finding
and reporting usages of (void) casts used to silence no_discard compiler warnings
or ignore error enums and nodiscard returns.
"""

import sys
import os
import argparse
import glob
import fnmatch
from pathlib import Path
from typing import List, Optional

import clang.cindex
from clang.cindex import (
    Cursor,
    CursorKind,
    TypeKind,
    CompilationDatabase,
    CompilationDatabaseError,
)

DEFAULT_IGNORE_CALLERS: List[str] = ["test_*", "TEST*", "main"]
"""List of glob patterns for callers ignored by default."""

DEFAULT_IGNORE_CALLEES: List[str] = ["*_free", "*_destroy", "printf"]
"""List of glob patterns for callees ignored by default."""


def is_ignored(name: Optional[str], patterns: List[str]) -> bool:
    """Checks if a name matches any of the glob patterns.

    Args:
        name: The name to check.
        patterns: A list of glob patterns.

    Returns:
        True if the name matches any pattern, False otherwise.
    """
    if not name:
        return False
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


class Violation:
    """Represents a rule violation where a (void) cast discards an error enum or nodiscard return."""

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
            line: The line number where violation occurred.
            column: The column number where violation occurred.
            message: The description of the violation.
            symbol: The name of the function/scope where violation occurred.
        """
        self.filename = filename
        self.line = line
        self.column = column
        self.message = message
        self.symbol = symbol


def get_underlying_type(cursor_type: clang.cindex.Type) -> clang.cindex.Type:
    """Resolves typedefs and elaborated types down to their base type.

    Args:
        cursor_type: The Clang type to resolve.

    Returns:
        The underlying canonical type.
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
    """Checks if a given type evaluates to an enum or typedef resolving to an enum.

    Args:
        cursor_type: The type to evaluate.

    Returns:
        True if the underlying type is an enum, False otherwise.
    """
    return get_underlying_type(cursor_type).kind == TypeKind.ENUM


def is_void_type(cursor_type: clang.cindex.Type) -> bool:
    """Checks if a given type is void.

    Args:
        cursor_type: The type to evaluate.

    Returns:
        True if the type is void, False otherwise.
    """
    return (
        get_underlying_type(cursor_type).kind == TypeKind.VOID
        or cursor_type.kind == TypeKind.VOID
        or cursor_type.spelling == "void"
    )


def has_nodiscard_attr(decl: Optional[Cursor]) -> bool:
    """Checks if a declaration or its type has a nodiscard or warn_unused_result attribute.

    Args:
        decl: The declaration cursor to check.

    Returns:
        True if marked with nodiscard / warn_unused_result, False otherwise.
    """
    if not decl:
        return False
    for child in decl.get_children():
        if child.kind == CursorKind.WARN_UNUSED_RESULT_ATTR:
            return True
    try:
        types_to_check = [decl.type]
        if hasattr(decl, "result_type"):
            types_to_check.append(decl.result_type)
        for t in types_to_check:
            t_decl = t.get_declaration()
            if t_decl and t_decl != decl:
                for child in t_decl.walk_preorder():
                    if child.kind == CursorKind.WARN_UNUSED_RESULT_ATTR:
                        return True
    except Exception:
        pass
    return False


def get_call_return_type(call_cursor: Cursor) -> clang.cindex.Type:
    """Retrieves the return type of a function call cursor.

    Args:
        call_cursor: The CALL_EXPR cursor.

    Returns:
        The Clang type representing the return type of the call.
    """
    ret_type = call_cursor.type
    if ret_type.kind == TypeKind.INVALID:
        try:
            ret_type = call_cursor.type.get_result()
        except Exception:
            pass
    if ret_type.kind == TypeKind.INVALID and call_cursor.referenced:
        try:
            ret_type = call_cursor.referenced.result_type
        except Exception:
            pass
    return ret_type


def inspect_operand(expr: Cursor, ignore_callees: List[str]) -> Optional[str]:
    """Inspects the operand of a void cast to determine if it discards an error enum or nodiscard result.

    Args:
        expr: The operand AST cursor inside the void cast.
        ignore_callees: List of glob patterns for callees to ignore.

    Returns:
        An error message if the cast discards an error enum or nodiscard value, None otherwise.
    """
    if expr.kind == CursorKind.PAREN_EXPR:
        for child in expr.get_children():
            msg = inspect_operand(child, ignore_callees)
            if msg:
                return msg
        return None

    if expr.kind == CursorKind.UNEXPOSED_EXPR:
        children = list(expr.get_children())
        for child in children:
            msg = inspect_operand(child, ignore_callees)
            if msg:
                return msg
        if is_enum_type(expr.type):
            return f"(void) cast used to discard error enum expression of type '{expr.type.spelling}'"
        return None

    if expr.kind in (
        CursorKind.CSTYLE_CAST_EXPR,
        CursorKind.CXX_STATIC_CAST_EXPR,
        CursorKind.CXX_FUNCTIONAL_CAST_EXPR,
    ):
        return None

    if expr.kind == CursorKind.CALL_EXPR:
        callee_name = expr.spelling
        if callee_name and is_ignored(callee_name, ignore_callees):
            return None
        ret_type = get_call_return_type(expr)
        decl = expr.referenced or expr.get_definition()
        is_nodiscard = has_nodiscard_attr(decl)
        if is_enum_type(ret_type):
            name_str = f" from function '{callee_name}'" if callee_name else ""
            return f"(void) cast used to discard error enum return value{name_str}"
        elif is_nodiscard:
            name_str = f" from function '{callee_name}'" if callee_name else ""
            return f"(void) cast used to discard no_discard return value{name_str}"
        return None

    if expr.kind == CursorKind.DECL_REF_EXPR:
        ref = expr.referenced
        if ref and ref.kind == CursorKind.ENUM_CONSTANT_DECL:
            return None
        if is_enum_type(expr.type):
            kind_str = (
                "parameter" if ref and ref.kind == CursorKind.PARM_DECL else "variable"
            )
            var_name = expr.spelling or "<unnamed>"
            return f"(void) cast used to discard error enum {kind_str} '{var_name}'"
        return None

    if expr.kind == CursorKind.BINARY_OPERATOR:
        children = list(expr.get_children())
        for child in reversed(children):
            msg = inspect_operand(child, ignore_callees)
            if msg:
                return msg
        if is_enum_type(expr.type):
            return f"(void) cast used to discard error enum expression of type '{expr.type.spelling}'"
        return None

    if expr.kind == CursorKind.CONDITIONAL_OPERATOR:
        for child in expr.get_children():
            msg = inspect_operand(child, ignore_callees)
            if msg:
                return msg
        if is_enum_type(expr.type):
            return f"(void) cast used to discard error enum expression of type '{expr.type.spelling}'"
        return None

    if expr.kind in (
        CursorKind.MEMBER_REF_EXPR,
        CursorKind.ARRAY_SUBSCRIPT_EXPR,
        CursorKind.UNARY_OPERATOR,
    ):
        if is_enum_type(expr.type):
            return f"(void) cast used to discard error enum expression of type '{expr.type.spelling}'"
        for child in expr.get_children():
            msg = inspect_operand(child, ignore_callees)
            if msg:
                return msg
        return None

    if is_enum_type(expr.type):
        return f"(void) cast used to discard error enum expression of type '{expr.type.spelling}'"

    return None


def process_file(
    filename: str,
    compile_args: List[str],
    index: clang.cindex.Index,
    ignore_callers: List[str],
    ignore_callees: List[str],
    comp_db: Optional[CompilationDatabase] = None,
) -> List[Violation]:
    """Processes a single C file and returns violations.

    Args:
        filename: The C source file path.
        compile_args: Clang arguments.
        index: The Clang index object.
        ignore_callers: List of glob patterns for callers to ignore.
        ignore_callees: List of glob patterns for callees to ignore.
        comp_db: Optional Clang compilation database.

    Returns:
        List of Violations found in the file.
    """
    args_to_use = list(compile_args)
    if comp_db:
        cmds = comp_db.getCompileCommands(os.path.abspath(filename))
        if not cmds:
            cmds = comp_db.getCompileCommands(filename)
        if cmds:
            for cmd in cmds:
                raw_args = list(cmd.arguments)[1:]
                filtered_args = []
                skip_next = False
                for arg in raw_args:
                    if skip_next:
                        skip_next = False
                        continue
                    if arg == "-o":
                        skip_next = True
                        continue
                    if (
                        arg == "-c"
                        or arg == os.path.abspath(filename)
                        or arg == filename
                    ):
                        continue
                    filtered_args.append(arg)
                args_to_use = filtered_args
                break

    try:
        tu = index.parse(filename, args=args_to_use)
    except clang.cindex.TranslationUnitLoadError:
        return [Violation(filename, 0, 0, "Failed to parse TranslationUnit")]

    if tu is None:
        return [Violation(filename, 0, 0, "Failed to parse TranslationUnit")]

    violations: List[Violation] = []
    target_abs = os.path.abspath(filename)

    def visit(node: Cursor, current_caller: Optional[str] = None) -> None:
        """Recursively visits AST nodes checking for disallowed void casts.

        Args:
            node: The current AST cursor.
            current_caller: The name of the enclosing function declaration, if any.
        """
        if node.kind == CursorKind.FUNCTION_DECL:
            current_caller = node.spelling
            if is_ignored(current_caller, ignore_callers):
                return

        if node.kind in (
            CursorKind.CSTYLE_CAST_EXPR,
            CursorKind.CXX_STATIC_CAST_EXPR,
            CursorKind.CXX_FUNCTIONAL_CAST_EXPR,
        ):
            node_file = getattr(node.location, "file", None)
            if node_file and (
                node_file.name == filename
                or os.path.abspath(node_file.name) == target_abs
            ):
                if is_void_type(node.type):
                    operands = [
                        c for c in node.get_children() if c.kind != CursorKind.TYPE_REF
                    ]
                    if not operands:
                        operands = list(node.get_children())
                    if operands:
                        msg = inspect_operand(operands[0], ignore_callees)
                        if msg:
                            violations.append(
                                Violation(
                                    filename,
                                    node.location.line,
                                    node.location.column,
                                    msg,
                                    current_caller or "<global>",
                                )
                            )

        for child in node.get_children():
            visit(child, current_caller)

    visit(tu.cursor)
    return violations


def setup_libclang(libclang_path: Optional[str]) -> None:
    """Sets up libclang library path.

    Args:
        libclang_path: Explicit path or None to search default paths.
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


def find_c_files(
    paths: List[str], exclude_patterns: Optional[List[str]] = None
) -> List[str]:
    """Finds all .c files in a list of paths, searching directories recursively.

    Args:
        paths: A list of file or directory paths.
        exclude_patterns: Optional list of glob patterns to exclude.

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

    if exclude_patterns:
        filtered = set()
        for f in c_files:
            if not any(
                fnmatch.fnmatch(f, pat) or fnmatch.fnmatch(os.path.basename(f), pat)
                for pat in exclude_patterns
            ):
                filtered.add(f)
        c_files = filtered

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
        grouped: dict = {}
        for v in violations:
            grouped.setdefault(v.filename, {}).setdefault(v.symbol, []).append(v)

        for filename in sorted(grouped.keys()):
            print(f"## `{filename}`")
            for symbol in sorted(grouped[filename].keys()):
                print(f"- [ ] `{symbol}`")
                for v in grouped[filename][symbol]:
                    print(f"  - Line {v.line}: {v.message}")
            print("")


def main(argv: Optional[List[str]] = None) -> int:
    """Main execution entry point.

    Args:
        argv: Optional command-line argument list. If None, uses sys.argv[1:].

    Returns:
        0 for success, 1 for errors.
    """
    if argv is None:
        argv = sys.argv[1:]

    extra_compile_args: List[str] = []
    if "--compile-args" in argv:
        idx = argv.index("--compile-args")
        extra_compile_args = argv[idx + 1 :]
        argv = argv[:idx]
    elif "--" in argv:
        idx = argv.index("--")
        extra_compile_args = argv[idx + 1 :]
        argv = argv[:idx]

    if extra_compile_args and extra_compile_args[0] == "--":
        extra_compile_args = extra_compile_args[1:]

    parser = argparse.ArgumentParser(
        description="Check for (void) casts bypassing no_discard or error enums"
    )
    parser.add_argument("filenames", nargs="*", help="C files or directories to check")
    parser.add_argument("--libclang-path", help="Path to libclang library file")
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
        "--no-default-exceptions",
        action="store_true",
        help="Do not use default ignore patterns for callers and callees",
    )
    parser.add_argument(
        "--exclude-files",
        action="append",
        help="Glob pattern to exclude files (can be specified multiple times)",
    )
    parser.add_argument(
        "--format", choices=["text", "markdown"], default="text", help="Output format"
    )
    parser.add_argument(
        "--build-dir",
        help="Path to directory containing compile_commands.json",
    )
    args = parser.parse_args(argv)

    if not args.filenames:
        return 0

    c_files = find_c_files(args.filenames, args.exclude_files)
    if not c_files:
        return 0

    setup_libclang(args.libclang_path)

    comp_db = None
    if args.build_dir:
        try:
            comp_db = CompilationDatabase.fromDirectory(args.build_dir)
        except CompilationDatabaseError as e:
            print(
                f"Error: Could not load compilation database from '{args.build_dir}'.",
                file=sys.stderr,
            )
            print(f"Underlying error: {e}", file=sys.stderr)
            return 1

    compile_args = ["-x", "c"]
    if extra_compile_args:
        compile_args.extend(
            extra_compile_args[1:]
            if extra_compile_args[0] == "--"
            else extra_compile_args
        )

    ignore_callers = [] if args.no_default_exceptions else list(args.ignore_callers)
    ignore_callees = [] if args.no_default_exceptions else list(args.ignore_callees)

    index = clang.cindex.Index.create()
    all_violations: List[Violation] = []

    for filename in c_files:
        all_violations.extend(
            process_file(
                filename,
                compile_args,
                index,
                ignore_callers,
                ignore_callees,
                comp_db=comp_db,
            )
        )

    if all_violations:
        print_violations(all_violations, args.format)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
