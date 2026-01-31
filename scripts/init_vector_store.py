# #!/usr/bin/env python3
# """
# Initialize ChromaDB vector store with post-mortem data for RAG.
# Uses Vertex AI embeddings when available, falls back to simple embeddings.
# """
# import os
# import sys
# from pathlib import Path

# sys.path.insert(0, str(Path(__file__).parent.parent))

# import pandas as pd
# import chromadb
# from chromadb.config import Settings

# POST_MORTEMS_PATH = Path("data/post_mortems/incidents.csv")
# CHROMA_DIR = Path("data/embeddings")
# COLLECTION_NAME = "post_mortems"


# def load_incidents() -> pd.DataFrame:
#     """Load post-mortem incidents from CSV."""
#     if not POST_MORTEMS_PATH.exists():
#         print(f"❌ Post-mortems file not found: {POST_MORTEMS_PATH}")
#         print("   Run 'make mock-data' first")
#         sys.exit(1)
    
#     df = pd.read_csv(POST_MORTEMS_PATH)
#     print(f"✓ Loaded {len(df)} incidents")
#     return df


# def create_documents(df: pd.DataFrame) -> tuple[list[str], list[dict], list[str]]:
#     """Create documents, metadata, and IDs for ChromaDB."""
#     documents = []
#     metadatas = []
#     ids = []
    
#     for _, row in df.iterrows():
#         doc_text = f"""
# Channel: {row['channel']}
# Anomaly Type: {row['anomaly_type']}
# Severity: {row['severity']}
# Root Cause: {row['root_cause']}
# Resolution: {row['resolution']}
#         """.strip()
        
#         documents.append(doc_text)
#         metadatas.append({
#             "incident_id": str(row['incident_id']),
#             "date": str(row['date']),
#             "channel": str(row['channel']),
#             "anomaly_type": str(row['anomaly_type']),
#             "severity": str(row['severity']),
#             "root_cause": str(row['root_cause']),
#             "resolution": str(row['resolution']),
#         })
#         ids.append(str(row['incident_id']))
    
#     return documents, metadatas, ids


# def get_vertex_embedding_function():
#     """Get Vertex AI embedding function."""
#     try:
#         from langchain_google_vertexai import VertexAIEmbeddings
#         from src.utils.config import settings
        
#         # Check credentials exist
#         has_creds = (
#             os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or
#             os.path.exists(os.path.expanduser("~/.config/gcloud/application_default_credentials.json"))
#         )
        
#         if not has_creds or not settings.google_cloud_project:
#             return None
        
#         print(f"  Using Vertex AI embeddings (project: {settings.google_cloud_project})")
        
#         embeddings = VertexAIEmbeddings(
#             model_name=settings.embedding_model,
#             project=settings.google_cloud_project,
#             location=settings.vertex_ai_location,
#         )
        
#         # Wrap for ChromaDB compatibility
#         return VertexEmbeddingWrapper(embeddings)
        
#     except Exception as e:
#         print(f"  ⚠️ Vertex AI embeddings not available: {e}")
#         return None


# class VertexEmbeddingWrapper:
#     """Wrapper to make LangChain embeddings compatible with ChromaDB."""
    
#     def __init__(self, embeddings):
#         self.embeddings = embeddings
    
#     def __call__(self, input):
#         if isinstance(input, str):
#             input = [input]
#         return self.embeddings.embed_documents(input)
    
#     def embed_documents(self, texts):
#         return self.embeddings.embed_documents(texts)
    
#     def embed_query(self, text=None, input=None):
#         query = input if input is not None else text
#         if isinstance(query, list):
#             return self.embeddings.embed_documents(query)
#         return self.embeddings.embed_query(query)


# class SimpleHashEmbedding:
#     """Fallback hash-based embeddings for testing."""
    
#     def __call__(self, input):
#         return self._embed(input)
    
#     def _embed(self, texts):
#         import hashlib
#         if isinstance(texts, str):
#             texts = [texts]
#         embeddings = []
#         for text in texts:
#             hash_bytes = hashlib.sha256(text.encode()).digest()
#             embedding = [(hash_bytes[i % 32] - 128) / 128.0 for i in range(768)]
#             embeddings.append(embedding)
#         return embeddings
    
#     def embed_documents(self, texts):
#         return self._embed(texts)
    
