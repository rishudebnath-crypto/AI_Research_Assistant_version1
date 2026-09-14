from fastapi import UploadFile
from langchain_core.documents import Document
from langchain_classic.document_loaders import PyPDFLoader
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from schemas import PaperSummary
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import sqlite3
from typing import List
import os

# make a folder "documents" containing all uploaded PDF files if not exists yet
DATA_DIR = "data"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "documents"), exist_ok=True)

# loading environment variables of LLM API keys
load_dotenv()

llm = ChatGroq(model='llama-3.3-70b-versatile')

# using hugging face embedding model for creating embeddings of chunks
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# using chroma vector database
vectorstore = Chroma(
    embedding_function=embedding_model,
    persist_directory=os.path.join(DATA_DIR, "RAG_vectorstore_db"),
    collection_name='research_papers'
)
def get_connection():
    conn = sqlite3.connect(os.path.join(DATA_DIR, "research_assistant.db"))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_projects(user_id: int, project_name: str) -> int:

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            INSERT INTO projects (project_name, user_id) VALUES (?, ?)
        """

       cursor.execute(SQL_query, (project_name, user_id))
       conn.commit()
 
       project_id = cursor.lastrowid
       conn.close()
       return project_id

def get_projects(user_id: int):

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            SELECT project_id, project_name FROM projects WHERE user_id = ? ORDER BY created_at DESC
        """

       cursor.execute(SQL_query, (user_id,))
       rows = cursor.fetchall()
       projects = []
       for row in rows:
              projects.append({
                     'project_id': row[0],
                     'project_name': row[1]
              })

       conn.close()
       return projects

def delete_project(project_id: int, user_id: int):

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query1 = """
            SELECT filepath FROM documents WHERE project_id = ?
        """

       cursor.execute(SQL_query1, (project_id,))
       files = cursor.fetchall()

       for (filepath,) in files:
              if os.path.exists(filepath):
                     os.remove(filepath)

       vectorstore.delete(
              where = {
                     'project_id': project_id
              }
       ) 
       SQL_query2 = """
            DELETE FROM projects WHERE project_id = ? AND user_id = ?
        """

       cursor.execute(SQL_query2, (project_id, user_id))
       conn.commit()
       conn.close()

# saving pdf filename and path into documents table and filepath in documents folder
async def save_pdf_file(file: UploadFile, project_id: int):
        filename = file.filename
        conn = get_connection()
        cursor = conn.cursor()

        SQL_query1 = """
            INSERT INTO documents (project_id, filename, filepath) VALUES (?, ?, ?)
        """

        cursor.execute(SQL_query1, (project_id, filename, ""))
        document_id = cursor.lastrowid

        filepath = os.path.join(DATA_DIR, "documents", f"{document_id}.pdf")

        with open(filepath, 'wb') as pdf:
                        pdf.write(await file.read())

        SQL_query2 = """
            UPDATE documents SET filepath = ? WHERE document_id = ? AND project_id = ?
        """

        cursor.execute(SQL_query2, (filepath, document_id, project_id))
        conn.commit()
        conn.close()

        return document_id, filepath, filename

def load_and_chunk_pdf_file(project_id, document_id, filepath, filename) -> List[Document]:

    loader = PyPDFLoader(filepath)
    docs = loader.load()
    for doc in docs:
            doc.metadata['filename'] = filename
            doc.metadata['document_id'] = document_id
            doc.metadata['project_id'] = project_id

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    values = []
    for i, chunk in enumerate(chunks):
           chunk.metadata['chunk_index'] = i
           page_number = chunk.metadata.get('page', -1)
           chunk_text = chunk.page_content
           row = (document_id, page_number, i, chunk_text)
           values.append(row)

    conn = get_connection()
    cursor = conn.cursor()
    SQL_query = """
        INSERT INTO chunks (document_id, page_number, chunk_index, chunk_text) VALUES (?, ?, ?, ?)
    """

    cursor.executemany(SQL_query, values)
    conn.commit()
    conn.close()
    return chunks

