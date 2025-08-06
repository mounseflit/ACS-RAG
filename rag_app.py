import streamlit as st
import time
import os
import json
import tempfile
from file_processor import process_file

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.foundation_models.schema import TextChatParameters

st.set_page_config(page_title="RAG Chatbot with Multi-File Support", layout="wide")

st.title("RAG Chatbot with Multi-File Support 🤖📁")

# Sidebar for credentials and settings
with st.sidebar:
    st.header("🔧 Settings")
    
    # Try to get credentials from secrets first, otherwise use input fields
    api_key = st.text_input("Watsonx AI API Key *", type="password")
    try:
        project_id = st.secrets.get("project_id", "") or st.text_input("Project ID *")
        url = st.secrets.get("url", "") or st.text_input("Endpoint URL *")
    except:
        project_id = st.text_input("Project ID *")
        url = st.text_input("Endpoint URL *")


    # project_type = st.selectbox("Project Type", options=["Text",  "Vision"])
    # model_vision_options = {
    #     "Google": [
    #         "google/flan-t5-xl"
    #     ],
    #     "IBM Granite": [
    #         "ibm/granite-vision-3-2-2b"
    #     ],
    #     "Meta (LLaMA)": [
    #         "meta-llama/llama-3-2-11b-vision-instruct",
    #         "meta-llama/llama-3-2-90b-vision-instruct",
    #         "meta-llama/llama-guard-3-11b-vision"
    #     ],
    #     "Mistral": [
    #         "mistralai/pixtral-12b"
    #     ]
    # }


    model_text_options = {
        "IBM Granite": [
            "ibm/granite-3-2-8b-instruct",
            "ibm/granite-3-2b-instruct",
            "ibm/granite-3-3-8b-instruct",
            "ibm/granite-3-8b-instruct"
        ],
        "Meta (LLaMA)": [
            "meta-llama/llama-3-2-1b-instruct"
            "meta-llama/llama-3-2-3b-instruct",
            "meta-llama/llama-3-3-70b-instruct",
            "meta-llama/llama-3-405b-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct-fp8"
        ],
        "Mistral": [
            "mistralai/mistral-large",
            "mistralai/mistral-medium-2505",
            "mistralai/mistral-small-3-1-24b-instruct-2503"
        ]
    }

    # Select appropriate model options based on project type
    # if project_type == "Vision":
    #     current_options = model_vision_options
    # else:  # Text
    #     current_options = model_text_options

    current_options = model_text_options

    model_provider = st.selectbox("Model Provider", options=list(current_options.keys()))
    model_id = st.selectbox("Model ID *", options=current_options.get(model_provider, []))


# File upload section
st.header("📁 Upload Files")
uploaded_files = st.file_uploader(
    "Choose files to upload",
    accept_multiple_files=True,
    type=['txt', 'pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg'],
    help="Supported formats: TXT, PDF, DOCX, XLSX, PNG, JPG, JPEG"
)

# Initialize session state for processed files and chat history
if "processed_files" not in st.session_state:
    st.session_state.processed_files = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Process uploaded files
if uploaded_files:
    st.subheader("📄 Processing Files...")
    
    for uploaded_file in uploaded_files:
        # Check if file is already processed
        if uploaded_file.name not in [f["metadata"]["file_name"] for f in st.session_state.processed_files]:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                # Determine file type
                file_extension = uploaded_file.name.split('.')[-1].lower()
                if file_extension in ['txt']:
                    file_type = 'txt'
                elif file_extension in ['pdf']:
                    file_type = 'pdf'
                elif file_extension in ['docx']:
                    file_type = 'docx'
                elif file_extension in ['xlsx']:
                    file_type = 'xlsx'
                elif file_extension in ['png', 'jpg', 'jpeg']:
                    file_type = 'image'
                else:
                    st.error(f"Unsupported file type: {file_extension}")
                    continue
                
                # Process file
                try:
                    processed_data = process_file(
                        tmp_file_path, 
                        file_type
                    )
                    
                    if processed_data:
                        st.session_state.processed_files.extend(processed_data)
                        st.success(f"✅ Processed {uploaded_file.name} - {len(processed_data)} chunks created")
                    else:
                        st.warning(f"⚠️ No content extracted from {uploaded_file.name}")
                        
                except Exception as e:
                    st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
                
                # Clean up temporary file
                os.unlink(tmp_file_path)

# Display processed files summary
if st.session_state.processed_files:
    st.subheader("📊 Processed Files Summary")
    file_summary = {}
    for item in st.session_state.processed_files:
        file_name = item["metadata"]["file_name"]
        if file_name not in file_summary:
            file_summary[file_name] = 0
        file_summary[file_name] += 1
    
    for file_name, chunk_count in file_summary.items():
        st.write(f"📄 {file_name}: {chunk_count} chunks")

# Chat interface
st.header("💬 Chat with Your Documents")

# Display past messages
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input for new user message
user_input = st.chat_input("Ask your question here...")

if user_input:
    if not all([api_key, project_id, model_id]):
        st.error("❗ Please fill in all required fields in the sidebar (marked with *)")
        st.stop()
    
    if not st.session_state.processed_files:
        st.error("❗ Please upload and process some files first")
        st.stop()

    # Add user message to history
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        # Simple retrieval: find relevant chunks based on keyword matching
        # In a production system, this would use vector embeddings and similarity search
        relevant_chunks = []
        query_words = user_input.lower().split()
        
        for item in st.session_state.processed_files:
            content_lower = item["content"].lower()
            relevance_score = sum(1 for word in query_words if word in content_lower)
            if relevance_score > 0:
                relevant_chunks.append((item, relevance_score))
        
        # Sort by relevance and take top 3
        relevant_chunks.sort(key=lambda x: x[1], reverse=True)
        top_chunks = [chunk[0] for chunk in relevant_chunks[:3]]
        
        # Build context from relevant chunks
        context = ""
        if top_chunks:
            context = "Based on the following information from your documents:\n\n"
            for i, chunk in enumerate(top_chunks):
                context += f"Document {i+1} ({chunk['metadata']['file_name']}):\n{chunk['content']}\n\n"
        
        # Prepare messages for the model
        system_message = "You are a helpful assistant that answers questions based on the provided document context. If the context doesn't contain relevant information, say so clearly."
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"{context}\n\nQuestion: {user_input}"}
        ]

        credentials = Credentials(url=url, api_key=api_key)
        params = TextChatParameters(temperature=0.7)
        model = ModelInference(
            model_id=model_id,
            credentials=credentials,
            project_id=project_id,
            params=params
        )

        start_time = time.time()
        response = model.chat(messages=messages)
        end_time = time.time()
        
        content = response["choices"][0]["message"]["content"]
        elapsed = end_time - start_time
        tokens = len(content.split())
        speed = tokens / elapsed if elapsed > 0 else 0

        # Add assistant message to history
        st.session_state.chat_history.append({"role": "assistant", "content": content})
        with st.chat_message("assistant"):
            st.markdown(content)

        st.info(f"⏱ Time: {elapsed:.2f}s | 🧮 Tokens: {tokens} | ⚡ Speed: {speed:.2f} tokens/s | 📄 Used {len(top_chunks)} document chunks")

    except Exception as e:
        st.error(f"Error: {str(e)}")

# Clear chat button
if st.button("🗑️ Clear Chat History"):
    st.session_state.chat_history = []
    st.rerun()

# Clear processed files button
if st.button("🗑️ Clear Processed Files"):
    st.session_state.processed_files = []
    st.rerun()

