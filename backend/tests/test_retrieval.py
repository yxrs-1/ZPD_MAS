import os
import sys
import types

from zpd_api.retrieval import _embedding, _ranker, index_chunks, retrieve_named_passages


def test_index_chunks_keeps_each_prepared_chunk(monkeypatch):
    stored = {}

    class VectorStoreIndex:
        def __init__(self, nodes, **_kwargs):
            stored["texts"] = [node.get_content() for node in nodes]
            stored["metadata"] = [dict(node.metadata) for node in nodes]

        @classmethod
        def from_documents(cls, *_args, **_kwargs):
            raise AssertionError("prepared chunks must not be split again")

    class StorageContext:
        @staticmethod
        def from_defaults(**_kwargs):
            return "storage"

    class TextNode:
        def __init__(self, text, metadata=None):
            self.text = text
            self.metadata = metadata or {}

        def get_content(self):
            return self.text

    core = types.ModuleType("llama_index.core")
    core.Document = lambda **kwargs: kwargs
    core.StorageContext = StorageContext
    core.VectorStoreIndex = VectorStoreIndex
    schema = types.ModuleType("llama_index.core.schema")
    schema.TextNode = TextNode
    chroma = types.ModuleType("llama_index.vector_stores.chroma")
    chroma.ChromaVectorStore = lambda **_kwargs: "store"

    monkeypatch.setitem(sys.modules, "llama_index.core", core)
    monkeypatch.setitem(sys.modules, "llama_index.core.schema", schema)
    monkeypatch.setitem(sys.modules, "llama_index.vector_stores.chroma", chroma)
    monkeypatch.setattr("zpd_api.retrieval._collection", lambda: "collection")
    monkeypatch.setattr("zpd_api.retrieval._embedding", lambda: "embed")

    index_chunks(7, "lesson.pdf", ("第一段", "第二段"))

    assert stored["texts"] == ["第一段", "第二段"]
    assert stored["metadata"] == [
        {"material_id": "7", "name": "lesson.pdf"},
        {"material_id": "7", "name": "lesson.pdf"},
    ]


def test_retrieve_uses_embedding_hits_until_the_reranker_is_cached(monkeypatch):
    monkeypatch.setattr("zpd_api.retrieval._reranker_cached", lambda: False)
    monkeypatch.setattr("zpd_api.retrieval._ranker", lambda: (_ for _ in ()).throw(AssertionError("reranker")))
    monkeypatch.setattr("zpd_api.retrieval._collection", lambda: "collection")
    monkeypatch.setattr("zpd_api.retrieval._embedding", lambda: "embed")

    class Node:
        def __init__(self, name, text):
            self.metadata = {"name": name}
            self.text = text

        def get_content(self):
            return self.text

    class Retriever:
        def retrieve(self, _query):
            return [Node(name, text) for name, text in (("a.pdf", "甲"), ("b.pdf", "乙"), ("c.pdf", "丙"), ("d.pdf", "丁"), ("e.pdf", "戊"))]

    class Index:
        @classmethod
        def from_vector_store(cls, *_args, **_kwargs):
            return cls()

        def as_retriever(self, **_kwargs):
            return Retriever()

    core = types.ModuleType("llama_index.core")
    core.VectorStoreIndex = Index
    chroma = types.ModuleType("llama_index.vector_stores.chroma")
    chroma.ChromaVectorStore = lambda **_kwargs: "store"
    monkeypatch.setitem(sys.modules, "llama_index.core", core)
    monkeypatch.setitem(sys.modules, "llama_index.vector_stores.chroma", chroma)

    assert retrieve_named_passages("项目六") == [("a.pdf", "甲"), ("b.pdf", "乙"), ("c.pdf", "丙"), ("d.pdf", "丁")]


def test_embedding_loads_prefetched_weights_without_downloading(monkeypatch, tmp_path):
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(tmp_path))
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    monkeypatch.setattr("zpd_api.retrieval._embed_model", None)

    def cached(repo, filename):
        if repo == "BAAI/bge-small-zh-v1.5" and filename == "pytorch_model.bin":
            return str(tmp_path / filename)
        return None

    hub = types.ModuleType("huggingface_hub")
    hub.try_to_load_from_cache = cached
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)

    seen = {}

    class HuggingFaceEmbedding:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    module = types.ModuleType("llama_index.embeddings.huggingface")
    module.HuggingFaceEmbedding = HuggingFaceEmbedding
    monkeypatch.setitem(sys.modules, "llama_index.embeddings.huggingface", module)

    assert _embedding() is not None
    assert seen == {
        "model_name": "BAAI/bge-small-zh-v1.5",
        "cache_folder": str(tmp_path),
        "local_files_only": True,
    }


def test_cached_reranker_does_not_contact_the_hub(monkeypatch):
    import huggingface_hub.constants as constants

    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.setattr(constants, "HF_HUB_OFFLINE", False)
    monkeypatch.setattr("zpd_api.retrieval._reranker", None)
    monkeypatch.setattr("zpd_api.retrieval._weights_cached", lambda _name: True)
    seen = {}

    class SentenceTransformerRerank:
        def __init__(self, **kwargs):
            seen["offline"] = constants.HF_HUB_OFFLINE
            seen["model"] = kwargs["model"]

    module = types.ModuleType("llama_index.core.postprocessor")
    module.SentenceTransformerRerank = SentenceTransformerRerank
    monkeypatch.setitem(sys.modules, "llama_index.core.postprocessor", module)

    try:
        assert _ranker() is not None
        assert seen == {"offline": True, "model": "BAAI/bge-reranker-v2-m3"}
    finally:
        os.environ.pop("HF_HUB_OFFLINE", None)
