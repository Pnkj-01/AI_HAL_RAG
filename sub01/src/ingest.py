# Document Ingestion for RAG
# Reads files (PDF, TXT, MD), splits into chunks, and saves to ChromaDB

import os
import sys
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv

# Set project root path
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


class DocumentIngestor:
    # Supported file formats
    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}

    def __init__(self, persist_directory="./chroma_db"):
        load_dotenv()

        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

        self.persist_directory = persist_directory
        self.tracking_file = os.path.join(persist_directory, "ingested_files.json")

        # OpenAI embeddings model
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=self.api_key
        )

    # Calculate file hash to see if it changed
    def _get_file_hash(self, file_path):
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest()

    # Load file tracking history
    def _load_tracking_data(self):
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file, "r") as f:
                return json.load(f)
        return {}

    # Save file tracking history
    def _save_tracking_data(self, tracking_data):
        os.makedirs(self.persist_directory, exist_ok=True)
        with open(self.tracking_file, "w") as f:
            json.dump(tracking_data, f, indent=2)

    # Check if a file is already processed
    def _is_file_ingested(self, file_path):
        tracking_data = self._load_tracking_data()
        resolved_path = str(Path(file_path).resolve())

        if resolved_path not in tracking_data:
            return False

        current_hash = self._get_file_hash(resolved_path)
        return tracking_data[resolved_path] == current_hash

    # Save processed file to tracking
    def _mark_file_ingested(self, file_path):
        tracking_data = self._load_tracking_data()
        resolved_path = str(Path(file_path).resolve())

        if not os.path.exists(resolved_path):
            print(f"Warning: File not found for tracking: {resolved_path}")
            return

        file_hash = self._get_file_hash(resolved_path)
        tracking_data[resolved_path] = file_hash
        self._save_tracking_data(tracking_data)

    # Load PDF, TXT or MD files
    def load_document(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_ext = Path(file_path).suffix.lower()

        if file_ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif file_ext in {".txt", ".md"}:
            loader = TextLoader(file_path, encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file type: {file_ext}. Supported: {self.SUPPORTED_EXTENSIONS}")

        documents = loader.load()

        # Add file name and type to document metadata
        for doc in documents:
            doc.metadata["source_file"] = Path(file_path).name
            doc.metadata["file_type"] = file_ext

        print(f"Loaded {len(documents)} page(s)/section(s) from {Path(file_path).name}")
        return documents

    # Split documents into smaller text chunks
    def chunk_documents(self, documents, chunk_size=500, chunk_overlap=50):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(documents)
        print(f"Created {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})")
        return chunks

    # Remove old chunks for a modified file
    def _delete_file_chunks(self, file_name):
        if not os.path.exists(self.persist_directory):
            return

        vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )

        try:
            results = vectorstore.get(where={"source_file": file_name})
            if results and results.get("ids"):
                vectorstore.delete(ids=results["ids"])
                print(f"Deleted {len(results['ids'])} old chunks from {file_name}")
        except Exception as e:
            print(f"Warning: Could not delete old chunks: {e}")

    # Save chunks into ChromaDB
    def create_or_update_vector_store(self, chunks):
        print("Generating embeddings and storing in ChromaDB...")

        if os.path.exists(self.persist_directory):
            vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            vectorstore.add_documents(chunks)
            print(f"Added {len(chunks)} chunks to existing vector store")
        else:
            vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            print(f"Created new vector store with {len(chunks)} chunks")

        print(f"Persisted to: {self.persist_directory}")
        return vectorstore

    # Ingest one file
    def ingest_file(self, file_path, chunk_size=500, chunk_overlap=50, force=False):
        resolved_path = str(Path(file_path).resolve())
        file_name = Path(resolved_path).name

        already_done = self._is_file_ingested(resolved_path)
        tracking_data = self._load_tracking_data()
        is_tracked = resolved_path in tracking_data

        # Skip if already done and not forced
        if not force and already_done:
            print(f"Skipping {file_name} (already ingested)")
            return None

        # Re-ingest modified file
        if is_tracked and not already_done:
            print(f"\nRe-ingesting modified file: {file_name}")
            self._delete_file_chunks(file_name)
        else:
            print(f"\nIngesting: {file_name}")

        # Step 1: Load
        documents = self.load_document(resolved_path)

        # Step 2: Split
        chunks = self.chunk_documents(documents, chunk_size, chunk_overlap)

        # Step 3: Embed and store
        vectorstore = self.create_or_update_vector_store(chunks)

        # Step 4: Save record
        self._mark_file_ingested(resolved_path)

        print("Ingestion complete.\n")
        return vectorstore

    # Ingest all files in a folder
    def ingest_folder(self, folder_path, chunk_size=500, chunk_overlap=50, extensions=None, force=False):
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        allowed_exts = extensions or self.SUPPORTED_EXTENSIONS
        print(f"\nScanning folder: {folder_path}")

        files_to_process = []
        for ext in allowed_exts:
            files_to_process.extend(folder.glob(f"*{ext}"))

        if not files_to_process:
            print(f"No supported files found in {folder_path}")
            print(f"   Supported extensions: {allowed_exts}")
            return self.load_existing_vectorstore()

        print(f"Found {len(files_to_process)} file(s): {[f.name for f in files_to_process]}\n")

        ingested_count = 0
        skipped_count = 0

        for fpath in files_to_process:
            result = self.ingest_file(str(fpath), chunk_size, chunk_overlap, force)
            if result is not None:
                ingested_count += 1
            else:
                skipped_count += 1

        print("\nFolder ingestion summary:")
        print(f"  Ingested: {ingested_count} file(s)")
        print(f"  Skipped: {skipped_count} file(s) (already processed)\n")

        return self.load_existing_vectorstore()

    # Load existing Chroma database
    def load_existing_vectorstore(self):
        if not os.path.exists(self.persist_directory):
            raise FileNotFoundError(
                f"Vector store not found at {self.persist_directory}. Please run ingestion first."
            )

        vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )
        print(f"Loaded existing vector store from {self.persist_directory}")
        return vectorstore

    def get_ingested_files(self):
        return self._load_tracking_data()

    def clear_tracking(self):
        if os.path.exists(self.tracking_file):
            os.remove(self.tracking_file)
            print("Cleared file tracking data")


# Alias for backward compatibility
PDFIngestor = DocumentIngestor


def main():
    ingestor = DocumentIngestor(persist_directory="./chroma_db")
    ingestor.ingest_folder("./data")

    print("\nIngested files:")
    for file_path in ingestor.get_ingested_files():
        print(f"  - {Path(file_path).name}")


if __name__ == "__main__":
    main()
