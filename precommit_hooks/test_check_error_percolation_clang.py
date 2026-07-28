"""Tests for the error percolation hook."""

import os
import tempfile
from pathlib import Path
from unittest import mock
import pytest
import clang.cindex

from check_error_percolation_clang import (
    Violation,
    setup_libclang,
    process_file,
    main,
    is_enum_type,
    extract_variable_name,
)

# Basic setup to ensure we can load index for tests
setup_libclang(None)
INDEX = clang.cindex.Index.create()


def parse_code(code: str) -> tuple[clang.cindex.TranslationUnit, str]:
    """Helper to parse code string to TU."""
    fd, path = tempfile.mkstemp(suffix=".c")
    with os.fdopen(fd, "w") as f:
        f.write(code)
    tu = INDEX.parse(path, args=["-x", "c"])
    return tu, path


def test_violation_init():
    """Test Violation class initialization."""
    v = Violation("file.c", 10, 5, "msg", "my_func")
    assert v.filename == "file.c"
    assert v.line == 10
    assert v.column == 5
    assert v.message == "msg"
    assert v.symbol == "my_func"


def test_violation_symbol_tracking():
    """Test that violations track the function symbol."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result my_bad_function(void) {
        foo();
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert violations[0].symbol == "my_bad_function"


def test_find_c_files(tmp_path):
    """Test directory expansion."""
    d = tmp_path / "src"
    d.mkdir()
    f1 = d / "a.c"
    f1.write_text("int main(){}")
    f2 = d / "b.h"
    f2.write_text("")

    from check_error_percolation_clang import find_c_files

    files = find_c_files([str(d), "unknown_path.txt", str(f1)])
    assert len(files) == 1
    assert "a.c" in files[0]


def test_main_block():
    """Test __main__ block indirectly."""
    import runpy
    import sys

    # To run it as a script, we mock sys.argv and sys.exit
    with mock.patch("sys.argv", ["script"]):
        with mock.patch("sys.exit") as mock_exit:
            runpy.run_path(
                "precommit_hooks/check_error_percolation_clang.py", run_name="__main__"
            )
            mock_exit.assert_called_with(0)


def test_goto_cleanup_valid():
    """Test proper percolation using a goto cleanup block."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc = foo();
        if (rc != OK) {
            goto cleanup;
        }
        rc = OK;
    cleanup:
        return rc;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 0


def test_goto_cleanup_invalid_no_return():
    """Test goto cleanup where function does not return error variable."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc = foo();
        if (rc != OK) {
            goto cleanup;
        }
        rc = OK;
    cleanup:
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "not returned" in violations[0].message.lower()


def test_goto_cleanup_invalid_mutation():
    """Test goto cleanup where mutation happens before goto."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc = foo();
        if (rc != OK) {
            rc = ERR; /* invalid mutation before goto */
            goto cleanup;
        }
        rc = OK;
    cleanup:
        return rc;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "mutated before return" in violations[0].message.lower()


def test_main_no_args(monkeypatch):
    """Test main with no args."""
    monkeypatch.setattr("sys.argv", ["script"])
    assert main() == 0


@mock.patch("check_error_percolation_clang.find_c_files")
@mock.patch("check_error_percolation_clang.process_file")
def test_main_success(mock_process, mock_find, monkeypatch):
    """Test main success returns 0."""
    mock_find.return_value = ["f.c"]
    mock_process.return_value = []
    monkeypatch.setattr("sys.argv", ["script", "f.c", "--compile-args", "-I."])
    assert main() == 0


@mock.patch("check_error_percolation_clang.find_c_files")
@mock.patch("check_error_percolation_clang.process_file")
def test_main_violations_text(mock_process, mock_find, monkeypatch, capsys):
    """Test main with violations returns 1 in text format."""
    mock_find.return_value = ["f.c"]
    mock_process.return_value = [Violation("f.c", 1, 1, "err", "func")]
    monkeypatch.setattr("sys.argv", ["script", "f.c", "--format", "text"])
    assert main() == 1
    captured = capsys.readouterr()
    assert "f.c:1:1: [func] err" in captured.err


