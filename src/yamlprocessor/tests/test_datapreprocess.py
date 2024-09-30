import pytest
from ruamel.yaml import YAML

from ..datapreprocessor import (
    DataPreProcessor)


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
DIRECT_INCLUDE=${FILE_PATH}/aux.yaml

data:
    brain: *banana
    tel: *groups
"""
    yaml_2 = """
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

    infilename = tmp_path / 'in_1.yaml'
    with infilename.open('w') as infile:
        infile.write(yaml_1)

    auxfilename = tmp_path / 'aux.yaml'
    with auxfilename.open('w') as auxfile:
        auxfile.write(yaml_2)

    # Run preprocessor
    preprocessor = DataPreProcessor()
    keymap = {"FILE_PATH": str(tmp_path)}
    preprocessor.add_replacements_map(keymap)
    # Setup reference
    ref_yaml = yaml.load(reference)
    # Test first style input
    outfilename0 = tmp_path / 'test_0.yaml'
    preprocessor.process_yaml(tmp_path / 'in_0.yaml', outfilename0)
    assert yaml.load(outfilename0.open()) == ref_yaml
    # Test second style input
    outfilename1 = tmp_path / 'test_1.yaml'
    preprocessor.process_yaml(tmp_path / 'in_1.yaml', outfilename1)
    assert yaml.load(outfilename1.open()) == ref_yaml
