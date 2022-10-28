import json

from dateutil.parser import parse as datetimeparse
import pytest
from ruamel.yaml import YAML

from ..dataprocess import (
    DataProcessor, main, strftime_with_colon_z, UnboundVariableError)


@pytest.fixture
def yaml():
    return YAML(typ='safe', pure=True)


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
    processor.time_ref = datetimeparse('2022-02-20T22:02Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF}")
        == '2022-02-20T22:02:00Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF_AT_T0H0M0S}")
        == '2022-02-20T00:00:00Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF_AT_1DT0H0M0S}")
        == '2022-02-01T00:00:00Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF_MINUS_T10H2M}")
        == '2022-02-20T12:00:00Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF_PLUS_10D}")
        == '2022-03-02T22:02:00Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF_AT_1DT0H0M0S_MINUS_T12H}")
        == '2022-01-31T12:00:00Z')
    assert (
        processor.process_variable(r"${YP_TIME_NOW}")
        == strftime_with_colon_z(processor.time_now, '%FT%T%:z'))


def test_process_variable_3():
    """Test DataProcessor.process_variable time substitution format."""
    processor = DataProcessor()
    processor.variable_map.clear()
    processor.time_formats.update({
        'ABBR': '%Y%m%dT%H%M%S%z',
        'MIN_UTC': '%Y%m%dT%H%MZ',
        'CTIME': '%a %e %b %T %Y',
        'LONG_2': '%FT%T%::z',
        'LONG_3': '%FT%T%:::z',
    })
    processor.time_ref = datetimeparse('2022-02-20T22:02Z')
    # Default time format %FT%T%:z
    assert (
        processor.process_variable(r"${YP_TIME_REF}")
        == '2022-02-20T22:02:00Z')
    # Custom time formats
    assert (
        processor.process_variable(r"${YP_TIME_REF_FORMAT_ABBR}")
        == '20220220T220200Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF_FORMAT_MIN_UTC}")
        == '20220220T2202Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF_FORMAT_CTIME}")
        == 'Sun 20 Feb 22:02:00 2022')
    assert (
        processor.process_variable(r"${YP_TIME_REF_FORMAT_LONG_2}")
        == '2022-02-20T22:02:00Z')
    assert (
        processor.process_variable(r"${YP_TIME_REF_FORMAT_LONG_3}")
        == '2022-02-20T22:02:00Z')


def test_process_variable_4():
    """Test DataProcessor.process_variable time zone substitution format."""
    processor = DataProcessor()
    processor.variable_map.clear()
    processor.time_formats.update({
        'ABBR': '%Y%m%dT%H%M%S%z',
        # '': '%FT%T%:z',  # default format
        'LONG_2': '%FT%T%::z',
        'LONG_3': '%FT%T%:::z',
    })
    for in_, out0, out1, out2, out3 in (
        ('-12:00', '-1200', '-12:00', '-12:00:00', '-12'),
        ('-09:45', '-0945', '-09:45', '-09:45:00', '-09:45'),
        ('-09:30', '-0930', '-09:30', '-09:30:00', '-09:30'),
        ('-05:15', '-0515', '-05:15', '-05:15:00', '-05:15'),
        ('-01:00', '-0100', '-01:00', '-01:00:00', '-01'),
        ('-00:45', '-0045', '-00:45', '-00:45:00', '-00:45'),
        ('+00:00', 'Z', 'Z', 'Z', 'Z'),
        ('-00:00', 'Z', 'Z', 'Z', 'Z'),
        ('+00:30', '+0030', '+00:30', '+00:30:00', '+00:30'),
        ('+01:00', '+0100', '+01:00', '+01:00:00', '+01'),
        ('+04:30', '+0430', '+04:30', '+04:30:00', '+04:30'),
        ('+05:45', '+0545', '+05:45', '+05:45:00', '+05:45'),
        ('+09:15', '+0915', '+09:15', '+09:15:00', '+09:15'),
        ('+12:45', '+1245', '+12:45', '+12:45:00', '+12:45'),
        ('+14:00', '+1400', '+14:00', '+14:00:00', '+14'),
    ):
        processor.time_ref = datetimeparse('2022-02-20T22:02' + in_)
        assert (
            processor.process_variable(r"${YP_TIME_REF_FORMAT_ABBR}")
            == '20220220T220200' + out0)
        assert (
            processor.process_variable(r"${YP_TIME_REF}")  # default format
            == '2022-02-20T22:02:00' + out1)
        assert (
            processor.process_variable(r"${YP_TIME_REF_FORMAT_LONG_2}")
            == '2022-02-20T22:02:00' + out2)
        assert (
            processor.process_variable(r"${YP_TIME_REF_FORMAT_LONG_3}")
            == '2022-02-20T22:02:00' + out3)