def update_vectorstore(chunks: List[Document]):

       vectorstore.add_documents(chunks)

def load_chat_history(project_id: int):

       history = []
       conn = get_connection()
       cursor = conn.cursor()
       SQL_query = """
            SELECT role, message FROM chat_history WHERE project_id = ? ORDER BY message_id
        """

       cursor.execute(SQL_query, (project_id,))
       rows = cursor.fetchall()

       for role, message in rows:

              if role == 'user':
                     history.append(HumanMessage(content=message))

              elif role == 'ai':
                     history.append(AIMessage(content=message))

       conn.close() 
       return history

def get_chat_history(project_id: int):

        conn = get_connection()
        cursor = conn.cursor()
        SQL_query = """
            SELECT role, message FROM chat_history WHERE project_id = ? ORDER BY message_id
        """
        cursor.execute(SQL_query, (project_id,))
        rows = cursor.fetchall()
        history = []
        for row in rows:
                r = {
                        'role': row[0], 
                        'message': row[1]
                    }
                history.append(r)

        conn.close()
        return history

def save_chat_history(project_id: int, user_input: str, ai: str) -> None:

       rows = [(project_id, 'user', user_input), (project_id, 'ai', ai)]
       conn = get_connection()
       cursor = conn.cursor()
       SQL_query = """
            INSERT INTO chat_history (project_id, role, message) VALUES (?, ?, ?)
        """   

       cursor.executemany(SQL_query, rows)
       conn.commit()
       conn.close() 

