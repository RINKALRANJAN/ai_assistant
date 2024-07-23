from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
import json

app = FastAPI()

class StreamRequest(BaseModel):
    message: str
    session_id: str

# Store memory objects keyed by session_id
memory_store = {}

def get_memory(session_id):
    if session_id not in memory_store:
        memory_store[session_id] = ConversationBufferWindowMemory(k=3, memory_key="chat_history", return_messages=True)
    return memory_store[session_id]

chat = ChatGroq(
    temperature=0,
    model="llama3-70b-8192",
    api_key="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"
)
# prompt 
# system = "आप एक चार्टर्ड अकाउंटेंट विशेषज्ञ हैं। चार्टर्ड अकाउंटेंसी से संबंधित सभी प्रश्नों का उत्तर हिंदी में 50 शब्दों में दें। अगर उपयोगकर्ता विस्तार से समझाने के लिए कहता है, तो आप अधिक शब्दों का उपयोग कर सकते हैं। उत्तर सरल और स्पष्ट हों ताकि उपयोगकर्ता आसानी से समझ सके। उदाहरणों का उपयोग करें यदि आवश्यक हो, और उपयोगकर्ता के अनुरोध पर गहराई में जाएं। अगर उपयोगकर्ता अभिवादन (जैसे नमस्ते, हेलो) करता है, तो उसे उचित अभिवादन से जवाब दें।"
system ="your are a friendly conversation robot,सभी प्रश्नों का उत्तर हिंदी में 50 शब्दों में दें। "
human = "{text}"
prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "{text}"),
    ("human", "Previous conversation:\n{chat_history}\nHuman: {text}")
])
# api endpoint for getting the response with streaming
@app.post("/stream")
async def stream(request: StreamRequest):
    session_id = request.session_id
    memory = get_memory(session_id)

    conversation = memory.load_memory_variables({})
    human_message = request.message
    chat_history = conversation.get("chat_history", [])

    # Format the prompt
    messages = prompt.format_messages(text=human_message, chat_history=chat_history)

    # Generate the response
    response_chunks = chat.stream(messages)
    
    async def generate():
        full_response = ""
        for chunk in response_chunks:
            full_response += chunk.content
            yield json.dumps({"content": chunk.content}) + "\n"
        
        # Update memory with new message and response
        memory.save_context({"text": human_message}, {"output": full_response})

    return StreamingResponse(generate(), media_type="application/json")

# Reset conversation endpoint
@app.post("/reset_conversation/{session_id}")
async def reset_conversation(session_id: str):
    if session_id in memory_store:
        del memory_store[session_id]
    return {"message": "Conversation reset successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
