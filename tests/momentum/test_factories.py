from momentum.factories import create_ic_split_adapter


def test_create_ic_split_adapter_forwards_allowed_symbols() -> None:
    adapter = create_ic_split_adapter(allowed_symbols={"BTC"})

    assert adapter.allowed_symbols == {"BTC"}


def test_create_ic_split_adapter_preserves_empty_allowed_symbols() -> None:
    adapter = create_ic_split_adapter(allowed_symbols=set())

    assert adapter.allowed_symbols == set()
