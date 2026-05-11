from __future__ import annotations

from pathlib import Path

from corelm import CoreLMProduct


def test_product_roundtrip(tmp_path: Path) -> None:
    session = tmp_path / 'session.json'
    product = CoreLMProduct(seed=0)
    product.ingest_fact('corelm', 'project', 'name', 'Lucid Mind', text='Draft name is Lucid Mind.')
    product.correct_fact('corelm', 'project', 'name', 'Core LM', text='Final name is Core LM.')
    assert product.get_value('corelm', 'project', 'name') == 'Core LM'
    assert 'Final name is Core LM.' in product.get_provenance('corelm', 'project', 'name')
    saved = product.save_session(session)
    loaded = CoreLMProduct.load_session(saved)
    assert loaded.get_value('corelm', 'project', 'name') == 'Core LM'
    assert loaded.replay_verify()['ok'] is True


def test_branch_listing() -> None:
    product = CoreLMProduct(seed=1)
    product.ingest_fact('corelm', 'llm', 'role', 'excitation source only')
    product.ingest_fact('corelm', 'truth', 'store', 'core state')
    listing = product.list_branch('corelm')
    assert 'llm.role=excitation source only' in listing
    assert 'truth.store=core state' in listing
