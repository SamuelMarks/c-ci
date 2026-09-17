"""Tests for the check_no_discard_void_clang hook."""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock
import pytest
import clang.cindex

from check_no_discard_void_clang import (
    Violation,
    setup_libclang,
    process_file,
    main,
    is_ignored,
    get_underlying_type,
    is_enum_type,
    is_void_type,
    has_nodiscard_attr,
    get_call_return_type,
    inspect_operand,
    find_c_files,
    print_violations,
)

setup_libclang(None)
INDEX = clang.cindex.Index.create()


def parse_code(
    code: str, args: list = None
) -> tuple[clang.cindex.TranslationUnit, str]:
    """Helper to write C code to a temporary file and parse it into a TranslationUnit.

    Args:
        code: C source code string.
        args: Optional compiler arguments for Clang.

    Returns:
        Tuple of (TranslationUnit, file_path).
    """
    fd, path = tempfile.mkstemp(suffix=".c")
    with os.fdopen(fd, "w") as f:
        f.write(code)
    compile_args = ["-x", "c"] if args is None else args
    tu = INDEX.parse(path, args=compile_args)
    return tu, path


def test_violation_init():
    """Test Violation class initialization and fields."""
    v = Violation("sample.c", 12, 4, "Violation message", "my_func")
    assert v.filename == "sample.c"
    assert v.line == 12
    assert v.column == 4
    assert v.message == "Violation message"
    assert v.symbol == "my_func"


def test_is_ignored():
    """Test is_ignored helper with patterns and None name."""
    assert not is_ignored(None, ["test_*"])
    assert not is_ignored("", ["test_*"])
    assert is_ignored("test_func", ["test_*", "main"])
    assert is_ignored("main", ["test_*", "main"])
    assert not is_ignored("normal_func", ["test_*", "main"])


def test_get_underlying_type_and_is_enum():
    """Test get_underlying_type with typedefs, elaborated types, and primitives."""
    code = """
    typedef enum { OK = 0, ERR = 1 } base_err_t;
    typedef base_err_t my_err_t;
    typedef int my_int_t;
    """
    tu, path = parse_code(code)
    os.unlink(path)

    types_found = {}
    for node in tu.cursor.walk_preorder():
        if node.kind == clang.cindex.CursorKind.TYPEDEF_DECL:
            types_found[node.spelling] = node.underlying_typedef_type

    assert is_enum_type(types_found["my_err_t"])
    assert not is_enum_type(types_found["my_int_t"])


def test_is_void_type():
    """Test is_void_type helper."""
    code = """
    typedef void my_void_t;
    void f1(void);
    int f2(void);
    """
    tu, path = parse_code(code)
    os.unlink(path)

    for node in tu.cursor.walk_preorder():
        if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            if node.spelling == "f1":
                assert is_void_type(node.result_type)
            elif node.spelling == "f2":
                assert not is_void_type(node.result_type)


def test_void_cast_function_call_returning_enum():
    """Test detecting (void) cast of a function call returning an enum."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    void test_func(void) {
        (void)foo();
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 1
    assert (
        "discard error enum return value from function 'foo'" in violations[0].message
    )
    assert violations[0].symbol == "test_func"


def test_void_cast_parenthesized_call():
    """Test detecting (void) cast of a parenthesized call returning an enum."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    void test_func(void) {
        (void)(foo());
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 1
    assert (
        "discard error enum return value from function 'foo'" in violations[0].message
    )