def test_process_variable_5():
    """Test DataProcessor.process_variable int, float, bool substitution."""
    processor = DataProcessor()
    processor.variable_map.clear()
    # Variables for substitution
    processor.variable_map.update({
        'N_PLANETS': '8',
        'COLD': '-10',
        'PI': '3.14',
        'CHARGE': '-1.6E-19',
        'LOWER_TRUE': 'true',
        'UPPER_TRUE': 'TRUE',
        'YES': 'yes',
        'ONE': '1',
        'LOWER_FALSE': 'false',
        'UPPER_FALSE': 'FALSE',
        'NO': 'no',
        'ZERO': '0',
        'STRING': 'string',
    })
    # Good usages
    assert processor.process_variable(r'${N_PLANETS.int}') == 8
    assert processor.process_variable(r'${COLD.int}') == -10
    assert processor.process_variable(r'${PI.float}') == 3.14
    assert processor.process_variable(r'${CHARGE.float}') == -1.6E-19
    for name in ('LOWER_TRUE', 'UPPER_TRUE', 'YES', 'ONE'):
        assert processor.process_variable(r"${" + name + r".bool}") is True
    for name in ('LOWER_FALSE', 'UPPER_FALSE', 'NO', 'ZERO'):
        assert processor.process_variable(r"${" + name + r".bool}") is False
    # Bad usages
    with pytest.raises(ValueError) as excinfo:
        processor.process_variable(r'Not ${PI.float}.')
        assert (
            str(excinfo.value)
            == 'Not ${PI.float}.: bad substitution expression'
        )
    for cast in ('.int', '.float', '.bool'):
        item = r'${STRING' + cast + r'}'
        with pytest.raises(ValueError) as excinfo:
            processor.process_variable(item)
            assert (
                str(excinfo.value) == item + ': bad substitution value: string'
            )


def test_main_0(tmp_path, yaml):
    """Test main, basic."""
    data = {'testing': [1, 2, 3]}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data, infile)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.load(outfilename.open()) == data


def test_main_1(tmp_path, yaml):
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
    assert yaml.load(outfilename.open()) == data


def test_main_3(tmp_path, yaml):
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
    assert yaml.load(outfilename.open()) == data


def test_main_4(tmp_path, yaml):
    """Test main, no process include."""
    data = {'testing': [{'INCLUDE': '1.yaml'}, 2, {'INCLUDE': '3.yaml'}]}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data, infile)
    outfilename = tmp_path / 'b.yaml'
    main(['--no-process-include', str(infilename), str(outfilename)])
    assert yaml.load(outfilename.open()) == data


def test_main_5(tmp_path, yaml):
    """Test main, process variable, with placeholder."""
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
    assert yaml.load(outfilename.open()) == ['Hello Jo', 'Hello unknown']
    main([
        '--no-environment',
        '-DGREET=Hello',
        '--define=PERSON=Jo',
        '--unbound-placeholder=' + DataProcessor.UNBOUND_ORIGINAL,
        str(infilename),
        str(outfilename),
    ])
    assert yaml.load(outfilename.open()) == ['Hello Jo', 'Hello ${ALIEN}']


def test_main_6(tmp_path, yaml):
    """Test main, no process variable."""
    data = ['${GREET} ${PERSON}', '${GREET} ${ALIEN}']
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data, infile)
    outfilename = tmp_path / 'b.yaml'
    main(['--no-process-variable', str(infilename), str(outfilename)])
    assert yaml.load(outfilename.open()) == data


