import streamlit as st
import requests
import json
from streamlit_chat import message
from gtts import gTTS
import io
import uuid
st.set_page_config( initial_sidebar_state="expanded")


# Initialize session state variables
if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "stream_complete" not in st.session_state:
    st.session_state.stream_complete = True

# Function to create a new conversation
def new_conversation():
    conversation_id = str(uuid.uuid4())
    st.session_state.conversations[conversation_id] = []
    st.session_state.current_conversation_id = conversation_id
    requests.post(f"http://localhost:8000/reset_conversation/{conversation_id}")

# Create a new conversation if none exists
if not st.session_state.conversations:
    new_conversation()

# Sidebar for conversation history
with st.sidebar:
    st.title("Your AI BUDDY")
    
    # New Chat button
    if st.button("New Chat"):
        new_conversation()
        st.experimental_rerun()
    
    # Display conversation history
    st.subheader("Chat History")
    for conv_id, messages in st.session_state.conversations.items():
        if messages:
            # Display the first user message as the conversation title
            title = next((m[1] for m in messages if m[0] == "user"), "New Chat")
            if st.button(f"{title[:30]}...", key=f"conv_{conv_id}"):
                st.session_state.current_conversation_id = conv_id
                st.experimental_rerun()



# Function to send a message to the API and retrieve the response
def send_message_to_api(message, history, session_id):
    url = "http://localhost:8000/stream"
    response = requests.post(url, json={"message": message, "history": history, "session_id": session_id}, stream=True)
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                try:
                    response_json = json.loads(line.decode('utf-8'))
                    yield response_json.get("content", "")
                except ValueError:
                    st.write("Error: Invalid response format")
                    yield "Error: Invalid response format"
    else:
        yield f"Error: {response.status_code} - {response.reason}"

# Function to convert text to speech
def text_to_speech(text, lang='hi'):
    tts = gTTS(text=text, lang=lang, slow=False)
    audio_bytes = io.BytesIO()
    tts.write_to_fp(audio_bytes)
    audio_bytes.seek(0)
    return audio_bytes

# Function to play audio
def play_audio_response(text, lang='en'):
    with st.spinner('Loading...'):
        audio_bytes = text_to_speech(text, lang)
    st.audio(audio_bytes, format="audio/mp3")

# Display messages for the current conversation
current_messages = st.session_state.conversations[st.session_state.current_conversation_id]
for i, (role, content) in enumerate(current_messages):
    message(content, is_user=(role == "user"), key=f"{role}_{i}")
    if role == "assistant":
        if st.button(f"🔊", key=f"listen_{i}"):
            play_audio_response(content, lang='hi')

# User input
user_input = st.chat_input("Type your message here...", key="user_input")

# Send button to submit the message
if user_input and st.session_state.stream_complete:
    st.session_state.stream_complete = False
    # Add user message to current conversation
    current_messages.append(("user", user_input))
    message(user_input, is_user=True, key=f"user_{len(current_messages)}")
    
    # Prepare history for API
    history = [(role, content) for role, content in current_messages[:-1]]
    
    # Placeholder for assistant response
    response_placeholder = st.empty()
    
    # Call the API and stream the assistant response
    full_response = ""
    for response_chunk in send_message_to_api(user_input, history, st.session_state.current_conversation_id):
        full_response += response_chunk
        response_placeholder.markdown(full_response + "▌")
    
    # Add assistant response to current conversation
    current_messages.append(("assistant", full_response))
    
    # Replace placeholder with final message
    response_placeholder.empty()
    message(full_response, is_user=False, key=f"assistant_{len(current_messages)}")
    st.session_state.stream_complete = True
    st.experimental_rerun()

# Check for session ID in JavaScript (you can keep this part if needed)
st.markdown(
    """
    <script>
        var session_id = sessionStorage.getItem('session_id');
        if (session_id === null) {
            session_id = '%s';
            sessionStorage.setItem('session_id', session_id);
        }
        if (session_id !== '%s') {
            sessionStorage.setItem('session_id', '%s');
            window.location.reload();
        }
    </script>
    """ % (st.session_state.current_conversation_id, st.session_state.current_conversation_id, st.session_state.current_conversation_id),
    unsafe_allow_html=True
)