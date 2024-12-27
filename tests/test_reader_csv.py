import pytest
from io import StringIO

from tptools.reader.csv import CSVReader


@pytest.fixture
def simple_csv_stream():
    return StringIO("first,second,third\nA,1,True\nB,2,false\nC,3,False\n")


def test_reader_iter(simple_csv_stream):
    reader = CSVReader(simple_csv_stream)
    assert "first" in next(reader)
    for i, r in enumerate(reader):
        pass
    assert i == 1


def test_reader_auto_convert_int(simple_csv_stream):
    reader = CSVReader(simple_csv_stream, auto_convert_int=True)
    rec = next(reader)
    assert rec["second"] == 1


def test_reader_no_auto_convert_int(simple_csv_stream):
    reader = CSVReader(simple_csv_stream, auto_convert_int=False)
    rec = next(reader)
    assert rec["second"] == "1"


def test_reader_auto_convert_bool(simple_csv_stream):
    reader = CSVReader(simple_csv_stream, auto_convert_bool=True)
    assert next(reader)["third"]
    assert not next(reader)["third"]
    assert not next(reader)["third"]


def test_reader_no_auto_convert_bool(simple_csv_stream):
    reader = CSVReader(simple_csv_stream, auto_convert_bool=False)
    assert next(reader)["third"] == "True"
