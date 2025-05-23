import streamlit as st
from util import load_faiss_index, update_index_with_file, generate_answer, get_history, save_history


st.set_page_config(page_title="NUST Bank RAG Chatbot", layout="wide")
st.title("🤖 NUST Bank Assistant — RAG Chatbot")
st.markdown("Upload documents or ask any question related to **NUST Bank Accounts**.")


# Initialize chat history
if "history" not in st.session_state:
    st.session_state.history = []


# File uploader
uploaded_file = st.file_uploader("📄 Upload a document", type=["txt", "pdf", "xlsx"])
if uploaded_file is not None:
    success = update_index_with_file(uploaded_file)
    if success:
        st.success("✅ Document successfully indexed.")
    else:
        st.warning("⚠️ Document could not be indexed (empty or unsupported content).")


# Ask a question
user_input = st.text_input("💬 Ask a question:")
submit_clicked = st.button("Submit", disabled=not user_input)

if submit_clicked and user_input:
    try:
        with st.spinner("🔍 Generating answer..."):
            context, answer = generate_answer(user_input)

        # Chat-style UI (Streamlit 1.25+)
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            st.markdown(answer)

        # Show context
        with st.expander("📚 Context Retrieved"):
            if "---" in context:
                for pair in context.split("---"):
                    q_and_a = pair.strip().split("\n")
                    for line in q_and_a:
                        if line.startswith("Q:") or line.startswith("A:"):
                            st.markdown(line)
                    st.markdown("---")
            else:
                st.markdown(context)

        # Save history
        st.session_state.history.append((user_input, answer))
        save_history(st.session_state.history)

    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")


# Show chat history
with st.expander("📜 Chat History", expanded=False):
    history = get_history()
    if history:
        for q, a in history:
            st.markdown(f"**Q:** {q}")
            st.markdown(f"**A:** {a}")
    else:
        st.markdown("No chat history yet.")


# Optional: Clear chat history
if st.button("🗑️ Clear Chat History"):
    st.session_state.history = []
    save_history([])
    st.experimental_rerun()
