from fastapi import UploadFile
from langchain_core.documents import Document
from langchain_classic.document_loaders import PyPDFLoader
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import HumanMessage, AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import sqlite3
from typing import List
import os

# make a folder "documents" containing all uploaded PDF files if not exists yet
os.makedirs("documents", exist_ok=True)

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
    persist_directory='RAG_vectorstore_db',
    collection_name='research_papers'
)

# saving pdf filename and path into documents table and filepath in documents folder
async def save_pdf_file(file: UploadFile):
        filename = file.filename
        conn = sqlite3.connect("research_assistant.db")
        cursor = conn.cursor()

        SQL_query1 = """
            INSERT INTO documents (filename, filepath) VALUES (?, ?)
        """

        cursor.execute(SQL_query1, (filename, ""))
        document_id = cursor.lastrowid

        filepath = f'documents/{document_id}.pdf'

        with open(filepath, 'wb') as pdf:
                        pdf.write(await file.read())

        SQL_query2 = """
            UPDATE documents SET filepath = ? WHERE document_id = ?
        """

        cursor.execute(SQL_query2, (filepath, document_id))
        conn.commit()
        conn.close()

        return document_id, filepath, filename

def load_and_chunk_pdf_file(document_id, filepath, filename) -> List[Document]:

    loader = PyPDFLoader(filepath)
    docs = loader.load()
    for doc in docs:
            doc.metadata['filename'] = filename
            doc.metadata['document_id'] = document_id

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    values = []
    for i, chunk in enumerate(chunks):
           chunk.metadata['chunk_index'] = i
           page_number = chunk.metadata.get('page', -1)
           chunk_text = chunk.page_content
           row = (document_id, page_number, i, chunk_text)
           values.append(row)

    conn = sqlite3.connect("research_assistant.db")
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

def load_chat_history(_):

       history = []
       conn = sqlite3.connect("research_assistant.db")
       cursor = conn.cursor()
       SQL_query = """
            SELECT role, message FROM chat_history ORDER BY message_id
        """

       cursor.execute(SQL_query)
       rows = cursor.fetchall()

       for role, message in rows:

              if role == 'user':
                     history.append(HumanMessage(content=message))

              elif role == 'ai':
                     history.append(AIMessage(content=message))

       conn.close() 
       return history

def get_chat_history():

        conn = sqlite3.connect("research_assistant.db")
        cursor = conn.cursor()
        SQL_query = """
            SELECT role, message FROM chat_history ORDER BY message_id
        """
        cursor.execute(SQL_query)
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

def save_chat_history(user_input: str, ai: str) -> None:

       rows = [('user', user_input), ('ai', ai)]
       conn = sqlite3.connect("research_assistant.db")
       cursor = conn.cursor()
       SQL_query = """
            INSERT INTO chat_history (role, message) VALUES (?, ?)
        """   

       cursor.executemany(SQL_query, rows)
       conn.commit()
       conn.close() 

def get_documents():

        conn = sqlite3.connect("research_assistant.db")
        cursor = conn.cursor()
        SQL_query = """
            SELECT document_id, filename FROM documents ORDER BY document_id
        """    

        cursor.execute(SQL_query)
        rows = cursor.fetchall()
        conn.close()
        return rows

def delete_document(document_id):

        conn = sqlite3.connect("research_assistant.db")
        cursor = conn.cursor()
        SQL_query = """
            SELECT filepath FROM documents WHERE document_id = ?
        """

        cursor.execute(SQL_query, (document_id,))
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
            DELETE FROM documents WHERE document_id = ?
        """

        cursor.execute(SQL_query_child, (document_id,))
        cursor.execute(SQL_query_parent, (document_id,))
        conn.commit()
        conn.close()

        vectorstore.delete(where={'document_id': document_id})


def document_exists(filename):

    conn = sqlite3.connect("research_assistant.db")
    cursor = conn.cursor()

    SQL_query = """
        SELECT document_id
        FROM documents
        WHERE filename = ?
    """

    cursor.execute(SQL_query, (filename,))

    row = cursor.fetchone()

    conn.close()

    return row is not None       

        

        


        
        