@mock.patch("check_error_percolation_clang.find_c_files")
@mock.patch("check_error_percolation_clang.process_file")
def test_main_violations_markdown(mock_process, mock_find, monkeypatch, capsys):
    """Test main with violations returns 1 in markdown format."""
    mock_find.return_value = ["f.c"]
    mock_process.return_value = [Violation("f.c", 1, 1, "err", "func")]
    monkeypatch.setattr("sys.argv", ["script", "f.c", "--format", "markdown"])
    assert main() == 1
    captured = capsys.readouterr()
    assert "## `f.c`" in captured.out
    assert "- [ ] `func`" in captured.out
    assert "- Line 1: err" in captured.out


def test_direct_return_valid():
    """Test direct return is allowed."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        return foo();
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 0


def test_discarded_return_invalid():
    """Test discarding return is flagged."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        foo();
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "discarded" in violations[0].message.lower()


def test_not_checked_invalid():
    """Test returning without if check."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc = foo();
        return rc;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "immediately checked" in violations[0].message.lower()


def test_proper_percolation_valid():
    """Test full proper percolation."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc = foo();
        if (rc != OK) {
            return rc;
        }
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 0


def test_mutation_invalid():
    """Test mutation before return."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc = foo();
        if (rc != OK) {
            rc = ERR;
            return rc;
        }
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "mutated before return" in violations[0].message.lower()


def test_missing_return_in_if():
    """Test not returning in the if block."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc = foo();
        if (rc != OK) {
            int x = 1;
        }
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "not returned" in violations[0].message.lower()


def test_inline_assignment_valid():
    """Test proper inline assignment percolation."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc;
        if ((rc = foo()) != OK) {
            return rc;
        }
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 0


def test_inline_assignment_invalid_mutation():
    """Test mutation inside inline assignment if block."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc;
        if ((rc = foo()) != OK) {
            rc = ERR;
            return rc;
        }
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "mutated before return" in violations[0].message.lower()


def test_inline_assignment_not_assigned():
    """Test inline call without assignment is flagged."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        if (foo() != OK) {
            return ERR;
        }
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "discarded or not assigned" in violations[0].message.lower()


def test_switch_statement_valid():
    """Test percolation through a switch statement."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc = foo();
        switch (rc) {
            case ERR: return rc;
            default: break;
        }
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 0


def test_switch_statement_invalid():
    """Test missing return inside switch."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result rc = foo();
        switch (rc) {
            case ERR: break;
            default: break;
        }
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "not returned" in violations[0].message.lower()


def test_macro_assertion_ignored():
    """Test that calls inside macros (like assert) are ignored."""
    code = """
    #define assert(x) if (!(x)) { __builtin_trap(); }
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        assert(foo() == OK);
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 0


def test_ignore_callers():
    """Test that ignored callers are skipped."""
    from check_error_percolation_clang import is_ignored

    assert is_ignored(None, ["test*"]) is False

    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result test_bar(void) {
        foo(); /* normally invalid discarded return */
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, ["test_*"], [])
    os.unlink(path)
    assert len(violations) == 0


