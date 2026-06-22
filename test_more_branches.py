import pytest
import precommit_matrix
from unittest.mock import patch, mock_open

@patch("sys.argv", ["precommit_matrix.py", "shields"])
@patch("os.path.exists", side_effect=lambda x: x in ["include", "build_gcc"])
@patch("os.walk", return_value=[("include", [], ["file.h"])])
@patch("builtins.open", new_callable=mock_open, read_data="void f1();\n// comment\n\nvoid f2();\n")
@patch("os.name", "posix")
@patch("precommit_matrix.is_tool", return_value=True)
@patch("subprocess.run")
def test_main_shields_lines_j_strip_not_empty(mock_run, mock_is_tool, mock_open, mock_walk, mock_exists):
    with pytest.raises(SystemExit):
        precommit_matrix.main()

def test_module_execution():
    import runpy
    with patch("sys.argv", ["precommit_matrix.py", "cppcheck"]):
        with patch("precommit_matrix.is_tool", return_value=False):
            with pytest.raises(SystemExit):
                runpy.run_path("precommit_matrix.py", run_name="__main__")