#     def embed_query(self, text=None, input=None):
#         query = input if input is not None else text
#         if isinstance(query, list):
#             return self._embed(query)
#         return self._embed([query])


# def initialize_vector_store():
#     """Initialize ChromaDB with post-mortem documents."""
    
#     print("\n" + "="*50)
#     print("🔧 Initializing RAG Vector Store")
#     print("="*50)
    
#     df = load_incidents()
#     documents, metadatas, ids = create_documents(df)
    
#     CHROMA_DIR.mkdir(parents=True, exist_ok=True)
#     print(f"\n📁 ChromaDB location: {CHROMA_DIR}")
    
#     client = chromadb.PersistentClient(
#         path=str(CHROMA_DIR),
#         settings=Settings(anonymized_telemetry=False),
#     )
    
#     # Get embedding function
#     print("\n🧠 Setting up embeddings...")
#     embedding_fn = get_vertex_embedding_function()
    
#     if embedding_fn is None:
#         print("  Using fallback hash embeddings (for testing)")
#         embedding_fn = SimpleHashEmbedding()
    
#     # Delete existing collection
#     try:
#         client.delete_collection(COLLECTION_NAME)
#         print(f"  Deleted existing '{COLLECTION_NAME}' collection")
#     except Exception:
#         pass
    
#     # Create collection
#     print(f"\n📚 Creating '{COLLECTION_NAME}' collection...")
#     collection = client.create_collection(
#         name=COLLECTION_NAME,
#         embedding_function=embedding_fn,
#         metadata={"description": "Marketing Post-Mortems"}
#     )
    
#     # Add documents
#     print(f"\n📝 Adding {len(documents)} documents...")
#     collection.add(
#         documents=documents,
#         metadatas=metadatas,
#         ids=ids,
#     )
#     print(f"  ✓ Added {collection.count()} documents")
    
#     # Test search
#     print("\n🔍 Testing search...")
#     test_query = "CPA spike competitor bidding"
#     results = collection.query(query_texts=[test_query], n_results=2)
    
#     if results and results.get("documents"):
#         for i, doc in enumerate(results["documents"][0]):
#             meta = results["metadatas"][0][i]
#             print(f"\n  Result {i+1}: {meta.get('incident_id')}")
#             print(f"    Channel: {meta.get('channel')}")
#             print(f"    Type: {meta.get('anomaly_type')}")
    
#     print("\n" + "="*50)
#     print("✅ RAG Vector Store initialized!")
#     print("="*50)


# if __name__ == "__main__":
#     initialize_vector_store()

#<----- Tier 3 and tier 4 update -------->
#!/usr/bin/env python3
"""
Initialize ChromaDB vector store with post-mortem data for RAG.
Uses Vertex AI embeddings when available, falls back to simple embeddings.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import chromadb
from chromadb.config import Settings

POST_MORTEMS_PATH = Path("data/post_mortems/incidents.csv")
CHROMA_DIR = Path("data/embeddings")
COLLECTION_NAME = "post_mortems"


def load_incidents() -> pd.DataFrame:
    """Load post-mortem incidents from CSV."""
    if not POST_MORTEMS_PATH.exists():
        print(f"❌ Post-mortems file not found: {POST_MORTEMS_PATH}")
        print("   Run 'make mock-data' first")
        sys.exit(1)
    
    df = pd.read_csv(POST_MORTEMS_PATH)
    print(f"✓ Loaded {len(df)} incidents")
    return df


def create_documents(df: pd.DataFrame) -> tuple[list[str], list[dict], list[str]]:
    """Create documents, metadata, and IDs for ChromaDB."""
    documents = []
    metadatas = []
    ids = []
    
    for _, row in df.iterrows():
        doc_text = f"""
