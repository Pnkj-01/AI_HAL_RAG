# Main RAG System
# Simple interface for ingesting documents and asking questions

import os
import sys
from pathlib import Path

# Set project root path
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from src.ingest import DocumentIngestor
from src.query import RAGQueryEngine


class RAGSystem:
    def __init__(self, persist_directory="./chroma_db", top_k=3):
        self.persist_directory = persist_directory
        self.top_k = top_k
        self.ingestor = DocumentIngestor(persist_directory=persist_directory)
        self.query_engine = None

    # Ingest a single file (PDF, TXT, MD)
    def ingest_file(self, file_path, chunk_size=500, chunk_overlap=50, force=False):
        self.ingestor.ingest_file(file_path, chunk_size, chunk_overlap, force)
        self.query_engine = None  # Reload query engine after new file

    # Ingest all documents in a folder
    def ingest_folder(self, folder_path, chunk_size=500, chunk_overlap=50, force=False):
        self.ingestor.ingest_folder(folder_path, chunk_size, chunk_overlap, force=force)
        self.query_engine = None  # Reload query engine after new files

    # Backward compatibility helper
    def ingest_pdf(self, pdf_path, chunk_size=500, chunk_overlap=50):
        self.ingest_file(pdf_path, chunk_size, chunk_overlap)

    # Check if database exists
    def is_vectorstore_ready(self):
        return os.path.exists(self.persist_directory)

    # Ask question using the RAG pipeline
    def ask(self, question, verbose=False):
        if not self.is_vectorstore_ready():
            raise RuntimeError(
                "Vector store not found. Please ingest documents first using ingest_folder() or ingest_file()"
            )

        if self.query_engine is None:
            self.query_engine = RAGQueryEngine(
                persist_directory=self.persist_directory,
                top_k=self.top_k
            )

        return self.query_engine.query(question, verbose=verbose)

    # Get matching chunks without generating text
    def get_relevant_chunks(self, question, k=None):
        if not self.is_vectorstore_ready():
            raise RuntimeError(
                "Vector store not found. Please ingest documents first using ingest_folder() or ingest_file()"
            )

        if self.query_engine is None:
            self.query_engine = RAGQueryEngine(
                persist_directory=self.persist_directory,
                top_k=self.top_k
            )

        return self.query_engine.get_relevant_chunks(question, k)

    # List files that have been ingested
    def get_ingested_files(self):
        return self.ingestor.get_ingested_files()


def main():
    print("\nRAG System Demo\n")

    rag = RAGSystem(persist_directory="./chroma_db", top_k=3)

    print("Ingesting documents from ./data folder...\n")
    rag.ingest_folder("./data")

    ingested = rag.get_ingested_files()
    if ingested:
        print(f"\nTotal ingested files: {len(ingested)}")
        for file_path in ingested:
            print(f"   - {Path(file_path).name}")

    print("\nReady for queries!\n")

    questions = [
        "What is DataMind?",
        "How can I get support?",
        "What are the pricing options?"
    ]

    print("\nRunning example queries:\n")
    for i, q in enumerate(questions, 1):
        print(f"\nQuery {i}: {q}")
        try:
            result = rag.ask(q, verbose=False)
            print(f"\nAnswer:\n{result['answer']}")
            print("\nSources:")
            for j, src in enumerate(result["sources"], 1):
                print(f"  [{j}] Page {src['page']}")
        except Exception as e:
            print(f"Error: {e}")

    print("\nDemo complete.\n")


if __name__ == "__main__":
    main()
