import json
import time
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import NoBrokersAvailable

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = "192.168.178.28:9092"  # Replace with your Kafka server address
QUERY_TOPIC = "llama_queries"
RESPONSE_TOPIC = "llama_responses"

# Initialize Kafka producer and consumer
def initialize_kafka():
    max_retries = 10
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            consumer = KafkaConsumer(
                RESPONSE_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset="latest",  # Start reading from the latest message
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode("utf-8")))
            print("Successfully connected to Kafka")
            return producer, consumer
        except NoBrokersAvailable as e:
            print(f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise Exception("Could not connect to Kafka after multiple attempts")
            time.sleep(retry_delay)

# Send a query to the Kafka topic
def send_query(producer, query):
    try:
        producer.send(QUERY_TOPIC, {"query": query})
        producer.flush()
        print(f"Sent query: {query}")
    except Exception as e:
        print(f"Error sending query: {e}")

# Listen for responses from the Kafka topic
def listen_for_responses(consumer):
    print("Listening for responses...")
    for message in consumer:
        response = message.value
        print(f"Received response: {response} \n")
        break

# Main function
def main():
    producer, consumer = initialize_kafka()

    # Example: Send a query and listen for responses
    try:
        while True:
            # Send a query
            query = input("Enter your query (or type 'exit' to quit): ")
            if query.lower() == "exit":
                break
            send_query(producer, query)

            # Listen for responses
            listen_for_responses(consumer)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        producer.close()
        consumer.close()

if __name__ == "__main__":
    main()