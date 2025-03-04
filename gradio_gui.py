import streamlit as st
import time

# Page setup
st.set_page_config(page_title="Chat App", layout="centered")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Function to generate response
def generate_response(prompt):
    # Replace this with your actual response generation logic
    time.sleep(0.5)  # Simulate processing delay
    return f"I received: '{prompt}'. How can I help further?"

# Display header
st.header("Chat Application")

# Display existing chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message (appears on the right by default)
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Generate response
    response = generate_response(prompt)
    
    # Display assistant response (appears on the left by default)
    with st.chat_message("assistant"):
        st.markdown(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})