Channel: {row['channel']}
Anomaly Type: {row['anomaly_type']}
Severity: {row['severity']}
Root Cause: {row['root_cause']}
Resolution: {row['resolution']}
        """.strip()
        
        # Convert date string (YYYY-MM-DD) to integer (YYYYMMDD) for filtering
        try:
            date_str = str(row['date'])
            date_int = int(date_str.replace('-', ''))
        except (ValueError, AttributeError):
            # Fallback for invalid dates
            date_int = 0
        
        documents.append(doc_text)
        metadatas.append({
            "incident_id": str(row['incident_id']),
            "date": str(row['date']),
            "date_int": date_int,  # Added for numeric filtering
            "channel": str(row['channel']),
            "anomaly_type": str(row['anomaly_type']),
            "severity": str(row['severity']),
            "root_cause": str(row['root_cause']),
            "resolution": str(row['resolution']),
        })
        ids.append(str(row['incident_id']))
    
    return documents, metadatas, ids


def get_vertex_embedding_function():
    """Get Vertex AI embedding function."""
    try:
        from langchain_google_vertexai import VertexAIEmbeddings
        from src.utils.config import settings
        
        # Check credentials exist
        has_creds = (
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or
            os.path.exists(os.path.expanduser("~/.config/gcloud/application_default_credentials.json"))
        )
        
        if not has_creds or not settings.google_cloud_project:
            return None
        
        print(f"  Using Vertex AI embeddings (project: {settings.google_cloud_project})")
        
        embeddings = VertexAIEmbeddings(
            model_name=settings.embedding_model,
            project=settings.google_cloud_project,
            location=settings.vertex_ai_location,
        )
        
        # Wrap for ChromaDB compatibility
        return VertexEmbeddingWrapper(embeddings)
        
    except Exception as e:
        print(f"  ⚠️ Vertex AI embeddings not available: {e}")
        return None


class VertexEmbeddingWrapper:
    """Wrapper to make LangChain embeddings compatible with ChromaDB."""
    
    def __init__(self, embeddings):
        self.embeddings = embeddings
        # Added attributes to satisfy ChromaDB introspection
        self.name = "VertexEmbeddingWrapper"
        self.__name__ = "VertexEmbeddingWrapper"
    
    def __call__(self, input):
        if isinstance(input, str):
            input = [input]
        return self.embeddings.embed_documents(input)
    
    def embed_documents(self, texts):
        return self.embeddings.embed_documents(texts)
    
    def embed_query(self, text=None, input=None):
        query = input if input is not None else text
        if isinstance(query, list):
            return self.embeddings.embed_documents(query)
        return self.embeddings.embed_query(query)


class SimpleHashEmbedding:
    """Fallback hash-based embeddings for testing."""
    
    def __call__(self, input):
        return self._embed(input)
    
    def _embed(self, texts):
        import hashlib
        if isinstance(texts, str):
            texts = [texts]
        embeddings = []
        for text in texts:
            hash_bytes = hashlib.sha256(text.encode()).digest()
            embedding = [(hash_bytes[i % 32] - 128) / 128.0 for i in range(768)]
            embeddings.append(embedding)
        return embeddings
    
    def embed_documents(self, texts):
        return self._embed(texts)
    
    def embed_query(self, text=None, input=None):
        query = input if input is not None else text
        if isinstance(query, list):
            return self._embed(query)
        return self._embed([query])


def initialize_vector_store():
    """Initialize ChromaDB with post-mortem documents."""
    
    print("\n" + "="*50)
    print("🔧 Initializing RAG Vector Store")
    print("="*50)
    
    df = load_incidents()
    documents, metadatas, ids = create_documents(df)
    
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 ChromaDB location: {CHROMA_DIR}")
    
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    
    # Get embedding function
    print("\n🧠 Setting up embeddings...")
    embedding_fn = get_vertex_embedding_function()
    
    if embedding_fn is None:
        print("  Using fallback hash embeddings (for testing)")
        embedding_fn = SimpleHashEmbedding()
    
    # Delete existing collection
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Deleted existing '{COLLECTION_NAME}' collection")
    except Exception:
        pass
    
    # Create collection
    print(f"\n📚 Creating '{COLLECTION_NAME}' collection...")
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "Marketing Post-Mortems"}
    )
    
    # Add documents
    print(f"\n📝 Adding {len(documents)} documents...")
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )
    print(f"  ✓ Added {collection.count()} documents")
    
    # Test search
    print("\n🔍 Testing search...")
    test_query = "CPA spike competitor bidding"
    results = collection.query(query_texts=[test_query], n_results=2)
    
    if results and results.get("documents"):
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            print(f"\n  Result {i+1}: {meta.get('incident_id')}")
            print(f"    Channel: {meta.get('channel')}")
            print(f"    Type: {meta.get('anomaly_type')}")
    
    print("\n" + "="*50)
    print("✅ RAG Vector Store initialized!")
    print("="*50)


if __name__ == "__main__":
    initialize_vector_store()
