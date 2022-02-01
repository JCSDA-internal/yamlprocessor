import json

from dateutil.parser import parse as datetimeparse
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


def test_process_variable_2():
    """Test DataProcessor.process_variable time substitution syntax."""
    processor = DataProcessor()
    processor.variable_map.clear()
    processor.time_now = datetimeparse('2012-01-20T12:01')
    processor.time_ref = datetimeparse('2022-02-20T22:02')
    assert (
        processor.process_variable(r"${YP_TIME_NOW}")
        == '2012-01-20T12:01:00')
    assert (
        processor.process_variable(r"${YP_TIME_REF}")
        == '2022-02-20T22:02:00')
    assert (
        processor.process_variable(r"${YP_TIME_REF_AT_T0H0M0S}")
        == '2022-02-20T00:00:00')
    assert (
        processor.process_variable(r"${YP_TIME_REF_AT_1DT0H0M0S}")
        == '2022-02-01T00:00:00')
    assert (
        processor.process_variable(r"${YP_TIME_REF_MINUS_T10H2M}")
        == '2022-02-20T12:00:00')
    assert (
        processor.process_variable(r"${YP_TIME_REF_PLUS_10D}")
        == '2022-03-02T22:02:00')
    assert (
        processor.process_variable(r"${YP_TIME_REF_AT_1DT0H0M0S_MINUS_T12H}")
        == '2022-01-31T12:00:00')


def test_process_variable_3():
    """Test DataProcessor.process_variable time substitution format."""
    processor = DataProcessor()
    processor.variable_map.clear()
    processor.time_formats.update({
        'ABBR': '%Y%m%dT%H%M%S%z',
        'MIN_UTC': '%Y%m%dT%H%MZ',
        'CTIME': '%a %e %b %T %Y',
    })
    processor.time_ref = datetimeparse('2022-02-20T22:02Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF}")
        == '2022-02-20T22:02:00+0000')
    assert (
        processor.process_variable(r"${YP_TIME_REF_FORMAT_ABBR}")
        == '20220220T220200+0000')
    assert (
        processor.process_variable(r"${YP_TIME_REF_FORMAT_MIN_UTC}")
        == '20220220T2202Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF_FORMAT_CTIME}")
        == 'Sun 20 Feb 22:02:00 2022')


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


def test_main_8(tmp_path):
    """Test main, YAML object (i.e. dict) key order."""
    infilename = tmp_path / 'a.yaml'
    incontent = "xyz: 1\npqrs: 2\nabc: 3\nijk: 4\n"
    with infilename.open('w') as infile:
        infile.write(incontent)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    with outfilename.open() as outfile:
        outcontent = outfile.read()
    assert incontent == outcontent


def test_main_9(tmp_path):
    """Test main, single include with query."""
    data = {'testing': [1, 2, 3]}
    data_0 = {'testing': {
        'INCLUDE': '1.yaml',
        'QUERY': "[?favourite].value",
    }}
    data_1 = [
        {'value': 1, 'favourite': True},
        {'value': 1.5, 'favourite': False},
        {'value': 2, 'favourite': True},
        {'value': 2.7, 'favourite': False},
        {'value': 3, 'favourite': True},
        {'value': 3.1, 'favourite': False},
    ]
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data_0, infile)
    with (tmp_path / '1.yaml').open('w') as infile_1:
        yaml.dump(data_1, infile_1)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.safe_load(outfilename.open()) == data


def test_main_validate_1(tmp_path, capsys):
    """Test main, YAML with JSON schema validation."""
    schema = {
        'type': 'object',
        'properties': {'hello': {'type': 'string'}},
        'required': ['hello'],
        'additionalProperties': False,
    }
    schemafilename = tmp_path / 'hello.schema.json'
    with schemafilename.open('w') as schemafile:
        json.dump(schema, schemafile)
    outfilename = tmp_path / 'b.yaml'
    infilename = tmp_path / 'a.yaml'
    # Schema specified as an absolute file system path
    with infilename.open('w') as infile:
        infile.write(f'#!{schemafilename}\n')
        yaml.dump({'hello': 'earth'}, infile)
    main([str(infilename), str(outfilename)])
    captured = capsys.readouterr()
    assert f'[INFO] ok {outfilename}' in captured.err.splitlines()
    # Schema specified as a file:// URL
    with infilename.open('w') as infile:
        infile.write(f'#!file://{schemafilename}\n')
        yaml.dump({'hello': 'earth'}, infile)
    main([str(infilename), str(outfilename)])
    captured = capsys.readouterr()
    assert f'[INFO] ok {outfilename}' in captured.err.splitlines()
    # Schema specified as a relative path, with schema prefix
    with infilename.open('w') as infile:
        infile.write('#!hello.schema.json\n')
        yaml.dump({'hello': 'earth'}, infile)
    schema_prefix = f'--schema-prefix=file://{tmp_path}/'
    main([schema_prefix, str(infilename), str(outfilename)])
    captured = capsys.readouterr()
    assert f'[INFO] ok {outfilename}' in captured.err.splitlines()
