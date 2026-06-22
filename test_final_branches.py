import pytest
import precommit_matrix
import os
import sys
from unittest.mock import patch, mock_open

@patch("sys.argv", ["precommit_matrix.py", "cppcheck"])
@patch("precommit_matrix.is_tool", return_value=True)
@patch("os.path.isdir", side_effect=lambda x: x == "src") # src is dir, include is not
@patch("precommit_matrix.run_cmd")
def test_main_cppcheck_src_only(mock_run_cmd, mock_isdir, mock_is_tool):
    with pytest.raises(SystemExit):
        precommit_matrix.main()

@patch("sys.argv", ["precommit_matrix.py", "unknown_job"])
def test_main_unknown_job():
    precommit_matrix.main() # shouldn't sys.exit because there is no else! Wait, sys.exit is inside all jobs.
    # Actually, it will just implicitly return None

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x in ["include"])
@patch("os.walk", return_value=[("include", [], ["file.h", "file.c", "file.txt"])])
@patch("builtins.open", new_callable=mock_open, read_data="void f1();\n")
@patch("os.name", "posix")
@patch("precommit_matrix.is_tool", return_value=True)
@patch("subprocess.run")
def test_main_shields_non_h_file(mock_run, mock_is_tool, mock_open, mock_walk, mock_exists):
    with pytest.raises(SystemExit):
        precommit_matrix.main()

