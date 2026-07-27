import streamlit as st
from api import *

st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="📚",
    layout="wide"
)

# ==========================================================
# Session State
# ==========================================================

if "messages" not in st.session_state:

    st.session_state.messages = []

    response = get_chat_history()

    if response.status_code == 200:

        history = response.json()["history"]

        for msg in history:

            role = "assistant" if msg["role"] == "ai" else "user"

            st.session_state.messages.append(
                {
                    "role": role,
                    "content": msg["message"]
                }
            )

# Used only so Streamlit doesn't repeatedly POST the
# same selected file on every rerun.
if "last_uploaded_filename" not in st.session_state:
    st.session_state.last_uploaded_filename = None

# ==========================================================
# Sidebar
# ==========================================================

with st.sidebar:

    st.title("📚 AI Research Assistant")

    st.markdown("### Upload Research Paper")

    uploaded_pdf = st.file_uploader(
        "Choose a PDF",
        type=["pdf"]
    )

    if (
        uploaded_pdf is not None
        and uploaded_pdf.name != st.session_state.last_uploaded_filename
    ):

        with st.spinner("Uploading..."):

            response = upload_pdf(uploaded_pdf)

        if response.status_code == 200:

            st.success("PDF uploaded successfully.")

            st.session_state.last_uploaded_filename = uploaded_pdf.name

            st.rerun()

        elif response.status_code == 409:

            st.warning("This document already exists.")

            st.session_state.last_uploaded_filename = uploaded_pdf.name

        else:

            st.error(response.json()["detail"])

    st.divider()

    st.subheader("📚 Document Library")

    response = get_documents()

    if response.status_code == 200:

        docs = response.json()

        if len(docs) == 0:

            st.info("No uploaded documents.")

        else:

            for doc in docs:

                with st.expander(
                    f"📄 {doc['filename']}",
                    expanded=False
                ):

                    st.write(
                        f"**Document ID :** {doc['document_ID']}"
                    )

                    if "chunks" in doc:

                        st.write(
                            f"**Chunks :** {doc['chunks']}"
                        )

                    st.write(
                        "**Status :** Indexed ✅"
                    )

                    if st.button(
                        "🗑 Delete Document",
                        key=f"delete_{doc['document_ID']}"
                    ):

                        response = delete_document(
                            doc["document_ID"]
                        )

                        if response.status_code == 200:

                            st.success("Document deleted.")

                            if (
                                st.session_state.last_uploaded_filename
                                == doc["filename"]
                            ):

                                st.session_state.last_uploaded_filename = None

                            st.rerun()

                        else:

                            st.error(response.json()["detail"])

    st.divider()

    if st.button("🗑 Clear Chat"):

        response = delete_chat()

        if response.status_code == 200:

            st.session_state.messages = []

            st.rerun()

# ==========================================================
# Main Page
# ==========================================================

st.title("🤖 AI Research Assistant")

st.caption(
    "Upload research papers and ask questions across your documents."
)

# ==========================================================
# Chat History
# ==========================================================

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])

# ==========================================================
# Chat Input
# ==========================================================

question = st.chat_input(
    "Ask a question about your uploaded papers..."
)

if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):

        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner("Thinking..."):

            response = chat(question)

        if response.status_code == 200:

            data = response.json()

            answer = data["response"]

            citations = data["citations"]

            st.markdown(answer)

            if citations:

                with st.expander("📖 Citations"):

                    for citation in citations:

                        st.markdown(
                            f"- **{citation['Filename']}** "
                            f"(Page {citation['Page Number']})"
                        )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )

        else:

            st.error("Unable to generate a response.")