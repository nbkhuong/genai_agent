from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
import json
import requests
import os
import time
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.language_models.llms import SimpleLLM

# Kafka setup
bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
max_retries = 10
retry_delay = 15

for attempt in range(max_retries):
    try:
        consumer = KafkaConsumer(
            "llama_queries",
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda x: json.loads(x.decode("utf-8"))
        )
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        print("Successfully connected to Kafka")
        break
    except NoBrokersAvailable:
        print(f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
        if attempt == max_retries - 1:
            raise Exception("Could not connect to Kafka after multiple attempts")
        time.sleep(retry_delay)

# Ollama server setup
ollama_server_url = f"http://{os.getenv('OLLAMA_SERVER_HOST', 'ollama:11434')}/api/generate"

# Embedding model
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Qdrant setup
qdrant_host = os.getenv("QDRANT_HOST", "qdrant:6333")
collection_name = "documents"

# Load and index documents
def index_documents():
    try:
        vectorstore = Qdrant.from_existing_collection(
            embedding=embeddings,
            collection_name=collection_name,
            url=f"http://{qdrant_host}"
        )
        print("Collection already exists, skipping indexing.")
    except:
        print("Indexing documents into Qdrant...")
        documents = []
        for filename in os.listdir("/app/documents"):
            if filename.endswith(".pdf"):
                loader = PyPDFLoader(os.path.join("/app/documents", filename))
                documents.extend(loader.load())
        
        if documents:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(documents)
            vectorstore = Qdrant.from_documents(
                documents=splits,
                embedding=embeddings,
                url=f"http://{qdrant_host}",
                collection_name=collection_name
            )
            print(f"Indexed {len(splits)} document chunks in Qdrant")
        else:
            print("No documents found to index.")
    return vectorstore

# Custom LLM class for Ollama
class OllamaLLM(SimpleLLM):
    def _call(self, prompt: str, stop=None) -> str:
        payload = {
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False,
            "max_tokens": 512,
            "temperature": 0.7
        }
        if stop:
            payload["stop"] = stop
        response = requests.post(ollama_server_url, json=payload)
        response.raise_for_status()
        return response.json()["response"]

# Warm-up Ollama server
print("Warming up Ollama server...")
requests.post(ollama_server_url, json={
    "model": "llama3.2",
    "prompt": "Ping",
    "stream": False,
    "max_tokens": 10
})

# Initialize vectorstore and RAG chain
vectorstore = index_documents()
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
llm = OllamaLLM()

prompt_template = ChatPromptTemplate.from_template(
    "Based on this context: {context}\nAnswer: {question}"
)

rag_chain = (
    {"context": retriever | (lambda docs: " ".join([d.page_content for d in docs])), "question": RunnablePassthrough()}
    | prompt_template
    | llm
    | StrOutputParser()
)

# Process queries
print("LLaMA 3.2 with LangChain and Qdrant listening for queries...")
for message in consumer:
    query = message.value["query"]
    print(f"Received query: {query}")
    
    # Generate response with RAG chain
    answer = rag_chain.invoke(query)
    
    producer.send("llama_responses", {"query": query, "response": answer})
    producer.flush()
    print(f"Sent response: {answer}")
