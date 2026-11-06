# Question Answering using ChromaDB and OpenAI
# Retrieves context chunks and answers questions without hallucinating

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Set project root path
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate


class RAGQueryEngine:
    def __init__(self, persist_directory="./chroma_db", top_k=3):
        load_dotenv()

        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

        self.persist_directory = persist_directory
        self.top_k = top_k

        # Embeddings model
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=self.api_key
        )

        # Chat model (temperature 0 keeps it factual)
        self.llm = ChatOpenAI(
            model="gpt-5-nano",
            temperature=0,
            openai_api_key=self.api_key
        )

        # Load Chroma database
        self.vectorstore = self._load_vectorstore()

        # Build QA chain
        self.qa_chain = self._create_qa_chain()

    def _load_vectorstore(self):
        if not os.path.exists(self.persist_directory):
            raise FileNotFoundError(
                f"Vector store not found at {self.persist_directory}. Please run ingestion first using ingest.py"
            )

        return Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )

    def _create_qa_chain(self):
        # Strict instructions so the model does not guess
        template = """You are a helpful AI assistant answering questions based on the provided context.

Use the following pieces of context to answer the question at the end. If you don't know the answer based on the context, just say that you don't know - don't try to make up an answer.

When answering:
1. Be concise and direct
2. Cite the page number(s) from the source when relevant
3. If the context doesn't contain the answer, clearly state that

Context:
{context}

Question: {question}

Answer:"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": self.top_k}
        )

        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )

    # Ask a question and get answer with sources
    def query(self, question, verbose=False):
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        result = self.qa_chain.invoke({"query": question})
        answer = result["result"]
        source_docs = result["source_documents"]

        sources = []
        for doc in source_docs:
            sources.append({
                "content": doc.page_content,
                "page": doc.metadata.get("page", "N/A"),
                "source": doc.metadata.get("source", "N/A")
            })

        if verbose:
            print("\n" + "=" * 60)
            print(f"Question: {question}")
            print("=" * 60 + "\n")

            print("Retrieved Context:")
            print("-" * 60)
            for i, src in enumerate(sources, 1):
                print(f"\n[Chunk {i}] Page {src['page']}:")
                content = src["content"]
                print(content[:300] + "..." if len(content) > 300 else content)

            print("\n" + "=" * 60)
            print("Answer:")
            print("=" * 60 + "\n")
            print(answer)
            print()

        return {
            "answer": answer,
            "sources": sources,
            "question": question
        }

    # Fetch relevant chunks without asking the LLM
    def get_relevant_chunks(self, question, k=None):
        num_chunks = k or self.top_k
        docs = self.vectorstore.similarity_search(question, k=num_chunks)

        chunks = []
        for doc in docs:
            chunks.append({
                "content": doc.page_content,
                "page": doc.metadata.get("page", "N/A"),
                "source": doc.metadata.get("source", "N/A")
            })
        return chunks


def main():
    print("Initializing RAG Query Engine...")
    engine = RAGQueryEngine(persist_directory="./chroma_db", top_k=3)
    print("Query engine ready!\n")

    questions = [
        "What is DataMind?",
        "How can I contact support?",
        "What are the main features?"
    ]

    for q in questions:
        engine.query(q, verbose=True)
        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
