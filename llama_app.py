import os
import time
import json
import requests
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.llms import Ollama  # Use built-in Ollama LLM

# Kafka setup with retries
def initialize_kafka():
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    max_retries = 10
    retry_delay = 15

    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                "llama_queries",
                bootstrap_servers=bootstrap_servers,
                auto_offset_reset="latest",
                value_deserializer=lambda x: json.loads(x.decode("utf-8"))
            )
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            print("Successfully connected to Kafka")
            return consumer, producer
        except NoBrokersAvailable as e:
            print(f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise Exception("Could not connect to Kafka after multiple attempts")
            time.sleep(retry_delay)

# Index documents into Qdrant
def index_documents(embeddings, qdrant_host, collection_name):
    try:
        vectorstore = Qdrant.from_existing_collection(
            embedding=embeddings,
            collection_name=collection_name,
            url=f"http://{qdrant_host}"
        )
        print("Loaded existing Qdrant collection.")
    except Exception as e:
        print(f"No existing collection found or error ({e}), indexing documents...")
        documents = []
        docs_dir = "/app/documents"
        if not os.path.exists(docs_dir):
            print(f"Documents directory {docs_dir} does not exist.")
            return None

        for filename in os.listdir(docs_dir):
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(docs_dir, filename)
                try:
                    loader = PyPDFLoader(file_path)
                    documents.extend(loader.load())
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")

        if not documents:
            print("No documents found to index.")
            return None

        # Split and index documents
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(documents)
        try:
            vectorstore = Qdrant.from_documents(
                documents=splits,
                embedding=embeddings,
                url=f"http://{qdrant_host}",
                collection_name=collection_name
            )
            print(f"Indexed {len(splits)} document chunks into Qdrant")
        except Exception as e:
            print(f"Error indexing documents into Qdrant: {e}")
            return None

    return vectorstore

def main():
    # Environment variables
    ollama_host = os.getenv("OLLAMA_SERVER_HOST", "ollama:11434")
    ollama_base_url = f"http://{ollama_host}"
    qdrant_host = os.getenv("QDRANT_HOST", "qdrant:6333")
    collection_name = "documents"

    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Warm up Ollama server with the custom model
    print("Warming up Ollama server...")
    try:
        llm_temp = Ollama(base_url=ollama_base_url, model="llama32-3B-instruct")
        response = llm_temp.invoke("Ping", max_tokens=10)
        print(f"Ollama server is ready. Warm-up response: {response}")
    except Exception as e:
        print(f"Error warming up Ollama: {e}")

    # Initialize Kafka
    consumer, producer = initialize_kafka()

    # Initialize vectorstore and RAG chain
    vectorstore = index_documents(embeddings, qdrant_host, collection_name)
    if vectorstore is None:
        print("Failed to initialize vectorstore. Exiting.")
        return

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    llm = Ollama(
        base_url=ollama_base_url,
        model="llama32-3B-instruct",  # Updated model name
        temperature=0.7,
        num_predict=512  # Equivalent to max_tokens
    )

    prompt_template = ChatPromptTemplate.from_template(
        "Based on this context: {context}\nAnswer: {question}"
    )

    rag_chain = (
        {"context": retriever | (lambda docs: " ".join([d.page_content for d in docs])), "question": RunnablePassthrough()}
        | prompt_template
        | llm
        | StrOutputParser()
    )

    # Process Kafka messages
    print("LLaMA 32-3B-instruct with LangChain and Qdrant listening for queries...")
    msg = None
    for message in consumer:
        try:
            query = message.value.get("query", "")
            if not query:
                print("Received empty query, skipping.")
                continue

            print(f"Received query: {query}")
            answer = rag_chain.invoke(query)
            producer.send("llama_responses", {"query": query, "response": answer})
            producer.flush()
            print(f"Sent response: {answer}")
            break
        except Exception as e:
            print(f"Error processing query '{query}': {e}")

if __name__ == "__main__":
    main()
    