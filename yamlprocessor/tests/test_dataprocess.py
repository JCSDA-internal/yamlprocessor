import pytest
import yaml

from ..dataprocess import DataProcessor, main, UnboundVariableError


def test_process_variable_0():
    """Test DataProcessor.process_variable null op."""
    processor = DataProcessor()
    processor.variable_map.clear()
    processor.variable_map['ZERO'] = '0'
    # Turn off .is_process_variable
    processor.is_process_variable = False
    assert '${ZERO}' == processor.process_variable('${ZERO}')
    # Turn on .is_process_variable, but argument not a string
    processor.is_process_variable = True
    assert [0] == processor.process_variable([0])


def test_process_variable_1():
    """Test DataProcessor.process_variable normal op."""
    processor = DataProcessor()
    processor.variable_map.clear()
    # Normal variable substitution
    processor.variable_map['GREET'] = 'Hello'
    processor.variable_map['PERSON'] = 'Jo'
    result = processor.process_variable(
        r"Today's \${PERSON} is ${PERSON}. $GREET $PERSON!")
    assert "Today's ${PERSON} is Jo. Hello Jo!" == result
    # Unbound variable, exception
    with pytest.raises(UnboundVariableError) as excinfo:
        processor.process_variable('Who is the ${ALIEN}?')
        assert str(excinfo.value) == '[UNBOUND VARIABLE] ALIEN'
    # Unbound variable, with placeholder
    processor.unbound_placeholder = 'unknown'
    assert (
        'Who is the unknown?'
        == processor.process_variable('Who is the ${ALIEN}?')
    )


def test_main_0(tmp_path):
    """Test main, basic."""
    data = {'testing': [1, 2, 3]}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data, infile)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.safe_load(outfilename.open()) == data


def test_main_1(tmp_path):
    """Test main, single include."""
    data = {'testing': [1, 2, 3]}
    data_0 = {'testing': [{'INCLUDE': '1.yaml'}, 2, 3]}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data_0, infile)
    with (tmp_path / '1.yaml').open('w') as infile_1:
        yaml.dump(1, infile_1)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.safe_load(outfilename.open()) == data


def test_main_3(tmp_path):
    """Test main, 3 way include."""
    data = {'testing': [1, 2, {3: [3.1, 3.14]}]}
    data_0 = {'testing': [{'INCLUDE': '1.yaml'}, 2, {'INCLUDE': '3.yaml'}]}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data_0, infile)
    with (tmp_path / '1.yaml').open('w') as infile_1:
        yaml.dump(1, infile_1)
    with (tmp_path / '3.yaml').open('w') as infile_3:
        yaml.dump({3: {'INCLUDE': '3x.yaml'}}, infile_3)
    with (tmp_path / '3x.yaml').open('w') as infile_3x:
        yaml.dump([3.1, 3.14], infile_3x)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.safe_load(outfilename.open()) == data


def test_main_4(tmp_path):
    """Test main, no process include."""
    data = {'testing': [{'INCLUDE': '1.yaml'}, 2, {'INCLUDE': '3.yaml'}]}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data, infile)
    outfilename = tmp_path / 'b.yaml'
    main(['--no-process-include', str(infilename), str(outfilename)])
    assert yaml.safe_load(outfilename.open()) == data


def test_main_5(tmp_path):
    """Test main, process variable."""
    data = ['${GREET} ${PERSON}', '${GREET} ${ALIEN}']
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data, infile)
    outfilename = tmp_path / 'b.yaml'
    main([
        '--no-environment',
        '-DGREET=Hello',
        '--define=PERSON=Jo',
        '--unbound-placeholder=unknown',
        str(infilename),
        str(outfilename),
    ])
    assert yaml.safe_load(outfilename.open()) == ['Hello Jo', 'Hello unknown']


def test_main_6(tmp_path):
    """Test main, no process variable."""
    data = ['${GREET} ${PERSON}', '${GREET} ${ALIEN}']
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data, infile)
    outfilename = tmp_path / 'b.yaml'
    main(['--no-process-variable', str(infilename), str(outfilename)])
    assert yaml.safe_load(outfilename.open()) == data


def test_main_7(tmp_path):
    """Test main, include files in a separate folder."""
    data = {'testing': [1, 2, {3: [3.1, 3.14]}]}
    data_0 = {'testing': [{'INCLUDE': '1.yaml'}, 2, {'INCLUDE': '3.yaml'}]}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data_0, infile)
    include_d = tmp_path / 'include'
    include_d.mkdir()
    with (include_d / '1.yaml').open('w') as infile_1:
        yaml.dump(1, infile_1)
    with (include_d / '3.yaml').open('w') as infile_3:
        yaml.dump({3: {'INCLUDE': '3x.yaml'}}, infile_3)
    with (include_d / '3x.yaml').open('w') as infile_3x:
        yaml.dump([3.1, 3.14], infile_3x)
    outfilename = tmp_path / 'b.yaml'
    main(['-I', str(include_d), str(infilename), str(outfilename)])
    assert yaml.safe_load(outfilename.open()) == data
