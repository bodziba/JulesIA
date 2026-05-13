import os
import tempfile
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb

from config import DB_DIR, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDINGS_MODEL, RETRIEVER_K

# Initialize embeddings
embedding_function = SentenceTransformerEmbeddings(model_name=EMBEDDINGS_MODEL)

# Initialize Chroma client
client = chromadb.PersistentClient(path=DB_DIR)

def get_vectorstore() -> Chroma:
    """Returns the Chroma vectorstore instance."""
    return Chroma(
        client=client,
        collection_name="pai_docs",
        embedding_function=embedding_function
    )

def index_pdf(uploaded_file, metadata: Dict[str, Any]) -> int:
    """
    Saves uploaded file to temp directory, loads with PyPDFLoader,
    splits with RecursiveCharacterTextSplitter, adds to ChromaDB.
    Returns number of chunks indexed.
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        loader = PyPDFLoader(tmp_path)
        documents = loader.load()

        # Clean up temp file
        os.unlink(tmp_path)

        # Enhance metadata
        doc_id = str(uuid.uuid4())
        enhanced_metadata = metadata.copy()
        enhanced_metadata.update({
            "doc_id": doc_id,
            "filename": uploaded_file.name,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        for doc in documents:
            doc.metadata.update(enhanced_metadata)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )

        chunks = text_splitter.split_documents(documents)

        if not chunks:
            return 0

        vectorstore = get_vectorstore()
        vectorstore.add_documents(chunks)

        return len(chunks)
    except Exception as e:
        print(f"Error indexing PDF {uploaded_file.name}: {e}")
        raise e

def get_indexed_documents() -> List[Dict[str, Any]]:
    """
    Retrieves unique documents from ChromaDB based on doc_id.
    """
    try:
        vectorstore = get_vectorstore()
        collection = vectorstore._collection

        # Get all metadatas
        results = collection.get(include=["metadatas"])
        metadatas = results.get("metadatas", [])

        if not metadatas:
            return []

        # Group by doc_id
        docs_map = {}
        for meta in metadatas:
            if not meta:
                continue
            doc_id = meta.get("doc_id")
            if doc_id:
                if doc_id not in docs_map:
                    docs_map[doc_id] = {
                        "doc_id": doc_id,
                        "filename": meta.get("filename", "Unknown"),
                        "uploaded_at": meta.get("uploaded_at", "Unknown"),
                        "chunks": 0,
                        "metadata": meta
                    }
                docs_map[doc_id]["chunks"] += 1

        # Sort by uploaded_at descending
        sorted_docs = sorted(list(docs_map.values()), key=lambda x: x.get("uploaded_at", ""), reverse=True)
        return sorted_docs
    except Exception as e:
        print(f"Error getting indexed documents: {e}")
        return []

def remove_document(doc_id: str) -> bool:
    """
    Removes all chunks associated with a doc_id from ChromaDB.
    """
    try:
        vectorstore = get_vectorstore()
        collection = vectorstore._collection
        collection.delete(where={"doc_id": doc_id})
        return True
    except Exception as e:
        print(f"Error removing document {doc_id}: {e}")
        return False

def remove_all_documents() -> bool:
    """
    Removes all documents from ChromaDB.
    """
    try:
        vectorstore = get_vectorstore()
        collection = vectorstore._collection
        # Get all ids to delete
        results = collection.get(include=[])
        ids = results.get("ids", [])
        if ids:
             collection.delete(ids=ids)
        return True
    except Exception as e:
        print(f"Error removing all documents: {e}")
        return False

def get_relevant_context(query: str, system: str, client_name: str) -> str:
    """
    Retrieves context using similarity search with metadata filtering.
    """
    try:
        vectorstore = get_vectorstore()

        # Construct filter based on rules
        # Rules:
        # - GLOBAL: used in any ticket
        # - CLIENT: only in corresponding client
        # - SYSTEM: only in corresponding system
        # - PRIVATE: requires explicit match (we'll ignore for now or require strict match if both system/client provided)

        # In Chroma, we can use $or to combine conditions
        where_filter = {
            "$or": [
                {"scope": "GLOBAL"},
                {"$and": [{"scope": "CLIENT"}, {"client": client_name}]},
                {"$and": [{"scope": "SYSTEM"}, {"system": system}]}
            ]
        }

        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": RETRIEVER_K,
                "filter": where_filter
            }
        )

        docs = retriever.invoke(query)
        if not docs:
            return ""

        context = []
        for doc in docs:
            filename = doc.metadata.get('filename', 'Unknown')
            context.append(f"--- Documento: {filename} ---\n{doc.page_content}")

        return "\n\n".join(context)
    except Exception as e:
        print(f"Error retrieving context: {e}")
        return ""
