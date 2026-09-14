import streamlit as st

from api_updated_quiz_difficulty import (
    login,
    register,
    create_project,
    get_projects,
    upload_pdf,
    get_documents,
    chat,
    get_chat_history,
    delete_chat,
    delete_document,
    delete_project,
    generate_flashcard,
    generate_quiz
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
                    st.session_state.pop("flashcard_question", None)
                    st.session_state.pop("flashcard_answer", None)
                    st.session_state.pop("flashcard_answer_visible", None)
                    st.session_state.pop("flashcard_window_number", None)
                    st.session_state.pop("quiz_questions", None)
                    st.session_state.pop("quiz_document_id", None)
                    st.session_state.pop("quiz_document_name", None)

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

        col1, col2 = st.columns([8, 1])

        with col1:
            st.subheader(project["project_name"])

        with col2:
            if st.button("🗑️ Project"):
                response = delete_project(token, project["project_id"])
                if response.status_code == 200:
                    st.success("Project deleted!")
                    st.session_state.pop("selected_project", None)
                    st.session_state.messages = []
                    st.session_state.pop("flashcard_question", None)
                    st.session_state.pop("flashcard_answer", None)
                    st.session_state.pop("flashcard_answer_visible", None)
                    st.session_state.pop("flashcard_window_number", None)
                    st.session_state.pop("quiz_questions", None)
                    st.session_state.pop("quiz_document_id", None)
                    st.session_state.pop("quiz_document_name", None)
                    st.rerun()
                else:
                    st.error(response.json()["detail"])

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

                    left, right = st.columns([8,1])

                    with left:
                        st.write(f"📄 {document['filename']}")

                    with right:
                        if st.button("🗑️", key=f"delete_doc_{document['document_ID']}"):
                            r = delete_document(token, project["project_id"], document["document_ID"])
                            if r.status_code == 200:
                                st.success("Document deleted!")
                                st.rerun()
                            else:
                                st.error(r.json()["detail"])

        st.write("---")

        # ---------------- FLASHCARDS ---------------- #

        st.subheader("🧠 Flashcards")

        flashcard_document_options = {
            document["filename"]: document["document_ID"]
            for document in documents
        }

        if flashcard_document_options:

            selected_flashcard_filename = st.selectbox(
                "Choose a document",
                list(flashcard_document_options.keys()),
                key="flashcard_document"
            )

            selected_flashcard_document_id = flashcard_document_options[
                selected_flashcard_filename
            ]

            if st.button(
                "✨ Generate Flashcard",
                key="generate_flashcard"
            ):

                with st.spinner("Generating flashcard..."):

                    flashcard_response = generate_flashcard(
                        token,
                        project["project_id"],
                        selected_flashcard_document_id
                    )

                if flashcard_response.status_code == 200:

                    flashcard_data = flashcard_response.json()

                    st.session_state.flashcard_question = (
                        flashcard_data["flashcard"]["question"]
                    )

                    st.session_state.flashcard_window_number = (
                        flashcard_data["window number"]
                    )
                    st.session_state.flashcard_answer = (
                        flashcard_data["flashcard"]["answer"]
                    )
                    st.session_state.flashcard_answer_visible = False

                else:

                    st.error(
                        flashcard_response.json().get(
                            "detail",
                            "Failed to generate flashcard."
                        )
                    )

            if "flashcard_question" in st.session_state:

                st.markdown("### Question")
                if "flashcard_window_number" in st.session_state:
                    st.caption(
                        f"Source window: {st.session_state.flashcard_window_number}"
                    )
                st.write(st.session_state.flashcard_question)

                if not st.session_state.get(
                    "flashcard_answer_visible",
                    False
                ):

                    if st.button(
                        "👁️ Show Answer",
                        key="show_answer_button"
                    ):
                        st.session_state.flashcard_answer_visible = True
                        st.rerun()

                else:

                    st.markdown("### Answer")
                    st.write(st.session_state.flashcard_answer)

                    if st.button(
                        "🔄 Generate Another",
                        key="generate_another_flashcard"
                    ):

                        with st.spinner(
                            "Generating another flashcard..."
                        ):

                            flashcard_response = generate_flashcard(
                                token,
                                project["project_id"],
                                selected_flashcard_document_id
                            )

                        if flashcard_response.status_code == 200:

                            flashcard_data = flashcard_response.json()

                            st.session_state.flashcard_question = (
                                flashcard_data["flashcard"]["question"]
                            )

                            st.session_state.flashcard_window_number = (
                                flashcard_data["window number"]
                            )
                            st.session_state.flashcard_answer = (
                                flashcard_data["flashcard"]["answer"]
                            )
                            st.session_state.flashcard_answer_visible = False
                            st.rerun()

                        else:

                            st.error(
                                flashcard_response.json().get(
                                    "detail",
                                    "Failed to generate flashcard."
                                )
                            )

        else:
            st.info("Upload a document to generate flashcards.")


        st.write("---")

        # ---------------- QUIZZES ---------------- #

        st.subheader("📝 Quiz")

        quiz_document_options = {
            document["filename"]: document["document_ID"]
            for document in documents
        }

        if quiz_document_options:

            selected_quiz_filename = st.selectbox(
                "Choose a document",
                list(quiz_document_options.keys()),
                key="quiz_document"
            )

            selected_quiz_document_id = quiz_document_options[
                selected_quiz_filename
            ]

            number_of_questions = st.number_input(
                "Number of questions",
                min_value=1,
                max_value=20,
                value=5,
                step=1,
                key="quiz_number_of_questions"
            )

            difficulty = st.selectbox(
                "Difficulty",
                ["easy", "medium", "tough"],
                index=1,
                format_func=lambda level: level.capitalize(),
                key="quiz_difficulty"
            )

            if st.button(
                "✨ Generate Quiz",
                key="generate_quiz"
            ):

                with st.spinner("Generating quiz..."):

                    quiz_response = generate_quiz(
                        token,
                        project["project_id"],
                        selected_quiz_document_id,
                        number_of_questions,
                        difficulty
                    )

                if quiz_response.status_code == 200:

                    st.session_state.quiz_questions = (
                        quiz_response.json()
                    )

                    st.session_state.quiz_document_id = (
                        selected_quiz_document_id
                    )

                    st.session_state.quiz_document_name = (
                        selected_quiz_filename
                    )

                    st.rerun()

                else:

                    st.error(
                        quiz_response.json().get(
                            "detail",
                            "Failed to generate quiz."
                        )
                    )

            # Display the currently generated quiz.
            if "quiz_questions" in st.session_state:

                st.markdown("### Generated Quiz")

                for question_number, item in enumerate(
                    st.session_state.quiz_questions,
                    start=1
                ):

                    quiz_question = item["quiz_question"]

                    st.markdown(
                        f"**Question {question_number}:** "
                        f"{quiz_question['question']}"
                    )

                    for option_number, option in enumerate(
                        quiz_question["options"]
                    ):

                        option_letter = chr(
                            ord("A") + option_number
                        )

                        st.write(
                            f"**{option_letter}.** {option}"
                        )

                    if st.button(
                        f"Show Answer {question_number}",
                        key=f"show_quiz_answer_{question_number}"
                    ):

                        st.success(
                            f"Correct Answer: "
                            f"{quiz_question['correct_answer']}"
                        )

                        st.info(
                            f"Explanation: "
                            f"{quiz_question['explanation']}"
                        )

                    st.write("")

        else:

            st.info("Upload a document to generate a quiz.")

        left, right = st.columns([6,1])

        with left:
            st.subheader("💬 Chat")

        with right:
            if st.button("🗑️ Chat"):
                r = delete_chat(token, project["project_id"])
                if r.status_code == 200:
                    st.session_state.messages = []
                    st.success("Chat cleared!")
                    st.rerun()
                else:
                    st.error(r.json()["detail"])

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