def test_ignore_callees():
    """Test that ignored callees are skipped."""
    code = """
    enum Result { OK, ERR };
    extern enum Result my_free(void);
    enum Result bar(void) {
        my_free(); /* normally invalid discarded return */
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], ["*_free"])
    os.unlink(path)
    assert len(violations) == 0


def test_invalid_type_resolution():
    """Test resolution of invalid underlying types."""
    from check_error_percolation_clang import get_underlying_type

    # Just mock a clang type that returns INVALID
    class MockTypeInvalid:
        @property
        def kind(self):
            return clang.cindex.TypeKind.INVALID

    class MockDecl:
        @property
        def underlying_typedef_type(self):
            return MockTypeInvalid()

    class MockTypeTypedef:
        @property
        def kind(self):
            return clang.cindex.TypeKind.TYPEDEF

        def get_declaration(self):
            return MockDecl()

    class MockTypeValid:
        @property
        def kind(self):
            return clang.cindex.TypeKind.ENUM

    class MockDeclValid:
        @property
        def underlying_typedef_type(self):
            return MockTypeValid()

    class MockTypeTypedefValid:
        @property
        def kind(self):
            return clang.cindex.TypeKind.TYPEDEF

        def get_declaration(self):
            return MockDeclValid()

    assert get_underlying_type(MockTypeInvalid()).kind == clang.cindex.TypeKind.INVALID
    assert get_underlying_type(MockTypeTypedef()).kind == clang.cindex.TypeKind.TYPEDEF
    assert (
        get_underlying_type(MockTypeTypedefValid()).kind == clang.cindex.TypeKind.ENUM
    )


def test_invalid_type_resolution_elaborated():
    """Test resolution of invalid underlying types via elaborated."""
    from check_error_percolation_clang import get_underlying_type

    class MockTypeInvalid:
        @property
        def kind(self):
            return clang.cindex.TypeKind.INVALID

    class MockTypeElaborated:
        @property
        def kind(self):
            return clang.cindex.TypeKind.ELABORATED

        def get_named_type(self):
            return MockTypeInvalid()

    assert (
        get_underlying_type(MockTypeElaborated()).kind
        == clang.cindex.TypeKind.ELABORATED
    )


def test_analyze_call_valid_type():
    """Test analyze_call when call_expr.type is already valid."""
    from check_error_percolation_clang import analyze_call

    call_expr = mock.Mock(kind=clang.cindex.CursorKind.CALL_EXPR)

    class MockType:
        kind = clang.cindex.TypeKind.INT

    class MockTypeInvalid:
        kind = clang.cindex.TypeKind.INVALID

        def get_result(self):
            return MockType()

    call_expr.type = MockTypeInvalid()

    # Should exit early because it's not an enum type, but doesn't need get_result()
    assert analyze_call(call_expr, {}) == []


def test_analyze_call_stops_at_func_decl():
    """Test analyze_call when traversing hits a FUNCTION_DECL before a block."""
    from check_error_percolation_clang import analyze_call

    call_expr = mock.Mock(kind=clang.cindex.CursorKind.CALL_EXPR)
    func_decl = mock.Mock(kind=clang.cindex.CursorKind.FUNCTION_DECL, spelling="myfunc")

    parent_map = {call_expr: func_decl}

    class MockType:
        kind = clang.cindex.TypeKind.ENUM

    call_expr.type = MockType()

    with mock.patch("check_error_percolation_clang.is_enum_type", return_value=True):
        with mock.patch(
            "check_error_percolation_clang.is_macro_instantiation", return_value=False
        ):
            assert analyze_call(call_expr, parent_map) == []


def test_setup_libclang_explicit():
    """Test setup_libclang with an explicit path."""
    from check_error_percolation_clang import setup_libclang

    with mock.patch("clang.cindex.Config.set_library_file") as mock_set:
        setup_libclang("/some/path.so")
        mock_set.assert_called_once_with("/some/path.so")


def test_setup_libclang_fallback():
    """Test setup_libclang fallback logic."""
    from check_error_percolation_clang import setup_libclang

    with mock.patch(
        "clang.cindex.Config.get_cindex_library",
        side_effect=clang.cindex.LibclangError("err"),
    ):
        with mock.patch("glob.glob", return_value=["/usr/lib/libclang.so"]):
            with mock.patch("clang.cindex.Config.set_library_file") as mock_set:
                setup_libclang(None)
                mock_set.assert_called_with("/usr/lib/libclang.so")


def test_setup_libclang_fallback_cpp_ignored():
    """Test setup_libclang fallback ignores cpp files."""
    from check_error_percolation_clang import setup_libclang

    with mock.patch(
        "clang.cindex.Config.get_cindex_library",
        side_effect=clang.cindex.LibclangError("err"),
    ):
        with mock.patch("glob.glob", return_value=["/usr/lib/libclang-cpp.so"]):
            with mock.patch("clang.cindex.Config.set_library_file") as mock_set:
                setup_libclang(None)
                mock_set.assert_not_called()


def test_analyze_call_no_var_name():
    """Test analyze_call when binary operator has no children or wrong kind."""
    from check_error_percolation_clang import analyze_call

    call_expr = mock.Mock(kind=clang.cindex.CursorKind.CALL_EXPR)
    call_expr.location.file.name = "f.c"
    call_expr.location.line = 1
    call_expr.location.column = 1

    block = mock.Mock(kind=clang.cindex.CursorKind.COMPOUND_STMT)
    bin_op = mock.Mock(kind=clang.cindex.CursorKind.BINARY_OPERATOR)
    child = mock.Mock(kind=clang.cindex.CursorKind.UNEXPOSED_EXPR)
    bin_op.get_children.return_value = [child]

    # Hierarchy: COMOUND_STMT -> BINARY_OPERATOR -> CALL_EXPR
    parent_map = {call_expr: bin_op, bin_op: block}

    class MockType:
        kind = clang.cindex.TypeKind.ENUM

    call_expr.type = MockType()

    with mock.patch("check_error_percolation_clang.is_enum_type", return_value=True):
        with mock.patch(
            "check_error_percolation_clang.is_macro_instantiation", return_value=False
        ):
            v = analyze_call(call_expr, parent_map)
            assert len(v) == 1
            assert "Could not determine assigned variable" in v[0].message

            # Hit the valid branch to cover line 332
            ref = mock.Mock(
                kind=clang.cindex.CursorKind.DECL_REF_EXPR, spelling="myvar"
            )
            bin_op.get_children.return_value = [ref]
            block.get_children.return_value = []
            v = analyze_call(call_expr, parent_map)
            assert len(v) == 1
            assert "not immediately checked" in v[0].message


def test_is_macro_instantiation_attr():
    """Test is_macro_instantiation attr setup."""
    from check_error_percolation_clang import is_macro_instantiation

    # Save the original to restore later
    orig_hasattr = hasattr

    def mock_hasattr(obj, name):
        if name == "clang_Location_isFromMainFile":
            return False
        return orig_hasattr(obj, name)

    with mock.patch("builtins.hasattr", side_effect=mock_hasattr):
        with mock.patch("clang.cindex.conf.lib", create=True) as mock_lib:
            mock_lib.clang_Location_isFromMainFile = mock.Mock(return_value=True)
            node = mock.Mock()
            assert is_macro_instantiation(node) is False
            assert hasattr(mock_lib.clang_Location_isFromMainFile, "restype")
            assert hasattr(mock_lib.clang_Location_isFromMainFile, "argtypes")


def test_analyze_call_no_block():
    from check_error_percolation_clang import analyze_call, is_enum_type

    # Mock a call expression that returns an enum but has no parent block
    call_expr = mock.Mock(kind=clang.cindex.CursorKind.CALL_EXPR)

    # Ensure it passes the enum check
    class MockType:
        kind = clang.cindex.TypeKind.ENUM

    call_expr.type = MockType()

    with mock.patch("check_error_percolation_clang.is_enum_type", return_value=True):
        with mock.patch(
            "check_error_percolation_clang.is_macro_instantiation", return_value=False
        ):
            assert analyze_call(call_expr, {}) == []


def test_analyze_call_direct_call_expr():
    """Test analyze_call when the direct parent is the block (discarded)."""
    from check_error_percolation_clang import analyze_call

    call_expr = mock.Mock(kind=clang.cindex.CursorKind.CALL_EXPR)
    call_expr.location.file.name = "f.c"
    call_expr.location.line = 1
    call_expr.location.column = 1

    block = mock.Mock(kind=clang.cindex.CursorKind.COMPOUND_STMT)

    # Make call_expr its own enclosing statement
    parent_map = {call_expr: block}

    with mock.patch("check_error_percolation_clang.is_enum_type", return_value=True):
        with mock.patch(
            "check_error_percolation_clang.is_macro_instantiation", return_value=False
        ):
            v = analyze_call(call_expr, parent_map)
            assert len(v) == 1
            assert "discarded" in v[0].message
    """Test resolution of invalid underlying types via elaborated."""
    from check_error_percolation_clang import get_underlying_type

    class MockTypeInvalid:
        @property
        def kind(self):
            return clang.cindex.TypeKind.INVALID

    class MockTypeElaborated:
        @property
        def kind(self):
            return clang.cindex.TypeKind.ELABORATED

        def get_named_type(self):
            return MockTypeInvalid()

    assert (
        get_underlying_type(MockTypeElaborated()).kind
        == clang.cindex.TypeKind.ELABORATED
    )


def test_get_next_statement_missing():
    """Test getting a statement when missing/end of block."""
    from check_error_percolation_clang import get_next_statement

    assert get_next_statement(mock.Mock(), mock.Mock(get_children=lambda: [])) is None


def test_extract_variable_name_invalid():
    """Test extracting variable name on unsupported types."""
    from check_error_percolation_clang import extract_variable_name

    assert (
        extract_variable_name(mock.Mock(kind=clang.cindex.CursorKind.COMPOUND_STMT))
        is None
    )


def test_extract_variable_name_valid():
    """Test extracting variable name on supported types."""
    from check_error_percolation_clang import extract_variable_name

    # mock a VAR_DECL
    vdecl = mock.Mock(kind=clang.cindex.CursorKind.VAR_DECL, spelling="myvar")
    assert extract_variable_name(vdecl) == "myvar"

    # mock a DECL_STMT
    decl_stmt = mock.Mock(kind=clang.cindex.CursorKind.DECL_STMT)
    decl_stmt.get_children.return_value = [vdecl]
    assert extract_variable_name(decl_stmt) == "myvar"

    # mock a BINARY_OPERATOR
    bin_op = mock.Mock(kind=clang.cindex.CursorKind.BINARY_OPERATOR)
    ref = mock.Mock(kind=clang.cindex.CursorKind.DECL_REF_EXPR, spelling="binvar")
    bin_op.get_children.return_value = [ref]
    assert extract_variable_name(bin_op) == "binvar"


def test_contains_node():
    """Test contains_node."""
    from check_error_percolation_clang import contains_node

    root = mock.Mock()
    child = mock.Mock()
    target = mock.Mock()

    root.get_children.return_value = [child]
    child.get_children.return_value = [target]
    target.get_children.return_value = []

    assert contains_node(root, root) is True
    assert contains_node(root, target) is True
    assert contains_node(root, mock.Mock()) is False


def test_missing_assignment():
    """Test when call expr is assigned to a var but not checked."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        int x = (int)foo();
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "not immediately checked" in violations[0].message.lower()


