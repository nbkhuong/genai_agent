# import os
# import time
# import json
# import requests
# import logging
# from kafka import KafkaConsumer, KafkaProducer
# from kafka.errors import NoBrokersAvailable
# from langchain_community.document_loaders import PyPDFLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import Qdrant
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnablePassthrough
# from langchain_ollama import OllamaLLM  # Use built-in Ollama LLM

# # Kafka setup with retries
# def initialize_kafka():
#     bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
#     max_retries = 10
#     retry_delay = 2

#     for attempt in range(max_retries):
#         try:
#             consumer = KafkaConsumer(
#                 "llama_queries",
#                 bootstrap_servers=bootstrap_servers,
#                 auto_offset_reset="latest",
#                 enable_auto_commit=True,
#                 value_deserializer=lambda x: json.loads(x.decode("utf-8"))
#             )
#             producer = KafkaProducer(
#                 bootstrap_servers=bootstrap_servers,
#                 value_serializer=lambda v: json.dumps(v).encode("utf-8")
#             )
#             print("Successfully connected to Kafka")
#             return consumer, producer
        
#         except NoBrokersAvailable as e:
#             print(f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}): {e}")
#             if attempt == max_retries - 1:
#                 raise Exception("Could not connect to Kafka after multiple attempts")
#             time.sleep(retry_delay)

# # Index documents into Qdrant
# def index_documents(embeddings, qdrant_host, collection_name):
#     try:
#         vectorstore = Qdrant.from_existing_collection(
#             embedding=embeddings,
#             collection_name=collection_name,
#             url=f"http://{qdrant_host}"
#         )
#         print("Loaded existing Qdrant collection.")
#     except Exception as e:
#         print(f"No existing collection found or error ({e}), indexing documents...")
#         documents = []
#         docs_dir = "/app/documents"
#         if not os.path.exists(docs_dir):
#             print(f"Documents directory {docs_dir} does not exist.")
#             return None

#         for filename in os.listdir(docs_dir):
#             if filename.lower().endswith(".pdf"):
#                 file_path = os.path.join(docs_dir, filename)
#                 try:
#                     loader = PyPDFLoader(file_path)
#                     documents.extend(loader.load())
#                 except Exception as e:
#                     print(f"Error loading {file_path}: {e}")

#         if not documents:
#             print("No documents found to index.")
#             return None

#         # Split and index documents
#         text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
#         splits = text_splitter.split_documents(documents)
#         try:
#             vectorstore = Qdrant.from_documents(
#                 documents=splits,
#                 embedding=embeddings,
#                 url=f"http://{qdrant_host}",
#                 collection_name=collection_name
#             )
#             print(f"Indexed {len(splits)} document chunks into Qdrant")
#         except Exception as e:
#             print(f"Error indexing documents into Qdrant: {e}")
#             return None

#     return vectorstore

# def main():
#     # Environment variables
#     ollama_host = os.getenv("OLLAMA_SERVER_HOST", "ollama:11434")
#     ollama_base_url = f"http://{ollama_host}"
#     qdrant_host = os.getenv("QDRANT_HOST", "qdrant:6333")
#     collection_name = "documents"

#     # Initialize embeddings
#     embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

#     # Warm up Ollama server with the custom model
#     print("Warming up Ollama server...")
#     try:
#         llm_temp = OllamaLLM(base_url=ollama_base_url, model="llama32-3B-instruct")
#         response = llm_temp.invoke("Ping", max_tokens=10)
#         print(f"Ollama server is ready. Warm-up response: {response}")
#     except Exception as e:
#         print(f"Error warming up Ollama: {e}")

#     # Initialize vectorstore and RAG chain
#     vectorstore = index_documents(embeddings, qdrant_host, collection_name)
#     if vectorstore is None:
#         print("Failed to initialize vectorstore. Exiting.")
#         return

#     retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
#     llm = OllamaLLM(
#         base_url=ollama_base_url,
#         model="llama32-3B-instruct"
#     )

#     prompt_template = ChatPromptTemplate.from_template(
#         "Based on this context: {context}\nAnswer: {question}"
#     )

#     rag_chain = (
#         {"context": retriever | (lambda docs: " ".join([d.page_content for d in docs])), "question": RunnablePassthrough()}
#         | prompt_template
#         | llm
#         | StrOutputParser()
#     )

