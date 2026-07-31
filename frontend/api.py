import requests

from config import API_URL


def register(username: str, password: str):

    response = requests.post(
        f"{API_URL}/register",
        json={
            "username": username,
            "password": password
        }
    )

    return response


def login(username: str, password: str):

    response = requests.post(
        f"{API_URL}/login",
        data={
            "username": username,
            "password": password
        }
    )

    return response

def create_project(token: str, project_name: str):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(
        f"{API_URL}/projects",
        params={
            "project_name": project_name
        },
        headers=headers
    )

    return response

def get_projects(token: str):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(
        f"{API_URL}/current_projects",
        headers=headers
    )

    return response

def upload_pdf(token: str, project_id: int, file):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    files = {
        "file": (file.name, file, "application/pdf")
    }

    response = requests.post(
        f"{API_URL}/upload",
        params={
            "project_id": project_id
        },
        headers=headers,
        files=files
    )

    return response

def get_documents(token: str, project_id: int):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(
        f"{API_URL}/documents",
        params={
            "project_id": project_id
        },
        headers=headers
    )

    return response

def chat(token: str, project_id: int, question: str):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(
        f"{API_URL}/chat",
        params={
            "project_id": project_id,
            "question": question
        },
        headers=headers
    )

    return response

def get_chat_history(token: str, project_id: int):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(
        f"{API_URL}/chathistory",
        params={
            "project_id": project_id
        },
        headers=headers
    )

    return response

def delete_chat(token: str, project_id: int):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.delete(
        f"{API_URL}/deletechat",
        params={
            "project_id": project_id
        },
        headers=headers
    )

    return response


def delete_document(token: str, project_id: int, document_id: int):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.delete(
        f"{API_URL}/deletedocuments",
        params={
            "project_id": project_id,
            "document_id": document_id
        },
        headers=headers
    )

    return response


def delete_project(token: str, project_id: int):

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.delete(
        f"{API_URL}/deleteproject",
        params={
            "project_id": project_id
        },
        headers=headers
    )

    return response