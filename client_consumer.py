import json
import time
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import NoBrokersAvailable
import streamlit as st

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

        return response

# Main function
def main():
    # Page setup
    st.set_page_config(page_title="Chat App", layout="centered")

    # Initialize chat history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display header
    st.header("Let's Chat :3")

    # Display existing chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Initialize Kafka once and store in session state
    if "producer" not in st.session_state or "consumer" not in st.session_state:
        try:
            st.session_state.producer, st.session_state.consumer = initialize_kafka()
        except Exception as e:
            st.error(f"Failed to connect to Kafka: {e}")
            return

    if query := st.chat_input("Type your message here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": query})
        
        # Display user message (appears on the right by default)
        with st.chat_message("user"):
            st.markdown(query)
        
        # Send query and show a spinner while waiting for response
        with st.spinner("Waiting for response..."):
            send_query(st.session_state.producer, query)
            response = listen_for_responses(st.session_state.consumer)
        
        # Get response content (handle different possible formats)
        response_content = response.get("response", response) if isinstance(response, dict) else response
        
        # Display assistant response (appears on the left by default)
        with st.chat_message("assistant"):
            st.markdown(response_content)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response_content})

if __name__ == "__main__":
    main()