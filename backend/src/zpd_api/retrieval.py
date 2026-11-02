import os

_embed_model = None
_reranker = None


def _hub_cache() -> str | None:
    configured = os.environ.get("HUGGINGFACE_HUB_CACHE")
    if configured:
        return configured
    home = os.environ.get("HF_HOME")
    if home:
        return os.path.join(home, "hub")
    return None


def _weights_cached(name: str) -> bool:
    from huggingface_hub import try_to_load_from_cache

    return any(
        isinstance(try_to_load_from_cache(name, filename), str)
        for filename in ("model.safetensors", "pytorch_model.bin")
    )


def _embedding():
    global _embed_model
    if _embed_model is None:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        name = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
        kwargs = {"model_name": name}
        cache = _hub_cache()
        if cache:
            kwargs["cache_folder"] = cache
        if _weights_cached(name):
            kwargs["local_files_only"] = True
        _embed_model = HuggingFaceEmbedding(**kwargs)
    return _embed_model


def _ranker():
    global _reranker
    if _reranker is None:
        from llama_index.core.postprocessor import SentenceTransformerRerank

        name = os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
        if _weights_cached(name):
            os.environ["HF_HUB_OFFLINE"] = "1"
            import huggingface_hub.constants as constants

            constants.HF_HUB_OFFLINE = True
        _reranker = SentenceTransformerRerank(model=name, top_n=4)
    return _reranker


def _collection():
    import chromadb

    client = chromadb.HttpClient(
        host=os.environ.get("CHROMA_HOST", "localhost"),
        port=int(os.environ.get("CHROMA_PORT", "8000")),
    )
    return client.get_or_create_collection("materials")


def index_chunks(material_id: int, name: str, chunks: tuple[str, ...]) -> None:
    from llama_index.core import StorageContext, VectorStoreIndex
    from llama_index.core.schema import TextNode
    from llama_index.vector_stores.chroma import ChromaVectorStore

    vector_store = ChromaVectorStore(chroma_collection=_collection())
    storage = StorageContext.from_defaults(vector_store=vector_store)
    nodes = [
        TextNode(text=chunk, metadata={"material_id": str(material_id), "name": name})
        for chunk in chunks
    ]
    VectorStoreIndex(nodes, storage_context=storage, embed_model=_embedding())


def delete_material(material_id: int) -> None:
    _collection().delete(where={"material_id": str(material_id)})


def _reranker_cached() -> bool:
    name = os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    return _weights_cached(name)


def retrieve_named_passages(query: str) -> list[tuple[str, str]]:
    from llama_index.core import VectorStoreIndex
    from llama_index.vector_stores.chroma import ChromaVectorStore

    vector_store = ChromaVectorStore(chroma_collection=_collection())
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=_embedding())
    nodes = index.as_retriever(similarity_top_k=12).retrieve(query)
    if _reranker_cached():
        nodes = _ranker().postprocess_nodes(nodes, query_str=query)
    else:
        nodes = nodes[:4]
    return [(str(node.metadata.get("name", "")), node.get_content()) for node in nodes]


def retrieve_passages(query: str) -> list[str]:
    return [text for _name, text in retrieve_named_passages(query)]
