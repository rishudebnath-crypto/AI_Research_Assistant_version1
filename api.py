import requests

BASE_URL = "http://127.0.0.1:8000"


def upload_pdf(uploaded_file):
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "application/pdf"
        )
    }

    return requests.post(
        f"{BASE_URL}/upload",
        files=files
    )


def chat(question):

    return requests.post(
        f"{BASE_URL}/chat",
        params={
            "question": question
        }
    )


def get_chat_history():

    return requests.get(
        f"{BASE_URL}/chathistory"
    )


def delete_chat():

    return requests.delete(
        f"{BASE_URL}/deletechat"
    )


def get_documents():

    return requests.get(
        f"{BASE_URL}/documents"
    )

def delete_document(document_id: int):

    return requests.delete(
        f"{BASE_URL}/deletedocuments",
        params={
            "document_id": document_id
        }
    )
