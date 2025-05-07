import pytest

import tptools.reader.csv as csv_reader


@pytest.fixture
def simple_csv_data():
    return (
        "letter,number,boolean,string\n"
        "A,1,True,\n"
        "B,2,false,bar\n"
        "C,3,False,foo\n"
    )


@pytest.fixture
def simple_csv_file(tmp_path, simple_csv_data):
    tmpfile = tmp_path / "testdata"
    with open(tmpfile, "w") as f:
        f.write(simple_csv_data)
    return tmpfile


def test_reader_iter(simple_csv_file):
    with csv_reader.connect(simple_csv_file) as reader:
        n = 0
        for n, i in enumerate(reader, 1):
            assert "letter" in i
            assert n
        assert n == 3


def test_reader_next(simple_csv_file):
    with csv_reader.connect(simple_csv_file) as reader:
        n = next(reader)
        assert "letter" in n
        assert len(list(reader)) == 2


def test_reader_no_file():
    with csv_reader.CSVReader() as reader:
        with pytest.raises(ValueError):
            next(reader)


def test_reader_query(simple_csv_file):
    with csv_reader.connect(simple_csv_file) as reader:
        for i, row in enumerate(reader.query(""), 1):
            assert "letter" in row
            assert row["number"] == str(i)


def test_reader_query_warning(simple_csv_file):
    with csv_reader.connect(simple_csv_file) as reader:
        with pytest.warns():
            list(reader.query("query"))
