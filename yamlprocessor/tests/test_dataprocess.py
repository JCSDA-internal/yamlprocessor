import yaml

from ..dataprocess import main


def test_main_0(tmp_path):
    data = {'testing': [1, 2, 3]}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data, infile)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.safe_load(outfilename.open()) == data


def test_main_1(tmp_path):
    data = {'testing': [1, 2, 3]}
    data_0 = {'testing': ['yaml::1.yaml', 2, 3]}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data_0, infile)
    with (tmp_path / '1.yaml').open('w') as infile_1:
        yaml.dump(1, infile_1)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.safe_load(outfilename.open()) == data


def test_main_3(tmp_path):
    data = {'testing': [1, 2, {3: [3.1, 3.14]}]}
    data_0 = {'testing': ['yaml::1.yaml', 2, 'yaml::3.yaml']}
    infilename = tmp_path / 'a.yaml'
    with infilename.open('w') as infile:
        yaml.dump(data_0, infile)
    with (tmp_path / '1.yaml').open('w') as infile_1:
        yaml.dump(1, infile_1)
    with (tmp_path / '3.yaml').open('w') as infile_3:
        yaml.dump({3: 'yaml::3x.yaml'}, infile_3)
    with (tmp_path / '3x.yaml').open('w') as infile_3x:
        yaml.dump([3.1, 3.14], infile_3x)
    outfilename = tmp_path / 'b.yaml'
    main([str(infilename), str(outfilename)])
    assert yaml.safe_load(outfilename.open()) == data
