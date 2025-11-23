import os
import sys
import logging
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import streamlit as st
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Disable verbose OpenAI/urllib3 logs
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Suppress all other loggers
for name in logging.root.manager.loggerDict:
    if name not in ["__main__", __name__]:
        logging.getLogger(name).setLevel(logging.CRITICAL)

load_dotenv()

# Configuration
DB_DIR = "./chroma_db"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "text-embedding-3-small"


@st.cache_data()
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """Split text into overlapping chunks."""
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    return chunks


@st.cache_data()
def get_embedding(text: str) -> list:
    """Get embedding for text using OpenAI."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding

@st.cache_resource()
def ingest_script_for_rag(script_path: str) -> chromadb.Collection:
    """
    Process a lecture script PDF and ingest it into ChromaDB.
    
    Pipeline:
    1. Load PDF
    2. Split text into chunks (chunk_size=1000, overlap=200)
    3. Embed chunks using OpenAI text-embedding-3-small
    4. Store in ChromaDB and persist to disk
    
    Args:
        script_path (str): Path to the PDF file
        
    Returns:
        chromadb.Collection: The ChromaDB collection
        
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
    
    logger.info(f"Step 1: Loading PDF from {script_path}...")
    try:
        # Extract text from PDF
        text = ""
        with open(script_path, "rb") as f:
            reader = PdfReader(f)
            logger.info(f"PDF has {len(reader.pages)} pages")
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n[Page {page_num + 1}]\n{page_text}"
    except Exception as e:
        logger.error(f"Failed to load PDF: {e}")
        raise
    
    logger.info(f"Step 2: Splitting text into chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    try:
        chunks = chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        logger.info(f"Created {len(chunks)} chunks")
    except Exception as e:
        logger.error(f"Failed to split documents: {e}")
        raise
    
    # Ensure output directory exists
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Step 3: Creating embeddings and storing in ChromaDB...")
    try:
        # Initialize ChromaDB client
        chroma_client = chromadb.PersistentClient(
            path=DB_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        collection = chroma_client.get_or_create_collection(
            name="lecture_script",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Add chunks with embeddings
        logger.info(f"Embedding and storing {len(chunks)} chunks...")
        for i, chunk in enumerate(chunks):
            if i % 10 == 0:
                logger.info(f"   Processing chunk {i + 1}/{len(chunks)}...")
            
            embedding = get_embedding(chunk)
            
            collection.add(
                ids=[f"chunk_{i}"],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": script_path, "chunk_index": i}]
            )
        
        logger.info(f"Stored all chunks in ChromaDB at {DB_DIR}")
    except Exception as e:
        logger.error(f"Failed to create vector store: {e}")
        raise
    
    logger.info("RAG ingestion pipeline completed successfully!")
    return collection

@st.cache_resource()
def load_vector_store() -> chromadb.Collection:
    """
    Load an existing vector store from disk.
    
    Returns:
        chromadb.Collection: The loaded ChromaDB collection
        
    Raises:
        FileNotFoundError: If the database doesn't exist
    """
    if not Path(DB_DIR).exists():
        logger.error(f"Vector store not found at {DB_DIR}")
        raise FileNotFoundError(f"Vector store not found at {DB_DIR}")
    
    logger.info(f"Loading vector store from {DB_DIR}...")
    try:
        chroma_client = chromadb.PersistentClient(
            path=DB_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        collection = chroma_client.get_collection(name="lecture_script")
        logger.info(f"Vector store loaded with {collection.count()} chunks")
        return collection
    except Exception as e:
        logger.error(f"Failed to load vector store: {e}")
        raise

@st.cache_data()
def retrieve_context(query: str, top_k: int = 3) -> str:
    """
    Retrieve relevant chunks from the vector store for a query.
    
    Args:
        query (str): The query text
        top_k (int): Number of top chunks to retrieve
        
    Returns:
        str: Concatenated relevant chunks as context
    """
    try:
        collection = load_vector_store()
        
        # Get embedding for query
        query_embedding = get_embedding(query)
        
        # Query the collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # Extract and concatenate documents
        if results and results["documents"]:
            context = "\n---\n".join(results["documents"][0])
            logger.info(f"Retrieved {len(results['documents'][0])} relevant chunks")
            return context
        else:
            logger.warning("No relevant chunks found")
            return ""
            
    except Exception as e:
        logger.error(f"Failed to retrieve context: {e}")
        return ""


if __name__ == "__main__":
    # Default script path
    SCRIPT_PATH = "vorlesungsskript.pdf"
    
    # Allow script path from command line
    if len(sys.argv) > 1:
        SCRIPT_PATH = sys.argv[1]
    
    try:
        ingest_script_for_rag(SCRIPT_PATH)
    except Exception as e:
        logger.error(f"RAG Ingestion failed: {e}")
        sys.exit(1)