from lateral.overlap import _intersect


def test_hunks_intersect() -> None:
    assert _intersect((10, 20), (15, 25))
    assert not _intersect((10, 20), (20, 30))
