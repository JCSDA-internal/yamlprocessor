import json

from dateutil.parser import parse as datetimeparse
import filecmp
import pytest
from ruamel.yaml import YAML

from ..datapreprocess import (
    DataPreProcessor, main)


@pytest.fixture
def yaml():
    return YAML(typ='safe', pure=True)

def create_input_files(path):
    # Write the content to a file named "a.yaml"
    with open(path+"/a.yaml", 'w') as file:
        file.write("DIRECT_INCLUDE=$FILE_PATH/b.yaml\n")
        file.write("\n")
        file.write("data:\n")
        file.write("    brain: *banana\n")
        file.write("    tel: *groups\n")
    # Write the content to a file named "b.yaml"
    with open(path+"/b.yaml", 'w') as file:
        file.write("_:\n")
        file.write("- &banana 1\n")
        file.write("- &groups [4, 5, 6]\n")

def create_comparison(path):
    with open(path+"/reference_0.yaml", 'w') as file:
        file.write("_:\n")
        file.write("- &banana 1\n")
        file.write("- &groups [4, 5, 6]\n")
        file.write("\n")
        file.write("data:\n")
        file.write("    brain: *banana\n")
        file.write("    tel: *groups\n")

def compare_files(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        content1 = f1.read()
        content2 = f2.read()
        
    assert content1 == content2, f"Files {file1} and {file2} do not match."

def test_main_0(tmp_path, yaml):
    """Test main, basic."""
    # Create test files
    create_input_files(tmp_path)
    create_comparison(tmp_path)
    # Run preprocessor
    preprocessor = DataPreProcessor()
    keymap = {"$FILE_PATH": tmp_path}
    preprocessor.add_replacements_map(keymap)
    preprocessor.process_yaml(tmp_path + "/a.yaml", tmp_path + "/test_0.yaml")
    # Check output
    compare_files(tmp_path + "/test_0.yaml", tmp_path + "/reference_0.yaml")