def test_void_cast_enum_variable():
    """Test detecting (void) cast of a local variable of enum type."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    void test_func(void) {
        enum Result rc = foo();
        (void)rc;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 1
    assert "discard error enum variable 'rc'" in violations[0].message


def test_void_cast_enum_parameter():
    """Test detecting (void) cast of a parameter of enum type."""
    code = """
    enum Result { OK, ERR };
    void test_func(enum Result err) {
        (void)err;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 1
    assert "discard error enum parameter 'err'" in violations[0].message


def test_void_cast_enum_constant_allowed():
    """Test that (void) on an enum constant literal is not flagged as a variable/return."""
    code = """
    enum Result { OK, ERR };
    void test_func(void) {
        (void)OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 0


def test_void_cast_non_enum_allowed():
    """Test that (void) casts on non-enum values (int, string, 0, printf) are allowed."""
    code = """
    #include <stdio.h>
    int get_code(void);
    void test_func(int arg) {
        (void)arg;
        (void)get_code();
        (void)0;
        (void)printf("test
");
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 0


def test_void_cast_nodiscard_int_function():
    """Test detecting (void) cast of a non-enum function with warn_unused_result attribute."""
    code = """
    #define NO_DISCARD __attribute__((warn_unused_result))
    NO_DISCARD int init_system(void);
    void test_func(void) {
        (void)init_system();
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 1
    assert (
        "discard no_discard return value from function 'init_system'"
        in violations[0].message
    )


def test_void_cast_assignment_expression():
    """Test detecting (void) cast of an assignment expression yielding an error enum."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    void test_func(void) {
        enum Result rc;
        (void)(rc = foo());
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 1
    assert "from function 'foo'" in violations[0].message


def test_void_cast_conditional_expression():
    """Test detecting (void) cast of a ternary conditional expression with error enums."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    extern enum Result bar(void);
    void test_func(int cond) {
        (void)(cond ? foo() : bar());
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 1
    assert "discard error enum return value" in violations[0].message


def test_void_cast_comma_expression():
    """Test detecting (void) cast of a comma expression involving error enums."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    void test_func(int x) {
        (void)(x, foo());
        (void)(foo(), 0);
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 2


def test_void_cast_member_and_array_and_pointer():
    """Test detecting (void) cast of struct member, array element, and pointer dereference."""
    code = """
    typedef enum { OK, ERR } error_t;
    struct Node { error_t status; };
    void test_func(struct Node *n, error_t *ptr, error_t arr[]) {
        (void)n->status;
        (void)*ptr;
        (void)arr[0];
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 3


def test_ignored_caller():
    """Test that ignored callers (e.g. test_* or main) are not flagged."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    void test_my_function(void) {
        (void)foo();
    }
    int main(void) {
        (void)foo();
        return 0;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, ["test_*", "main"], [])
    os.unlink(path)

    assert len(violations) == 0


def test_ignored_callee():
    """Test that ignored callees (e.g. *_free, *_destroy) are not flagged."""
    code = """
    enum Result { OK, ERR };
    extern enum Result buffer_free(void);
    void cleanup(void) {
        (void)buffer_free();
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], ["*_free"])
    os.unlink(path)

    assert len(violations) == 0


def test_cxx_static_cast_void():
    """Test detecting C++ static_cast<void>(...) on error enums."""
    code = """
    enum class Error { OK, FAIL };
    Error get_error();
    void test_func(Error e) {
        static_cast<void>(get_error());
        static_cast<void>(e);
    }
    """
    tu, path = parse_code(code, args=["-x", "c++"])
    violations = process_file(path, ["-x", "c++"], INDEX, [], [])
    os.unlink(path)

    assert len(violations) == 2


def test_process_file_load_error():
    """Test process_file when translation unit fails to load."""
    violations = process_file("nonexistent_file_xyz.c", ["-x", "c"], INDEX, [], [])
    assert len(violations) == 1
    assert "Failed to parse TranslationUnit" in violations[0].message


def test_process_file_tu_none():
    """Test process_file when index.parse returns None."""
    mock_index = mock.Mock()
    mock_index.parse.return_value = None
    violations = process_file("dummy.c", ["-x", "c"], mock_index, [], [])
    assert len(violations) == 1
    assert "Failed to parse TranslationUnit" in violations[0].message


def test_process_file_comp_db(tmp_path):
    """Test process_file with a mock CompilationDatabase.

    Args:
        tmp_path: Pytest temporary directory fixture.
    """
    src = tmp_path / "sample.c"
    src.write_text("enum E { A }; enum E f(void); void t(void) { (void)f(); }")

    mock_db = mock.Mock()
    mock_cmd = mock.Mock()
    mock_cmd.arguments = ["clang", "-o", "sample.o", "-c", str(src), "-I/extra/include"]
    mock_db.getCompileCommands.return_value = [mock_cmd]

    violations = process_file(str(src), ["-x", "c"], INDEX, [], [], comp_db=mock_db)
    assert len(violations) == 1


def test_find_c_files(tmp_path):
    """Test find_c_files directory expansion and file filtering.

    Args:
        tmp_path: Pytest temporary directory fixture.
    """
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    f1 = src_dir / "a.c"
    f1.write_text("int main(){}")
    f2 = src_dir / "b.h"
    f2.write_text("")
    f3 = src_dir / "ignored.c"
    f3.write_text("int foo(){}")

    files = find_c_files([str(src_dir)], exclude_patterns=["*ignored*"])
    assert len(files) == 1
    assert "a.c" in files[0]

    single_file = find_c_files([str(f1)])
    assert single_file == [str(f1)]


def test_print_violations_text(capsys):
    """Test print_violations in text format.

    Args:
        capsys: Pytest capture stdout/stderr fixture.
    """
    v = Violation("src/file.c", 10, 5, "Disallowed void cast", "run")
    print_violations([v], "text")
    captured = capsys.readouterr()
    assert "src/file.c:10:5: [run] Disallowed void cast" in captured.err


def test_print_violations_markdown(capsys):
    """Test print_violations in markdown format.

    Args:
        capsys: Pytest capture stdout/stderr fixture.
    """
    v = Violation("src/file.c", 10, 5, "Disallowed void cast", "run")
    print_violations([v], "markdown")
    captured = capsys.readouterr()
    assert "## `src/file.c`" in captured.out
    assert "- [ ] `run`" in captured.out
    assert "- Line 10: Disallowed void cast" in captured.out


def test_setup_libclang():
    """Test setup_libclang with explicit path and fallbacks."""
    with mock.patch("clang.cindex.Config.set_library_file") as mock_set:
        setup_libclang("/custom/libclang.so")
        mock_set.assert_called_once_with("/custom/libclang.so")

    with mock.patch(
        "clang.cindex.Config.get_cindex_library",
        side_effect=clang.cindex.LibclangError("err"),
    ):
        with mock.patch("glob.glob", return_value=["/usr/lib/libclang.so"]):
            with mock.patch("clang.cindex.Config.set_library_file") as mock_set:
                setup_libclang(None)
                mock_set.assert_called_with("/usr/lib/libclang.so")

    # When glob returns libclang-cpp, it should not set it
    with mock.patch(
        "clang.cindex.Config.get_cindex_library",
        side_effect=clang.cindex.LibclangError("err"),
    ):
        with mock.patch("glob.glob", return_value=["/usr/lib/libclang-cpp.so"]):
            with mock.patch("clang.cindex.Config.set_library_file") as mock_set:
                setup_libclang(None)
                mock_set.assert_not_called()


def test_main_no_args():
    """Test main with no arguments returns 0."""
    assert main([]) == 0


def test_main_no_c_files(tmp_path):
    """Test main when no C files match returns 0.

    Args:
        tmp_path: Pytest temporary directory fixture.
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert main([str(empty_dir)]) == 0


def test_main_build_dir_error(tmp_path):
    """Test main when build-dir cannot load compilation database.

    Args:
        tmp_path: Pytest temporary directory fixture.
    """
    f = tmp_path / "test.c"
    f.write_text("int x;")
    with mock.patch(
        "clang.cindex.CompilationDatabase.fromDirectory",
        side_effect=clang.cindex.CompilationDatabaseError(1, "error"),
    ):
        ret = main([str(f), "--build-dir", "/invalid/dir"])
        assert ret == 1


def test_main_success_and_violations(tmp_path):
    """Test main returns 0 on success and 1 on violations.

    Args:
        tmp_path: Pytest temporary directory fixture.
    """
    clean_file = tmp_path / "clean.c"
    clean_file.write_text("int main(void) { return 0; }")
    assert main([str(clean_file), "--compile-args", "--", "-I."]) == 0

    bad_file = tmp_path / "bad.c"
    bad_file.write_text("enum E { A }; enum E f(void); void bad(void) { (void)f(); }")
    assert main([str(bad_file)]) == 1

    # Markdown format
    assert main([str(bad_file), "--format", "markdown", "--no-default-exceptions"]) == 1


def test_main_runpy():
    """Test script execution via __main__."""
    import runpy

    with mock.patch("sys.argv", ["script"]):
        with mock.patch("sys.exit") as mock_exit:
            runpy.run_path(
                "precommit_hooks/check_no_discard_void_clang.py", run_name="__main__"
            )
            mock_exit.assert_called_with(0)


def test_has_nodiscard_attr_type_decl():
    """Test has_nodiscard_attr when attribute is attached to type declaration."""
    code = """
    #define NO_DISCARD __attribute__((warn_unused_result))
    typedef enum NO_DISCARD { OK, ERR } status_t;
    status_t foo(void);
    """
    tu, path = parse_code(code)
    os.unlink(path)

    for node in tu.cursor.walk_preorder():
        if (
            node.kind == clang.cindex.CursorKind.FUNCTION_DECL
            and node.spelling == "foo"
        ):
            assert has_nodiscard_attr(node)
            break


def test_has_nodiscard_attr_none():
    """Test has_nodiscard_attr with None cursor."""
    assert not has_nodiscard_attr(None)


def test_get_call_return_type_fallback():
    """Test get_call_return_type fallback when call.type is invalid."""
    mock_call = mock.Mock()
    mock_type = mock.Mock()
    mock_type.kind = clang.cindex.TypeKind.INVALID
    mock_type.get_result.side_effect = Exception("err")
    mock_call.type = mock_type

    mock_ref = mock.Mock()
    mock_res = mock.Mock()
    mock_res.kind = clang.cindex.TypeKind.INT
    mock_ref.result_type = mock_res
    mock_call.referenced = mock_ref

    res = get_call_return_type(mock_call)
    assert res.kind == clang.cindex.TypeKind.INT


def test_inspect_operand_unnamed_and_fallbacks():
    """Test inspect_operand with empty children, fallback types, and unnamed symbols."""
    mock_unexposed = mock.Mock()
    mock_unexposed.kind = clang.cindex.CursorKind.UNEXPOSED_EXPR
    mock_unexposed.get_children.return_value = []
    mock_type = mock.Mock()
    mock_type.kind = clang.cindex.TypeKind.ENUM
    mock_type.spelling = "enum Error"
    mock_unexposed.type = mock_type

    msg = inspect_operand(mock_unexposed, [])
    assert msg is not None
    assert "discard error enum expression of type 'enum Error'" in msg

    # Fallback cursor
    mock_other = mock.Mock()
    mock_other.kind = clang.cindex.CursorKind.UNEXPOSED_ATTR
    mock_other.type = mock_type
    msg2 = inspect_operand(mock_other, [])
    assert msg2 is not None
    assert "discard error enum expression of type 'enum Error'" in msg2

    # Call expr without callee_name
    mock_call = mock.Mock()
    mock_call.kind = clang.cindex.CursorKind.CALL_EXPR
    mock_call.spelling = ""
    mock_call.type = mock_type
    mock_call.referenced = None
    mock_call.get_definition.return_value = None
    msg3 = inspect_operand(mock_call, [])
    assert msg3 is not None
    assert "(void) cast used to discard error enum return value" in msg3

    # Nodiscard call without callee_name
    mock_int_type = mock.Mock()
    mock_int_type.kind = clang.cindex.TypeKind.INT
    mock_call.type = mock_int_type
    mock_decl = mock.Mock()
    mock_attr = mock.Mock()
    mock_attr.kind = clang.cindex.CursorKind.WARN_UNUSED_RESULT_ATTR
    mock_decl.get_children.return_value = [mock_attr]
    mock_decl.type = mock_int_type
    mock_call.referenced = mock_decl
    msg4 = inspect_operand(mock_call, [])
    assert msg4 is not None
    assert "(void) cast used to discard no_discard return value" in msg4


def test_get_underlying_type_invalid_breaks():
    """Test get_underlying_type breaks when underlying type is invalid."""
    mock_type1 = mock.Mock()
    mock_type1.kind = clang.cindex.TypeKind.TYPEDEF
    mock_decl1 = mock.Mock()
    mock_underlying1 = mock.Mock()
    mock_underlying1.kind = clang.cindex.TypeKind.INVALID
    mock_decl1.underlying_typedef_type = mock_underlying1
    mock_type1.get_declaration.return_value = mock_decl1
    assert get_underlying_type(mock_type1) == mock_type1

    mock_type2 = mock.Mock()
    mock_type2.kind = clang.cindex.TypeKind.ELABORATED
    mock_underlying2 = mock.Mock()
    mock_underlying2.kind = clang.cindex.TypeKind.INVALID
    mock_type2.get_named_type.return_value = mock_underlying2
    assert get_underlying_type(mock_type2) == mock_type2


def test_has_nodiscard_attr_exception():
    """Test has_nodiscard_attr handles exceptions gracefully."""
    mock_decl = mock.Mock()
    mock_decl.get_children.return_value = []
    mock_type = mock.Mock()
    mock_type.get_declaration.side_effect = Exception("err")
    mock_decl.type = mock_type
    assert not has_nodiscard_attr(mock_decl)


def test_get_call_return_type_referenced_exception():
    """Test get_call_return_type handles exception accessing referenced.result_type."""
    mock_call = mock.Mock()
    mock_type = mock.Mock()
    mock_type.kind = clang.cindex.TypeKind.INVALID
    mock_type.get_result.side_effect = Exception("err")
    mock_call.type = mock_type

    mock_ref = mock.Mock()
    type(mock_ref).result_type = mock.PropertyMock(side_effect=Exception("err"))
    mock_call.referenced = mock_ref

    res = get_call_return_type(mock_call)
    assert res.kind == clang.cindex.TypeKind.INVALID


def test_inspect_operand_nested_cast_and_none_branches():
    """Test inspect_operand with nested cast, paren returning none, and operators returning none."""
    # Nested cast
    mock_nested_cast = mock.Mock()
    mock_nested_cast.kind = clang.cindex.CursorKind.CSTYLE_CAST_EXPR
    assert inspect_operand(mock_nested_cast, []) is None

    # Paren returning None
    code = """
    void test_func(int x) {
        (void)(x);
        (void)(x + 1);
        (void)(x ? 1 : 2);
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 0


def test_inspect_operand_operator_fallbacks():
    """Test binary, conditional, and member operators returning fallback enum messages."""
    mock_enum_type = mock.Mock()
    mock_enum_type.kind = clang.cindex.TypeKind.ENUM
    mock_enum_type.spelling = "enum Error"

    # Binary operator with no matching children but enum type
    mock_bin = mock.Mock()
    mock_bin.kind = clang.cindex.CursorKind.BINARY_OPERATOR
    mock_bin.get_children.return_value = []
    mock_bin.type = mock_enum_type
    msg_bin = inspect_operand(mock_bin, [])
    assert msg_bin is not None
    assert "discard error enum expression of type 'enum Error'" in msg_bin

    # Binary operator with non-enum type
    mock_int_type = mock.Mock()
    mock_int_type.kind = clang.cindex.TypeKind.INT
    mock_bin.type = mock_int_type
    assert inspect_operand(mock_bin, []) is None

    # Conditional operator with no matching children but enum type
    mock_cond = mock.Mock()
    mock_cond.kind = clang.cindex.CursorKind.CONDITIONAL_OPERATOR
    mock_cond.get_children.return_value = []
    mock_cond.type = mock_enum_type
    msg_cond = inspect_operand(mock_cond, [])
    assert msg_cond is not None
    assert "discard error enum expression of type 'enum Error'" in msg_cond

    # Conditional operator with non-enum type
    mock_cond.type = mock_int_type
    assert inspect_operand(mock_cond, []) is None

    # Member ref where child returns message
    mock_member = mock.Mock()
    mock_member.kind = clang.cindex.CursorKind.MEMBER_REF_EXPR
    mock_member.type = mock_int_type
    mock_child = mock.Mock()
    mock_child.kind = clang.cindex.CursorKind.UNEXPOSED_EXPR
    mock_child.get_children.return_value = []
    mock_child.type = mock_enum_type
    mock_member.get_children.return_value = [mock_child]
    msg_member = inspect_operand(mock_member, [])
    assert msg_member is not None
    assert "discard error enum expression of type 'enum Error'" in msg_member

    # Member ref where children return None
    mock_member.get_children.return_value = []
    assert inspect_operand(mock_member, []) is None


def test_process_file_comp_db_fallback():
    """Test process_file with comp_db where abspath returns empty but relative returns command."""
    mock_db = mock.Mock()
    mock_cmd = mock.Mock()
    mock_cmd.arguments = [
        "clang",
        "-o",
        "sample.o",
        "-c",
        "sample.c",
        "-I/usr/include",
    ]

    def get_cmds(p):
        """Mock command resolution function.

        Args:
            p: File path queried.

        Returns:
            List of mock commands if path matches sample.c, empty list otherwise.
        """
        if p == "sample.c":
            return [mock_cmd]
        return []

    mock_db.getCompileCommands.side_effect = get_cmds

    mock_index = mock.Mock()
    mock_tu = mock.Mock()
    mock_tu.cursor.get_children.return_value = []
    mock_tu.cursor.kind = clang.cindex.CursorKind.TRANSLATION_UNIT
    mock_index.parse.return_value = mock_tu

    violations = process_file(
        "sample.c", ["-x", "c"], mock_index, [], [], comp_db=mock_db
    )
    assert violations == []
    mock_index.parse.assert_called_with("sample.c", args=["-I/usr/include"])


def test_process_file_cast_only_type_ref():
    """Test process_file when cast node has only TYPE_REF child."""
    mock_index = mock.Mock()
    mock_tu = mock.Mock()
    mock_cast = mock.Mock()
    mock_cast.kind = clang.cindex.CursorKind.CSTYLE_CAST_EXPR
    mock_file = mock.Mock()
    mock_file.name = "f.c"
    mock_loc = mock.Mock()
    mock_loc.file = mock_file
    mock_loc.line = 1
    mock_loc.column = 1
    mock_cast.location = mock_loc
    mock_type = mock.Mock()
    mock_type.kind = clang.cindex.TypeKind.VOID
    mock_type.spelling = "void"
    mock_cast.type = mock_type

    mock_child = mock.Mock()
    mock_child.kind = clang.cindex.CursorKind.TYPE_REF
    mock_child.type = mock_type
    mock_child.get_children.return_value = []
    mock_cast.get_children.return_value = [mock_child]

    mock_tu.cursor.get_children.return_value = [mock_cast]
    mock_tu.cursor.kind = clang.cindex.CursorKind.TRANSLATION_UNIT
    mock_index.parse.return_value = mock_tu

    violations = process_file("f.c", ["-x", "c"], mock_index, [], [])
    assert len(violations) == 0


def test_main_double_dash_only(tmp_path):
    """Test main when only '--' is passed without '--compile-args'.

    Args:
        tmp_path: Pytest temporary directory fixture.
    """
    clean_file = tmp_path / "clean.c"
    clean_file.write_text("int main(void) { return 0; }")
    assert main([str(clean_file), "--", "-I."]) == 0