#     logging.info("SFSAFSF")

#     # Initialize Kafka
#     consumer, producer = initialize_kafka()

#     # Kafka message processing loop
#     print("Starting Kafka consumer to read messages continuously...")
#     for message in consumer:
#         try:
#             query = message.value.get("query", "")
#             print(f"Received query: {query}")
#             if not query:
#                 continue

#             response = rag_chain.invoke(query)
#             response_message = {
#                 "query": query,
#                 "response": response,
#                 "timestamp": time.time()
#             }
#             producer.send("llama_responses", response_message)
#             producer.flush()
#             print("Response sent to Kafka topic 'llama_responses'")
#         except Exception as e:
#             print(f"Error processing message: {e}")
#             continue

# if __name__ == "__main__":
#     main()
    

import os
import json
import time
from kafka import KafkaConsumer, KafkaProducer
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

def setup_kafka():
    """Set up Kafka consumer and producer with simpler retry logic"""
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.178.28:9092")
    retries = 5
    
    for i in range(retries):
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
            print("Connected to Kafka successfully")
            return consumer, producer
        except Exception as e:
            print(f"Kafka connection attempt {i+1}/{retries} failed: {e}")
            if i < retries - 1:
                time.sleep(2)
    
    raise Exception("Failed to connect to Kafka")

def load_documents():
    """Load PDF documents from the documents directory"""
    documents = []
    docs_dir = "/app/documents"
    
    if not os.path.exists(docs_dir):
        print(f"Documents directory {docs_dir} not found")
        return []
    
    for filename in os.listdir(docs_dir):
        if filename.endswith(".pdf"):
            try:
                file_path = os.path.join(docs_dir, filename)
                loader = PyPDFLoader(file_path)
                documents.extend(loader.load())
                print(f"Loaded {filename}")
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    return documents

def create_vectorstore(documents, embeddings):
    """Create or load vectorstore from documents"""
    if not documents:
        print("No documents to index")
        return None
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)
    
    # Create vectorstore
    qdrant_host = os.getenv("QDRANT_HOST", "qdrant:6333")
    collection_name = "documents"
    
    try:
        # Try to load existing collection
        vectorstore = Qdrant.from_existing_collection(
            embedding=embeddings,
            collection_name=collection_name,
            url=f"http://{qdrant_host}"
        )
        print("Using existing Qdrant collection")
    except Exception:
        # Create new collection if loading fails
        vectorstore = Qdrant.from_documents(
            documents=splits,
            embedding=embeddings,
            url=f"http://{qdrant_host}",
            collection_name=collection_name
        )
        print(f"Created new Qdrant collection with {len(splits)} chunks")
    
    return vectorstore

def main():
    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Load documents and create vectorstore
    documents = load_documents()
    vectorstore = create_vectorstore(documents, embeddings)
    if not vectorstore:
        print("Failed to initialize vectorstore. Exiting.")
        return
    
    # Initialize LLM
    ollama_host = os.getenv("OLLAMA_SERVER_HOST", "ollama:11434")
    llm = OllamaLLM(
        base_url=f"http://{ollama_host}",
        model="llama32-3B-instruct"
    )
    
    # Set up retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    # Create prompt template
    prompt = PromptTemplate(
        template="Based on this context: {context}\nAnswer: {question}",
        input_variables=["context", "question"]
    )
    
    # Set up Kafka
    try:
        consumer, producer = setup_kafka()
    except Exception as e:
        print(f"Failed to set up Kafka: {e}")
        return
    
    # Process messages
    print("Starting to listen for queries...")
    for message in consumer:
        try:
            # Get query from message
            query = message.value.get("query", "")
            if not query:
                continue
            print(f"Processing query: {query}")
            
            # Retrieve relevant documents
            docs = retriever.get_relevant_documents(query)
            context = " ".join([doc.page_content for doc in docs])
            
            # Generate answer
            formatted_prompt = prompt.format(context=context, question=query)
            response = llm.invoke(formatted_prompt)
            
            # Send response
            response_message = {
                "query": query,
                "response": response,
                "timestamp": time.time()
            }
            producer.send("llama_responses", response_message)
            print("Sent response to Kafka")
            
        except Exception as e:
            print(f"Error processing message: {e}")

if __name__ == "__main__":
    main()