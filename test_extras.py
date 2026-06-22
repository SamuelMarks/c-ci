import pytest
import sys
import subprocess
import os
import shutil
import importlib
import precommit_matrix
from unittest.mock import patch, MagicMock, mock_open

def test_git_env_stripping():
    with patch.dict(os.environ, {"GIT_DIR": "foo", "GIT_WORK_TREE": "bar", "GIT_INDEX_FILE": "baz"}):
        importlib.reload(precommit_matrix)
    assert "GIT_DIR" not in os.environ
    assert "GIT_WORK_TREE" not in os.environ
    assert "GIT_INDEX_FILE" not in os.environ

def test_main_custom_pre_commit_script_cppcheck():
    with patch("sys.argv", ["precommit_matrix.py", "cppcheck"]):
        with patch("os.path.exists", side_effect=lambda x: x == "scripts/pre_commit.py"):
            with patch("precommit_matrix.is_tool", return_value=False):
                with pytest.raises(SystemExit):
                    precommit_matrix.main()

@patch("sys.argv", ["precommit_matrix.py", "test", "msvc_wine"])
@patch("os.path.exists", side_effect=lambda x: x in ["build_msvc_wine", "build_msvc_wine/_deps"])
@patch("os.listdir", return_value=["some-build", "not-match", "dir-build"])
@patch("precommit_matrix.run_cmd")
def test_main_test_msvc_wine_branches(mock_run_cmd, mock_listdir, mock_exists):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    winepath = mock_run_cmd.call_args[1]["env"]["WINEPATH"]
    assert "some-build" in winepath
    assert "dir-build" in winepath
    assert "not-match" not in winepath

@patch("sys.argv", ["precommit_matrix.py", "test", "msvc_wine"])
@patch("os.path.exists", side_effect=lambda x: x in ["build_msvc_wine"]) # _deps does not exist
@patch("precommit_matrix.run_cmd")
def test_main_test_msvc_wine_no_deps(mock_run_cmd, mock_exists):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0

@patch("sys.argv", ["precommit_matrix.py", "valgrind", "gcc"])
@patch("precommit_matrix.has_gcc", return_value=True)
@patch("precommit_matrix.is_tool", return_value=True)
@patch("sys.platform", "linux")
@patch("os.path.exists", side_effect=lambda x: x in ["build_gcc"])
@patch("os.walk", return_value=[("build_gcc", [], ["notest", "test_file.c", "test_file.h", "test_file.sh", "test_file.py", "parson_test", "test_bin"])])
@patch("os.access", side_effect=lambda x, y: x.endswith("test_bin"))
@patch("precommit_matrix.run_cmd")
def test_main_valgrind_gcc_filter(mock_run_cmd, mock_access, mock_walk, mock_exists, mock_is_tool, mock_has_gcc, capsys):
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0
    mock_run_cmd.assert_called_once()
    assert "test_bin" in mock_run_cmd.call_args[0][0][-1]

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x in ["include", "build_gcc"]) # No README.md
@patch("os.walk", return_value=[("include", [], ["file.h"])])
@patch("builtins.open", new_callable=mock_open, read_data="void f1();\n\n\n\n\nvoid f2();\n") # j goes < 0
@patch("os.name", "posix")
@patch("precommit_matrix.is_tool", return_value=True)
@patch("subprocess.run")
def test_main_shields_no_readme(mock_run, mock_is_tool, mock_open, mock_walk, mock_exists):
    mock_run.return_value = MagicMock(returncode=1) # coverage cmd fails
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x in ["include", "build_gcc", "README.md"])
@patch("os.walk", return_value=[("include", [], ["file.h"])])
@patch("builtins.open", new_callable=mock_open, read_data="void func();\n/* doc */\nint a;\n")
@patch("os.name", "posix")
@patch("precommit_matrix.is_tool", return_value=True)
@patch("subprocess.run")
def test_main_shields_no_match(mock_run, mock_is_tool, mock_open, mock_walk, mock_exists):
    mock_run.return_value = MagicMock(returncode=0, stdout="no coverage data")
    with pytest.raises(SystemExit) as excinfo:
        precommit_matrix.main()
    assert excinfo.value.code == 0

def get_shields_mocked(cov_out, read_data="void func();\n/* doc */\nint a;\n"):
    with patch("sys.argv", ["precommit_matrix.py", "shields"]):
        with patch("os.path.exists", side_effect=lambda x: x in ["include", "build_gcc", "README.md"]):
            with patch("os.walk", return_value=[("include", [], ["file.h"])]):
                with patch("builtins.open", new_callable=mock_open, read_data=read_data) as m_open:
                    with patch("os.name", "posix"):
                        with patch("precommit_matrix.is_tool", return_value=True):
                            with patch("subprocess.run") as mock_run:
                                mock_run.return_value = MagicMock(returncode=0, stdout=cov_out)
                                with pytest.raises(SystemExit):
                                    precommit_matrix.main()
                                return m_open

def test_main_shields_colors():
    # 85% is green
    get_shields_mocked("lines: 85.0%")
    # 75% is yellowgreen
    get_shields_mocked("lines: 75.0%")
    # 65% is yellow
    get_shields_mocked("lines: 65.0%")
    # 50% is red
    get_shields_mocked("lines: 50.0%")

@patch("subprocess.run")
def test_if_name_main(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    process = subprocess.run(["python3", "precommit_matrix.py", "cppcheck"], env=os.environ, check=False)
    assert process.returncode == 0 or process.returncode == 1 # Depending on if cppcheck is installed, it exits 0.

def test_if_name_main_direct_execution():
    with patch("sys.argv", ["precommit_matrix.py", "cppcheck"]):
        with patch("precommit_matrix.is_tool", return_value=False):
            with pytest.raises(SystemExit) as excinfo:
                precommit_matrix.main()
            assert excinfo.value.code == 0
