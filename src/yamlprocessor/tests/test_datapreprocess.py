import json

from dateutil.parser import parse as datetimeparse
import filecmp
import pytest
from ruamel.yaml import YAML

from ..datapreprocessor import (
    DataPreProcessor, main)


@pytest.fixture
def yaml():
    return YAML(typ='safe', pure=True)


def test_main_0(tmp_path, yaml):
    """Test main, basic."""
    yaml_0 = """
DIRECT_INCLUDE=$FILE_PATH/aux.yaml

data:
    brain: *banana
    tel: *groups
"""
    yaml_1 = """
_:
- &banana 1
- &groups [4, 5, 6]
"""
    reference = """
_:
- &banana 1
- &groups [4, 5, 6]

data:
    brain: *banana
    tel: *groups
"""
    infilename = tmp_path / 'in_0.yaml'
    with infilename.open('w') as infile:
        infile.write(yaml_0)

    auxfilename = tmp_path / 'aux.yaml'
    with auxfilename.open('w') as auxfile:
        auxfile.write(yaml_1)

    # Run preprocessor
    preprocessor = DataPreProcessor()
    keymap = {"FILE_PATH": str(tmp_path)}
    preprocessor.add_replacements_map(keymap)
    outfilename = tmp_path / 'test_0.yaml'
    preprocessor.process_yaml(tmp_path / 'in_0.yaml', outfilename)
    # Check output
    ref_yaml = yaml.load(reference)
    assert yaml.load(outfilename.open()) == ref_yaml
