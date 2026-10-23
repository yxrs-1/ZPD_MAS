from scaffolding.documents import StoredDocument, rank_passages


def _doc(doc_id: str, name: str, *chunks: str) -> StoredDocument:
    return StoredDocument(doc_id, name, chunks)


def test_more_distinct_words_rank_first_and_the_sixth_is_dropped():
    documents = (
        _doc("doc-1", "a.docx", "只有信息", "信息 与 数据"),
        _doc("doc-2", "b.pdf", "信息，数据，系统"),
    )

    ranked = rank_passages(documents, "信息，数据！系统")

    assert ranked[0] == ("b.pdf", "信息，数据，系统")
    assert ranked[1] == ("a.docx", "信息 与 数据")
    assert ("a.docx", "只有信息") in ranked
    assert len(ranked) == 3


def test_ties_follow_upload_order_then_chunk_order_and_case_is_exact():
    documents = tuple(
        _doc("doc-" + str(index), "f" + str(index) + ".docx", "Data", "data")
        for index in range(1, 5)
    )

    ranked = rank_passages(documents, "data")

    assert ranked[0] == ("f1.docx", "data")
    assert rank_passages(documents, "，，，") == ()
    assert len(rank_passages(tuple(
        _doc("doc-" + str(index), "n.docx", "词" + str(index)) for index in range(6)
    ), "词0 词1 词2 词3 词4 词5")) == 5
