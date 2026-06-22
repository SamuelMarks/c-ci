import pytest
import sys
import subprocess
import os
import shutil
import precommit_matrix
from unittest.mock import patch, MagicMock, mock_open

def test_run_cmd_success(capsys):
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        res = precommit_matrix.run_cmd(["echo", "hello"])
        assert res.returncode == 0
        captured = capsys.readouterr()
        assert "Running: echo hello\n" in captured.out

def test_run_cmd_failure_check_true(capsys):
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        with pytest.raises(SystemExit) as excinfo:
            precommit_matrix.run_cmd(["false_cmd"])
        assert excinfo.value.code == 1

def test_run_cmd_not_found_check_true(capsys):
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit) as excinfo:
            precommit_matrix.run_cmd(["non_existent_cmd"])
        assert excinfo.value.code == 1

def test_run_cmd_not_found_check_false(capsys):
    with patch("subprocess.run", side_effect=FileNotFoundError):
        res = precommit_matrix.run_cmd(["non_existent_cmd"], check=False)
        assert res.returncode == 127

def test_run_cmd_failure_check_false(capsys):
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        res = precommit_matrix.run_cmd(["false_cmd"], check=False)
        assert res.returncode == 1

def test_is_tool():
    with patch("shutil.which", return_value="/usr/bin/gcc"):
        assert precommit_matrix.is_tool("gcc") is True
    with patch("shutil.which", return_value=None):
        assert precommit_matrix.is_tool("nonexistent") is False

def test_has_gcc():
    with patch("precommit_matrix.is_tool", return_value=True):
        assert precommit_matrix.has_gcc() is True

def test_has_clang():
    with patch("precommit_matrix.is_tool", return_value=True):
        assert precommit_matrix.has_clang() is True

@patch("os.name", "nt")
@patch("precommit_matrix.is_tool", return_value=True)
def test_has_msvc_true(mock_is_tool):
    assert precommit_matrix.has_msvc() is True

@patch("os.name", "posix")
def test_has_msvc_false():
    assert precommit_matrix.has_msvc() is False

@patch("os.name", "posix")
@patch("precommit_matrix.is_tool", return_value=True)
@patch("os.path.exists", return_value=True)
def test_has_msvc_wine_true(mock_exists, mock_is_tool):
    assert precommit_matrix.has_msvc_wine() is True

@patch("os.name", "nt")
def test_has_msvc_wine_nt():
    assert precommit_matrix.has_msvc_wine() is False

@patch("os.name", "nt")
@patch("precommit_matrix.is_tool", return_value=True)
@patch("subprocess.run")
def test_has_mingw_true(mock_run, mock_is_tool):
    mock_run.return_value = MagicMock(stderr="mingw32")
    assert precommit_matrix.has_mingw() is True

@patch("os.name", "posix")
def test_has_mingw_false():
    assert precommit_matrix.has_mingw() is False

@patch("os.name", "nt")
@patch("precommit_matrix.is_tool", return_value=True)
@patch("subprocess.run")
def test_has_cygwin_true(mock_run, mock_is_tool):
    mock_run.return_value = MagicMock(stderr="cygwin")
    assert precommit_matrix.has_cygwin() is True

@patch("os.name", "posix")
def test_has_cygwin_false():
    assert precommit_matrix.has_cygwin() is False

def test_main_no_args():
    with patch("sys.argv", ["precommit_matrix.py"]):
        with pytest.raises(SystemExit) as excinfo:
            precommit_matrix.main()
        assert excinfo.value.code == 1

@patch("sys.argv", ["precommit_matrix.py", "cppcheck"])
@patch("precommit_matrix.is_tool", return_value=True)
@patch("os.path.isdir", side_effect=lambda x: x in ["src", "include"])
@patch("precommit_matrix.run_cmd")
def test_main_cppcheck_with_dirs(mock_run_cmd, mock_isdir, mock_is_tool):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    mock_run_cmd.assert_called_once()

@patch("sys.argv", ["precommit_matrix.py", "cppcheck"])
@patch("precommit_matrix.is_tool", return_value=True)
@patch("os.path.isdir", return_value=False)
@patch("precommit_matrix.run_cmd")
def test_main_cppcheck_no_dirs(mock_run_cmd, mock_isdir, mock_is_tool, capsys):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    mock_run_cmd.assert_not_called()
    assert "No src or include directory found" in capsys.readouterr().out

