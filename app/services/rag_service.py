import os
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.services.document_processor import pdf_processor

class RAGEngine:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        self.llm = OllamaLLM(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0
        )
        self.vector_store = None
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        """Initialize or load the ChromaDB vector store."""
        self.vector_store = Chroma(
            persist_directory=settings.CHROMA_DB_PATH,
            embedding_function=self.embeddings,
            collection_name="documind_collection"
        )

    async def process_document(self, file_path: str):
        """Extract text, embed, and store in vector database."""
        documents = pdf_processor.extract_text(file_path)
        if documents:
            self.vector_store.add_documents(documents)
            print(f"Indexed {len(documents)} chunks from {file_path}")

    async def ask(self, question: str) -> str:
        """Query the documents using the RAG chain."""
        if not self.vector_store:
            return "Vector store not initialized. Please upload a document first."
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 5}),
            return_source_documents=True
        )
        
        result = await qa_chain.ainvoke({"query": question})
        return result["result"]

    def _format_docs(self, docs):
        return "\n\n".join(doc.page_content for doc in docs)

    async def ask_stream(self, question: str):
        if not self.vector_store:
            yield "Vector store not initialized. Please upload a document first."
            return
            
        yield "__STATUS__🔍 Searching your documents... (This can take 30-60s)__STATUS_END__"
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 2})
        
        # 1. Manually retrieve the documents first so we have the citations
        docs = await retriever.ainvoke(question)
        
        # 2. Yield the metadata as a JSON string prefixed by a custom delimiter.
        import json
        sources_metadata = [
            {"page": getattr(doc.metadata, "get", lambda k: doc.metadata[k])("page", "?"), 
             "source": getattr(doc.metadata, "get", lambda k: doc.metadata[k])("source", "?"),
             "content": doc.page_content[:150] + "..."} 
            for doc in docs
        ]
        
        yield f"__SOURCES__{json.dumps(sources_metadata)}__SOURCES_END__"
        yield "__STATUS__🤖 AI is thinking of the best answer...__STATUS_END__"
        
        # 3. Stream the LLM response using the retrieved context
        prompt = PromptTemplate.from_template("""
        You are an intelligent Document Conversation Assistant.

        Your job is to answer user questions using ONLY the provided document context.
        Your responses must be clear, structured, and optimized for a chat-based UI.

        -----------------------------------
        RESPONSE FORMAT (STRICT)
        -----------------------------------

        ### 📌 Answer
        - Provide a direct and concise answer
        - Maximum 3–4 bullet points
        - Do NOT include unnecessary explanation

        ### 📖 Explanation
        - Expand the answer slightly for clarity
        - Use bullet points (•)
        - Keep it easy to scan (no long paragraphs)

        ### 📍 Source
        - Include:
        • Page number (if available)
        • Short exact quotes from the document
        - Keep quotes brief (1–2 lines max)

        ### 💡 Follow-up
        - Suggest 2 relevant next questions the user might ask

        -----------------------------------
        BEHAVIOR RULES
        -----------------------------------

        - Use ONLY the provided context
        - Do NOT hallucinate or assume anything
        - If answer is not found, respond with:
        "⚠️ The answer is not available in the provided document."

        - Detect user intent and adapt:

        IF user asks:
        → Summary → give high-level overview (3 bullets max)
        → List / Extract → return clean bullet list
        → Explain → simplify the concept 2-3 sentences
        → Compare → return a table format
        → Definitions → short and precise

        -----------------------------------
        STYLE RULES
        -----------------------------------

        - Be professional and minimal
        - Avoid conversational filler (no "Sure", "Here’s...")
        - Use clean Markdown structure
        - Prefer bullets over paragraphs
        - Make output UI-friendly and readable

        -----------------------------------
        CONTEXT
        -----------------------------------
        {context}

        -----------------------------------
        QUESTION
        -----------------------------------
        {question}

        -----------------------------------
        ANSWER
        -----------------------------------
        """)
        
        context_text = self._format_docs(docs)
        
        rag_chain = prompt | self.llm | StrOutputParser()
        
        try:
            async for chunk in rag_chain.astream({"context": context_text, "question": question}):
                yield chunk
        except Exception as e:
            # Prevent server hang on disconnection and notify the client
            print(f"Streaming interrupted: {e}")
            yield f"\n\n⚠️ **Connection interrupted.** This often happens if the server restarts or Ollama is under heavy load. Please try your question again."

rag_engine = RAGEngine()
