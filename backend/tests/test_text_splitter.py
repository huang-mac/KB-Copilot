from app.services.text_splitter import TextSplitter


def test_text_splitter_keeps_metadata() -> None:
    splitter = TextSplitter(chunk_size=10, chunk_overlap=2)

    chunks = splitter.split(
        kb_id="default",
        doc_id="doc-1",
        filename="demo.txt",
        text="abcdefghijklmnopqrstuvwxyz",
    )

    assert len(chunks) > 1
    assert chunks[0].kb_id == "default"
    assert chunks[0].doc_id == "doc-1"
    assert chunks[0].filename == "demo.txt"
    assert chunks[0].chunk_index == 0
