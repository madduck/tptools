from tptools.ext.squore import SquoreCourt


def test_serialize_to_just_id(sqcourt: SquoreCourt) -> None:
    assert sqcourt.model_dump() == sqcourt.id
