import streamlit as st

from api import (
    login,
    register,
    create_project,
    get_projects,
    upload_pdf,
    get_documents,
    chat,
    get_chat_history
)

from auth import save_token, get_token, logout

st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="📚",
    layout="wide"
)

if "page" not in st.session_state:
    st.session_state.page = "login"

st.title("📚 AI Research Assistant")

# ---------------- LOGIN ---------------- #

if st.session_state.page == "login":

    st.subheader("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        response = login(username, password)

        if response.status_code == 200:
            save_token(response.json()["access_token"])
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error(response.json()["detail"])

    st.write("---")

    if st.button("Register Here"):
        st.session_state.page = "register"
        st.rerun()

# ---------------- REGISTER ---------------- #

elif st.session_state.page == "register":

    st.subheader("Create Account")

    username = st.text_input("Choose Username")
    password = st.text_input("Choose Password", type="password")
    confirm = st.text_input("Confirm Password", type="password")

    if st.button("Register"):

        if password != confirm:
            st.error("Passwords do not match.")
        else:
            response = register(username, password)

            if response.status_code == 200:
                st.success("Registration Successful!")
            else:
                st.error(response.json()["detail"])

    st.write("---")

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# ---------------- DASHBOARD ---------------- #

else:

    token = get_token()

    st.sidebar.title("📚 AI Research Assistant")

    if st.sidebar.button("➕ New Project"):
        st.session_state.create_project = True

    st.sidebar.write("---")
    st.sidebar.subheader("Your Projects")

    response = get_projects(token)

    if response.status_code == 200:

        projects = response.json()

        if len(projects) == 0:
            st.sidebar.info("No projects created.")
        else:
            for project in projects:

                if st.sidebar.button(
                    f"📁 {project['project_name']}",
                    key=project["project_id"]
                ):

                    st.session_state.selected_project = project
                    st.session_state.create_project = False

                    history_response = get_chat_history(
                        token,
                        project["project_id"]
                    )

                    st.session_state.messages = []

                    if history_response.status_code == 200:

                        history = history_response.json()["history"]

                        for msg in history:
                            st.session_state.messages.append(
                                {
                                    "role": msg["role"],
                                    "content": msg["message"],
                                    "citations": []
                                }
                            )

                    st.session_state.current_project = project["project_id"]
                    st.rerun()

    st.sidebar.write("---")

    if st.sidebar.button("Logout"):
        logout()
        st.session_state.page = "login"
        st.rerun()

    st.header("Workspace")

    if st.session_state.get("create_project", False):

        st.subheader("Create New Project")

        project_name = st.text_input("Project Name")

        if st.button("Create"):

            response = create_project(token, project_name)

            if response.status_code == 200:
                st.success("Project Created!")
                st.session_state.create_project = False
                st.rerun()
            else:
                st.error(response.json()["detail"])

    elif "selected_project" in st.session_state:

        project = st.session_state.selected_project

        st.subheader(project["project_name"])
        st.write("---")

        st.subheader("📄 Upload PDF")

        uploaded_file = st.file_uploader(
            "Choose a PDF",
            type=["pdf"]
        )

        if uploaded_file is not None and st.button("Upload PDF"):

            with st.spinner("Uploading PDF..."):
                response = upload_pdf(
                    token,
                    project["project_id"],
                    uploaded_file
                )

            if response.status_code == 200:
                st.success("PDF uploaded successfully!")
                st.rerun()
            else:
                st.error(response.json()["detail"])

        st.write("---")

        st.subheader("📂 Uploaded Documents")

        response = get_documents(token, project["project_id"])

        if response.status_code == 200:

            documents = response.json()

            if len(documents) == 0:
                st.info("No documents uploaded.")
            else:
                for document in documents:
                    st.write(f"📄 {document['filename']}")

        st.write("---")
        st.subheader("💬 Chat")

        if "messages" not in st.session_state:
            st.session_state.messages = []

        if (
            "current_project" not in st.session_state
            or st.session_state.current_project != project["project_id"]
        ):

            history_response = get_chat_history(
                token,
                project["project_id"]
            )

            st.session_state.messages = []

            if history_response.status_code == 200:

                history = history_response.json()["history"]

                for msg in history:
                    st.session_state.messages.append(
                        {
                            "role": msg["role"],
                            "content": msg["message"],
                            "citations": []
                        }
                    )

            st.session_state.current_project = project["project_id"]

        for message in st.session_state.messages:

            with st.chat_message(message["role"]):

                st.markdown(message["content"])

                if message["role"] == "assistant":

                    citations = message.get("citations", [])

                    if citations:
                        st.markdown("**Sources**")
                        for citation in citations:
                            st.write(
                                f"📄 {citation['Filename']} (Page {citation['Page Number']})"
                            )

        question = st.chat_input(
            "Ask anything about your uploaded documents..."
        )

        if question:

            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": question
                }
            )

            response = chat(
                token,
                project["project_id"],
                question
            )

            if response.status_code == 200:

                data = response.json()

                answer = data["response"]
                citations = data["citations"]

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "citations": citations
                    }
                )

                st.rerun()

            else:
                st.error(response.json()["detail"])

    else:

        st.subheader("Welcome!")
        st.write(
            "Create a project or choose an existing one from the sidebar."
        )