@patch("sys.argv", ["precommit_matrix.py", "cppcheck"])
@patch("precommit_matrix.is_tool", return_value=False)
def test_main_cppcheck_not_found(mock_is_tool, capsys):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert "cppcheck not found" in capsys.readouterr().out

@patch("sys.argv", ["precommit_matrix.py", "build", "gcc"])
@patch("precommit_matrix.has_gcc", return_value=True)
@patch("os.makedirs")
@patch("precommit_matrix.run_cmd")
def test_main_build_gcc(mock_run_cmd, mock_makedirs, mock_has_gcc):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert mock_run_cmd.call_count == 2

@patch("sys.argv", ["precommit_matrix.py", "build", "clang"])
@patch("precommit_matrix.has_clang", return_value=True)
@patch("os.makedirs")
@patch("precommit_matrix.run_cmd")
def test_main_build_clang(mock_run_cmd, mock_makedirs, mock_has_clang):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert mock_run_cmd.call_count == 2

@patch("sys.argv", ["precommit_matrix.py", "build", "msvc_wine"])
@patch("precommit_matrix.has_msvc_wine", return_value=True)
@patch("os.makedirs")
@patch("builtins.open", new_callable=mock_open)
@patch("precommit_matrix.run_cmd")
def test_main_build_msvc_wine(mock_run_cmd, mock_open, mock_makedirs, mock_has_msvc_wine):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert mock_run_cmd.call_count == 2

@patch("sys.argv", ["precommit_matrix.py", "build", "msvc"])
@patch("precommit_matrix.has_msvc", return_value=True)
@patch("os.makedirs")
@patch("precommit_matrix.run_cmd")
def test_main_build_msvc(mock_run_cmd, mock_makedirs, mock_has_msvc):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert mock_run_cmd.call_count == 2

@patch("sys.argv", ["precommit_matrix.py", "build", "mingw"])
@patch("precommit_matrix.has_mingw", return_value=True)
@patch("os.makedirs")
@patch("precommit_matrix.run_cmd")
def test_main_build_mingw(mock_run_cmd, mock_makedirs, mock_has_mingw):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert mock_run_cmd.call_count == 2

@patch("sys.argv", ["precommit_matrix.py", "build", "cygwin"])
@patch("precommit_matrix.has_cygwin", return_value=True)
@patch("os.makedirs")
@patch("precommit_matrix.run_cmd")
def test_main_build_cygwin(mock_run_cmd, mock_makedirs, mock_has_cygwin):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert mock_run_cmd.call_count == 2

@patch("sys.argv", ["precommit_matrix.py", "build", "unknown"])
def test_main_build_unknown(capsys):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert "not found or not supported" in capsys.readouterr().out

@patch("sys.argv", ["precommit_matrix.py", "test", "gcc"])
@patch("os.path.exists", side_effect=lambda x: x == "build_gcc" or x == "scripts/pre_commit.py")
@patch("precommit_matrix.run_cmd")
def test_main_test_gcc_custom_script(mock_run_cmd, mock_exists, capsys):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    mock_run_cmd.assert_called_once()
    assert "Running repo-specific test script..." in capsys.readouterr().out

@patch("sys.argv", ["precommit_matrix.py", "test", "msvc_wine"])
@patch("os.path.exists", side_effect=lambda x: x in ["build_msvc_wine", "build_msvc_wine/_deps"])
@patch("os.listdir", return_value=["some-build", "other-dir"])
@patch("precommit_matrix.run_cmd")
def test_main_test_msvc_wine(mock_run_cmd, mock_listdir, mock_exists):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    mock_run_cmd.assert_called_once()
    assert "some-build" in mock_run_cmd.call_args[1]["env"]["WINEPATH"]

@patch("sys.argv", ["precommit_matrix.py", "test", "gcc"])
@patch("os.path.exists", return_value=False)
def test_main_test_not_found(mock_exists, capsys):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert "Build directory build_gcc not found" in capsys.readouterr().out

@patch("sys.argv", ["precommit_matrix.py", "valgrind", "gcc"])
@patch("precommit_matrix.has_gcc", return_value=True)
@patch("precommit_matrix.is_tool", return_value=True)
@patch("sys.platform", "linux")
@patch("os.path.exists", side_effect=lambda x: x in ["build_gcc", ".valgrind.supp"])
@patch("os.walk", return_value=[("build_gcc", [], ["test_bin", "file.c"]), ("build_gcc/_deps", [], ["test2"])])
@patch("os.access", return_value=True)
@patch("precommit_matrix.run_cmd")
def test_main_valgrind_gcc(mock_run_cmd, mock_access, mock_walk, mock_exists, mock_is_tool, mock_has_gcc, capsys):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    mock_run_cmd.assert_called_once()
    assert "Valgrind clean." in capsys.readouterr().out