def test_main_7(tmp_path, yaml):
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
    assert yaml.load(outfilename.open()) == data


def test_main_8(tmp_path, yaml):
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


def test_main_9(tmp_path, yaml):
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
    assert yaml.load(outfilename.open()) == data


def test_main_10(tmp_path, yaml):
    """Test main, with date-time string."""
    data = {
        'you-time': '2030-04-05T06:07:08Z',
        'me-time': '2030-04-05T06:07:08+09:00',
        'that-time': '2040-06-08T10:12:14-10:30',
    }
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data, infile)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.load(outfilename.open()) == {
        'you-time': '2030-04-05T06:07:08Z',
        'me-time': '2030-04-05T06:07:08+09:00',
        'that-time': '2040-06-08T10:12:14-10:30',
    }


def test_main_11(tmp_path, yaml):
    """Test main, include file with variables."""
    hello_data = {
        'hello': [
            {
                'INCLUDE': 'world.yaml',
                'VARIABLES': {'NAME': 'venus', 'PEOPLE': 'venusian'},
            },
            {
                'INCLUDE': 'world2.yaml',
                'VARIABLES': {'NAME': 'mars', 'PEOPLE': 'martian'},
            },
            {
                'INCLUDE': 'world.yaml',
            },
        ],
    }
    world_data = {
        'location': '${NAME}',
        'people': '${PEOPLE}',
    }
    infilename = tmp_path / 'hello.yaml'
    with infilename.open('w') as infile:
        yaml.dump(hello_data, infile)
    with (tmp_path / 'world.yaml').open('w') as infile:
        yaml.dump(world_data, infile)
    with (tmp_path / 'world2.yaml').open('w') as infile:
        yaml.dump({'INCLUDE': 'world.yaml'}, infile)
    outfilename = tmp_path / 'b.yaml'
    main([
        '--define=NAME=earth',
        '--define=PEOPLE=human',
        str(infilename),
        str(outfilename)])
    assert yaml.load(outfilename.open()) == {
        'hello': [
            {'location': 'venus', 'people': 'venusian'},
            {'location': 'mars', 'people': 'martian'},
            {'location': 'earth', 'people': 'human'},
        ],
    }


def test_main_12(tmp_path, yaml):
    """Test main, merge include files into a list."""
    root_data = [
        {'name': 'cat', 'speak': ['meow', 'miaow']},
        {'INCLUDE': 'more-farm-1.yaml', 'MERGE': True},
        {'INCLUDE': 'more-farm-2.yaml', 'MERGE': True},
        {'name': 'fish', 'speak': ['bubble', 'bubble']},
    ]
    more_data_1 = [
        {'name': 'dog', 'speak': ['woof', 'bark']},
        {'name': 'sheep', 'speak': ['baa', 'baa']},
    ]
    more_data_2 = [
        {'name': 'duck', 'speak': ['quack', 'quack']},
        {'name': 'farmer', 'speak': ['e-i-e-i-o']},
    ]
    infilename = tmp_path / 'root.yaml'
    with infilename.open('w') as infile:
        yaml.dump(root_data, infile)
    include_infilename = tmp_path / 'more-farm-1.yaml'
    with include_infilename.open('w') as infile:
        yaml.dump(more_data_1, infile)
    include_infilename = tmp_path / 'more-farm-2.yaml'
    with include_infilename.open('w') as infile:
        yaml.dump(more_data_2, infile)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.load(outfilename.open()) == [
        {'name': 'cat', 'speak': ['meow', 'miaow']},
        {'name': 'dog', 'speak': ['woof', 'bark']},
        {'name': 'sheep', 'speak': ['baa', 'baa']},
        {'name': 'duck', 'speak': ['quack', 'quack']},
        {'name': 'farmer', 'speak': ['e-i-e-i-o']},
        {'name': 'fish', 'speak': ['bubble', 'bubble']},
    ]


