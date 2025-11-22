import os
import sys
import logging
from pathlib import Path
from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    Settings
)
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SimpleNodeParser
import chromadb
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
DB_DIR = "./chroma_db"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "text-embedding-3-small"


def ingest_script_for_rag(script_path: str) -> VectorStoreIndex:
    """
    Process a lecture script PDF and ingest it into the vector database using LlamaIndex.
    
    Pipeline:
    1. Load PDF
    2. Split text using SimpleNodeParser (chunk_size=1000, overlap=200)
    3. Embed chunks using OpenAI text-embedding-3-small
    4. Store in ChromaDB and persist to disk
    
    Args:
        script_path (str): Path to the PDF file
        
    Returns:
        VectorStoreIndex: The vector store index object
        
    Raises:
        FileNotFoundError: If the script file doesn't exist
        ValueError: If OpenAI API key is not configured
    """
    
    # Validate input
    script_file = Path(script_path)
    if not script_file.exists():
        logger.error(f"Script file not found: {script_path}")
        raise FileNotFoundError(f"Script file not found: {script_path}")
    
    if not script_file.suffix.lower() == ".pdf":
        logger.warning(f"File is not a PDF: {script_path}")
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not found in environment variables")
        raise ValueError("OPENAI_API_KEY not configured")
    
    logger.info(f"📄 Step 1: Loading PDF from {script_path}...")
    try:
        # Load PDF using SimpleDirectoryReader
        documents = SimpleDirectoryReader(
            input_files=[script_path]
        ).load_data()
        logger.info(f"✅ Loaded {len(documents)} documents")
    except Exception as e:
        logger.error(f"Failed to load PDF: {e}")
        raise
    
    logger.info(f"🔗 Step 2: Setting up embeddings using {EMBEDDING_MODEL}...")
    try:
        # Configure embeddings
        embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL)
        Settings.embed_model = embed_model
        logger.info(f"✅ Embeddings model initialized")
    except Exception as e:
        logger.error(f"Failed to initialize embeddings: {e}")
        raise
    
    logger.info(f"📝 Step 3: Parsing and chunking text (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    try:
        # Configure node parser for chunking
        node_parser = SimpleNodeParser.from_defaults(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separator="\n\n"
        )
        Settings.node_parser = node_parser
        logger.info(f"✅ Node parser configured")
    except Exception as e:
        logger.error(f"Failed to configure node parser: {e}")
        raise
    
    # Ensure output directory exists
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)
    
    logger.info(f"💾 Step 4: Storing in ChromaDB ({DB_DIR})...")
    try:
        # Initialize Chroma client
        chroma_client = chromadb.PersistentClient(path=DB_DIR)
        chroma_collection = chroma_client.get_or_create_collection(
            name="lecture_script",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Create vector store
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        # Create index
        index = VectorStoreIndex.from_documents(
            documents=documents,
            vector_store=vector_store,
            show_progress=True
        )
        
        logger.info(f"✅ Vector store persisted to {DB_DIR}")
    except Exception as e:
        logger.error(f"Failed to create vector store: {e}")
        raise
    
    logger.info("🎉 RAG ingestion pipeline completed successfully!")
    return index


def load_vector_store() -> VectorStoreIndex:
    """
    Load an existing vector store from disk using LlamaIndex.
    
    Returns:
        VectorStoreIndex: The loaded vector store index
        
    Raises:
        FileNotFoundError: If the database doesn't exist
    """
    if not Path(DB_DIR).exists():
        logger.error(f"Vector store not found at {DB_DIR}")
        raise FileNotFoundError(f"Vector store not found at {DB_DIR}")
    
    logger.info(f"Loading vector store from {DB_DIR}...")
    try:
        # Configure embeddings
        embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL)
        Settings.embed_model = embed_model
        
        # Load Chroma client
        chroma_client = chromadb.PersistentClient(path=DB_DIR)
        chroma_collection = chroma_client.get_collection(name="lecture_script")
        
        # Create vector store from existing collection
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        
        logger.info(f"✅ Vector store loaded")
        return index
    except Exception as e:
        logger.error(f"Failed to load vector store: {e}")
        raise


if __name__ == "__main__":
    # Default script path
    SCRIPT_PATH = "vorlesungsskript.pdf"
    
    # Allow script path from command line
    if len(sys.argv) > 1:
        SCRIPT_PATH = sys.argv[1]
    
    try:
        ingest_script_for_rag(SCRIPT_PATH)
    except Exception as e:
        logger.error(f"❌ RAG Ingestion failed: {e}")
        sys.exit(1)