def test_missing_assignment_complex():
    """Test when call expr is a child of something other than var_decl or bin_op."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    extern void baz(int);
    enum Result bar(void) {
        baz(foo());
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "discarded or not assigned" in violations[0].message.lower()


def test_undetermined_variable():
    """Test when call expr is assigned to something complex like an array index."""
    code = """
    enum Result { OK, ERR };
    extern enum Result foo(void);
    enum Result bar(void) {
        enum Result arr[1];
        arr[0] = foo();
        return OK;
    }
    """
    tu, path = parse_code(code)
    violations = process_file(path, ["-x", "c"], INDEX, [], [])
    os.unlink(path)
    assert len(violations) == 1
    assert "could not determine assigned variable" in violations[0].message.lower()


def test_process_file_load_error():
    """Test process_file handles translation unit load errors."""
    violations = process_file("does_not_exist.c", ["-x", "c"], INDEX, [], [])
    assert len(violations) == 1
    assert "Failed to parse" in violations[0].message


@mock.patch("check_error_percolation_clang.find_c_files")
def test_main_no_c_files(mock_find, monkeypatch):
    """Test main returns 0 when no C files are found."""
    mock_find.return_value = []
    monkeypatch.setattr("sys.argv", ["script", "dir/"])
    assert main() == 0