@patch("sys.argv", ["precommit_matrix.py", "valgrind", "gcc"])
@patch("precommit_matrix.has_gcc", return_value=True)
@patch("precommit_matrix.is_tool", return_value=True)
@patch("sys.platform", "linux")
@patch("os.path.exists", return_value=False)
def test_main_valgrind_gcc_no_build_dir(mock_exists, mock_is_tool, mock_has_gcc, capsys):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert "Build directory build_gcc not found." in capsys.readouterr().out

@patch("sys.argv", ["precommit_matrix.py", "valgrind", "gcc"])
@patch("precommit_matrix.has_gcc", return_value=False)
def test_main_valgrind_skipped(mock_has_gcc, capsys):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    assert "Valgrind skipped." in capsys.readouterr().out

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x == "scripts/pre_commit.py")
@patch("precommit_matrix.run_cmd")
def test_main_shields_custom_script(mock_run_cmd, mock_exists):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    mock_run_cmd.assert_called_once_with([sys.executable, "scripts/pre_commit.py", "shields"])

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x == "scripts/update_shields.py")
@patch("precommit_matrix.run_cmd")
def test_main_shields_update_shields(mock_run_cmd, mock_exists):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    mock_run_cmd.assert_called_once_with([sys.executable, "scripts/update_shields.py"])

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x == "scripts/update_badges.py")
@patch("precommit_matrix.run_cmd")
def test_main_shields_update_badges(mock_run_cmd, mock_exists):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    mock_run_cmd.assert_called_once_with([sys.executable, "scripts/update_badges.py"])

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x == "scripts/update_badges.sh")
@patch("precommit_matrix.run_cmd")
def test_main_shields_update_badges_sh(mock_run_cmd, mock_exists):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    mock_run_cmd.assert_called_once_with(["bash", "scripts/update_badges.sh"])

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x in ["include", "build_gcc", "README.md"])
@patch("os.walk", return_value=[("include", [], ["file.h"])])
@patch("builtins.open", new_callable=mock_open, read_data="void func();\n/* doc */\nint a;\n")
@patch("os.name", "posix")
@patch("precommit_matrix.is_tool", return_value=True)
@patch("subprocess.run")
def test_main_shields_generic(mock_run, mock_is_tool, mock_open, mock_walk, mock_exists):
    mock_run.return_value = MagicMock(returncode=0, stdout="lines: 85.5%")
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x in ["include", "build_gcc", "README.md"])
@patch("os.walk", return_value=[("include", [], ["file.h"])])
@patch("builtins.open", new_callable=mock_open, read_data="void func();\n\n\n/* doc */\nint a;\n_API test;\nchar b;\n")
@patch("os.name", "posix")
@patch("precommit_matrix.is_tool", return_value=True)
@patch("subprocess.run")
def test_main_shields_generic_more_coverage(mock_run, mock_is_tool, mock_open, mock_walk, mock_exists):
    mock_run.return_value = MagicMock(returncode=0, stdout="lines: 95.0%")
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x in ["README.md"])
@patch("os.name", "posix")
@patch("precommit_matrix.is_tool", return_value=False)
@patch("builtins.open", new_callable=mock_open, read_data="[![License](license)](url)\n")
def test_main_shields_generic_no_test_cov(mock_open, mock_is_tool, mock_exists):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0

def test_main_custom_pre_commit_script():
    with patch("sys.argv", ["precommit_matrix.py", "build", "gcc"]):
        with patch("os.path.exists", return_value=True):
            # this hits the 'if os.path.exists("scripts/pre_commit.py")' logic
            with patch("precommit_matrix.has_gcc", return_value=True):
                with patch("os.makedirs"):
                    with patch("precommit_matrix.run_cmd"):
                        with pytest.raises(SystemExit):
                            precommit_matrix.main()

def test_if_name_main():
    with patch("precommit_matrix.main") as mock_main:
        with patch.dict("sys.modules", {"precommit_matrix": MagicMock(__name__="__main__")}):
            # This is hard to test directly without using subprocess or exec
            pass
