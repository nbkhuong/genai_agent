# LLM-Based Document QA System

A scalable document question-answering system using local LLMs, vector search, and a message queue architecture.

## Project Overview

This project implements a document question-answering system with the following components:

* **Ollama** : Runs the LLama-3 language model locally
* **Qdrant** : Vector database for document storage and similarity search
* **Kafka** : Message queue for handling query requests and responses
* **LLama App** : Core application that processes documents and answers queries

The system loads PDF documents, creates vector embeddings, and allows users to ask questions about the document content. It uses a retrieval-augmented generation (RAG) approach to provide accurate answers based on the document context.

## Architecture

```
+-------------+     +--------------+      +----------+
|             |     |              |      |          |
| Client App  +---->+ Kafka Queue +----->+ LLama App|
| (External)  |     | (Messages)   |      | (RAG)    |
|             |     |              |      |          |
+-------------+     +--------------+      +-----+----+
                                                |
                                                v
                    +------------+       +-----+------+
                    |            |       |            |
                    | Qdrant     |<----->+ Ollama LLM |
                    | (Vectors)  |       | (Model)    |
                    |            |       |            |
                    +------------+       +------------+
```

## Prerequisites

* Docker and Docker Compose
* NVIDIA GPU with appropriate drivers
* At least 16GB of RAM
* 10GB+ of free disk space

## Project Setup

1. Clone this repository:

```bash
git clone https://github.com/nbkhuong/genai_agent.git
cd genai_agent
```

2. Create necessary directories:

```bash
mkdir -p kafka_data qdrant_data documents models
```

3. Place your PDF documents in the `documents` directory:

```bash
cp your-documents/*.pdf documents/
```

4. Update the Kafka advertised listener in `docker-compose.yml` to match your machine's IP address:

```yaml
KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://your-ip-address:9092
```

5. Start the services:

```bash
docker-compose up -d
```

6. The first run will download the LLama model, which may take some time depending on your internet connection.

## Usage

The system listens for queries on the Kafka topic `llama_queries` and publishes responses to `llama_responses`.

To send a query, publish a JSON message to the `llama_queries` topic:

```json
{
  "query": "What are the key points in the document?"
}
```

Responses will be available on the `llama_responses` topic with this structure:

```json
{
  "query": "What are the key points in the document?",
  "response": "The document discusses...",
  "timestamp": 1646732456.789
}
```

## Configuration

### Environment Variables

The following environment variables can be set in the docker-compose.yml file:

* `KAFKA_BOOTSTRAP_SERVERS`: Kafka servers (default: kafka:9092)
* `OLLAMA_SERVER_HOST`: Ollama server address (default: ollama:11434)
* `QDRANT_HOST`: Qdrant server address (default: qdrant:6333)

### Model Configuration

By default, the system uses the `llama32-3B-instruct` model. To change this, update the model name in the `main()` function:

```python
llm = OllamaLLM(
    base_url=f"http://{ollama_host}",
    model="your-preferred-model"
)
```
