import os
import yaml

from ..appconfprocess import get_filename, main


def test_get_filename_abs():
    name = os.path.abspath(__file__)
    assert name == get_filename(name)


def test_get_filename_rel_0():
    assert os.path.abspath('myfile.txt') == get_filename('myfile.txt')


def test_get_filename_rel_1(tmp_path):
    orig_filename = tmp_path / 'original.txt'
    assert (
        str(tmp_path / 'myfile.txt')
        == get_filename('myfile.txt', str(orig_filename))
    )


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
