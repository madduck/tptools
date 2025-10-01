import pytest

from tptools.sqlmodels import TPModel


class Obj(TPModel):
    id: int


class Model(TPModel):
    attrid_: int
    attr: Obj | None = None
    noassociatedattrid_: str = "foo"


@pytest.fixture
def obj() -> Obj:
    return Obj(id=1)


@pytest.fixture
def model(obj: Obj) -> Model:
    return Model(attrid_=obj.id, attr=obj)


def test_set_id_sets_obj(obj: Obj) -> None:
    model = Model(attrid_=0)
    model.attr = obj
    assert model.attrid_ == 1


def test_model_dump_has_instance_not_id(obj: Obj, model: Model) -> None:
    dump = model.model_dump()
    assert "attr" in dump
    assert "attrid_" not in dump

    assert "noassociatedattrid_" in dump