def test_main_13(tmp_path, yaml):
    """Test main, merge include files into a map/object."""
    root_data = {
        'cat': {
            'speak': ['meow', 'miaow'],
            'dummy': {'INCLUDE': 'cat-data.yaml', 'MERGE': True},
            'young': 'kitten',
            'like': ['food'],
        },
    }
    cat_data = {
        'chase': ['rodents', 'birds'],
        'like': ['food', 'play', 'sleep'],
    }
    infilename = tmp_path / 'root.yaml'
    with infilename.open('w') as infile:
        yaml.dump(root_data, infile)
    include_infilename = tmp_path / 'cat-data.yaml'
    with include_infilename.open('w') as infile:
        yaml.dump(cat_data, infile)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.load(outfilename.open()) == {
        'cat': {
            'speak': ['meow', 'miaow'],
            'young': 'kitten',
            'chase': ['rodents', 'birds'],
            'like': ['food', 'play', 'sleep'],
        },
    }


def test_main_14(tmp_path, yaml):
    """Test main, include at root with include-scope variables."""
    root_data = {
        'INCLUDE': 'data.yaml',
        'VARIABLES': {
            'GREET_ONE': '$GREET $WORLD',
            'GREET_TWO': '$GREET $PEOPLE',
        },
    }
    data = {
        'greet-world': '$GREET_ONE',
        'greet-people': '$GREET_TWO',
    }
    infilename = tmp_path / 'root.yaml'
    with infilename.open('w') as infile:
        yaml.dump(root_data, infile)
    include_infilename = tmp_path / 'data.yaml'
    with include_infilename.open('w') as infile:
        yaml.dump(data, infile)
    outfilename = tmp_path / 'b.yaml'
    main([
        '--define=GREET=Hello',
        '--define=WORLD=Mars',
        '--define=PEOPLE=Martians',
        str(infilename),
        str(outfilename),
    ])
    assert yaml.load(outfilename.open()) == {
        'greet-world': 'Hello Mars',
        'greet-people': 'Hello Martians',
    }


def test_main_validate_1(tmp_path, capsys, yaml):
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
    for prefix in ('#!', '# yaml-language-server: $schema='):
        # Schema specified as an absolute file system path
        with infilename.open('w') as infile:
            infile.write(f'{prefix}{schemafilename}\n')
            yaml.dump({'hello': 'earth'}, infile)
        main([str(infilename), str(outfilename)])
        captured = capsys.readouterr()
        assert f'[INFO] ok {outfilename}' in captured.err.splitlines()
        # Schema specified as a file:// URL
        with infilename.open('w') as infile:
            infile.write(f'{prefix}file://{schemafilename}\n')
            yaml.dump({'hello': 'earth'}, infile)
        main([str(infilename), str(outfilename)])
        captured = capsys.readouterr()
        assert f'[INFO] ok {outfilename}' in captured.err.splitlines()
        # Schema specified as a relative path, with schema prefix
        with infilename.open('w') as infile:
            infile.write(f'{prefix}hello.schema.json\n')
            yaml.dump({'hello': 'earth'}, infile)
        schema_prefix = f'--schema-prefix=file://{tmp_path}/'
        main([schema_prefix, str(infilename), str(outfilename)])
        captured = capsys.readouterr()
        assert f'[INFO] ok {outfilename}' in captured.err.splitlines()


def test_process_data_include_dict(tmp_path, yaml):
    """Test DataProcessor.process_data, with DataProcessor.include_dict."""
    data = {'testing': ['one', 2, {3: [3.1, 3.14]}]}
    data_0 = {'testing': [{'INCLUDE': '1.yaml'}, 2, {'INCLUDE': '3.yaml'}]}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data_0, infile)
    # This one gets overriden.
    with (tmp_path / '1.yaml').open('w') as infile_1:
        yaml.dump(1, infile_1)
    # This one is used.
    with (tmp_path / '3.yaml').open('w') as infile_3:
        yaml.dump({3: {'INCLUDE': '3x.yaml'}}, infile_3)
    processor = DataProcessor()
    processor.include_dict.update({
        '1.yaml': 'one',  # This one overrides.
        '3x.yaml': [3.1, 3.14],  # This one is used.
    })
    outfilename = tmp_path / 'b.yaml'
    processor.process_data(str(infilename), str(outfilename))
    assert yaml.load(outfilename.open()) == data