def get_documents(project_id: int):

        conn = get_connection()
        cursor = conn.cursor()
        SQL_query = """
            SELECT document_id, filename FROM documents WHERE project_id = ? ORDER BY document_id
        """    

        cursor.execute(SQL_query, (project_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

def delete_document(project_id: int, document_id):

        conn = get_connection()
        cursor = conn.cursor()
        SQL_query = """
            SELECT filepath FROM documents WHERE document_id = ? AND project_id = ?
        """

        cursor.execute(SQL_query, (document_id, project_id))
        rows = cursor.fetchone()
        if rows is None:
                conn.close()
                raise ValueError(f'Document with document ID {document_id} not found')

        filepath = rows[0]
        if os.path.exists(filepath):
                os.remove(filepath)
        
        SQL_query_child = """   
            DELETE FROM chunks WHERE document_id = ?
        """
        SQL_query_parent = """
            DELETE FROM documents WHERE document_id = ? AND project_id = ?
        """

        cursor.execute(SQL_query_child, (document_id,))
        cursor.execute(SQL_query_parent, (document_id, project_id))
        conn.commit()
        conn.close()

        vectorstore.delete(
    where={
        "$and": [
            {"document_id": document_id},
            {"project_id": project_id}
            ]
        }
        )


def document_exists(project_id: int, filename: str):

    conn = get_connection()
    cursor = conn.cursor()

    SQL_query = """
        SELECT document_id
        FROM documents
        WHERE project_id = ?
        AND filename = ?
    """

    cursor.execute(SQL_query, (project_id, filename))

    row = cursor.fetchone()

    conn.close()

    return row is not None       

def username_exists(username: str) -> bool:

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            SELECT id FROM users WHERE username = ?
        """

       cursor.execute(SQL_query, (username,))
       rows = cursor.fetchone()
       conn.close()
       return rows is not None

def create_user(username: str, hashed_password: str):

       conn = get_connection()
       cursor = conn.cursor()
       SQL_query = """  
            INSERT INTO users (username, password_hash) VALUES (?, ?)
        """

       cursor.execute(SQL_query, (username, hashed_password))
       conn.commit()
       conn.close()

def get_user_by_username(username: str):

       conn = get_connection()
       cursor = conn.cursor()
       SQL_query = """  
            SELECT id, username, password_hash FROM users WHERE username = ?
        """

       cursor.execute(SQL_query, (username,))
       rows = cursor.fetchone()
       if rows is None:
              conn.close()
              return None

       conn.close()

       return {
              'user_id': rows[0],
              'username': rows[1],
              'password_hash': rows[2]
       }

def verify_project_owner(project_id: int, user_id: int) -> bool:

    conn = get_connection()
    cursor = conn.cursor()

    SQL_query = """
        SELECT user_id
        FROM projects
        WHERE project_id = ?
    """

    cursor.execute(SQL_query, (project_id,))
    row = cursor.fetchone()

    conn.close()

    if row is None:
        return False

    return row[0] == user_id
       
def get_document_chunks(document_id: int) -> List[str]:

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            SELECT chunk_text FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC
        """ 

       cursor.execute(SQL_query, (document_id,))
       rows = cursor.fetchall()
       conn.close()
       return [row[0] for row in rows]  

def document_belongs_to_project(project_id: int, document_id: int) -> bool:

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            SELECT project_id FROM documents WHERE document_id = ?
        """

       cursor.execute(SQL_query, (document_id,))
       row = cursor.fetchone()
       conn.close() 

       if row is None:
              return False
       
       return row[0] == project_id
        
def summary_exists(document_id: int, summary_length: str) -> bool:

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            SELECT summary_json FROM summaries WHERE document_id = ? AND summary_length = ?
        """
       cursor.execute(SQL_query, (document_id, summary_length))
       row = cursor.fetchone()
       conn.close()
       return row is not None

def save_summary(document_id: int, summary_length: str, summary: PaperSummary) -> None:

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            INSERT INTO summaries (document_id, summary_length, summary_json) VALUES (?, ?, ?)
        """

       cursor.execute(SQL_query, (document_id, summary_length, summary.model_dump_json()))
       conn.commit()
       conn.close()

def get_summary(document_id: int, summary_length: str) -> PaperSummary:

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            SELECT summary_json FROM summaries WHERE document_id = ? AND summary_length = ?
        """

       cursor.execute(SQL_query, (document_id, summary_length))
       row = cursor.fetchone()
       conn.close()
       if row is None:
              raise ValueError('Summary not found')
       
       summary = PaperSummary.model_validate_json(row[0])
       return summary

def local_summary_exists(document_id: int, window_number: int) -> bool:

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            SELECT local_summary FROM local_summaries WHERE document_id = ? AND window_number = ?
        """

       cursor.execute(SQL_query, (document_id, window_number))
       row = cursor.fetchone()
       conn.close()

       return row is not None

def save_local_summary(document_id: int, window_number: int, local_summary: str):

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            INSERT INTO local_summaries (document_id, window_number, local_summary) VALUES (?, ?, ?)
        """

       cursor.execute(SQL_query, (document_id, window_number, local_summary))
       conn.commit()
       conn.close()

def get_local_summary(document_id: int, window_number: int) -> str:

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            SELECT local_summary FROM local_summaries WHERE document_id = ? AND window_number = ?
        """

       cursor.execute(SQL_query, (document_id, window_number))
       row = cursor.fetchone()
       conn.close()
       if row is None:
              raise ValueError('Local Summary not found')
       
       return row[0]

def merged_summary_exists(document_id: int):

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            SELECT merged_summary FROM merged_summaries WHERE document_id = ?
        """
       cursor.execute(SQL_query, (document_id,))
       row = cursor.fetchone()
       conn.close()
       return row is not None

def save_merged_summary(document_id: int, merged_summary: str):

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            INSERT INTO merged_summaries (document_id, merged_summary) VALUES (?, ?)
        """

       cursor.execute(SQL_query, (document_id, merged_summary))
       conn.commit()
       conn.close()

def get_merged_summary(document_id: int) -> str:

       conn = get_connection()
       cursor = conn.cursor()

       SQL_query = """
            SELECT merged_summary FROM merged_summaries WHERE document_id = ?
        """

       cursor.execute(SQL_query, (document_id,))
       row = cursor.fetchone()
       conn.close()

       if row is None:
              raise ValueError('Merged summary not found')
       
       return row[0]