from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from RAG import get_response
from pydantic import BaseModel, Field
import sqlite3
from database import load_chat_history, save_chat_history, load_and_chunk_pdf_file, save_pdf_file, update_vectorstore, get_chat_history, get_documents, delete_document, document_exists, create_user, username_exists, get_user_by_username, get_connection
from auth import hash_password, verify_password, create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

app = FastAPI()

class User(BaseModel):

       username: str
       password: str

@app.get('/', description='might be mapped to homme page later')
def root():
      return {'message': 'Greetings, upload your doc and talk to Groq LLM about it'}

@app.post('/register', description='Register yourself as user')
def register_user(user: User):

       username, password = user.username, user.password
       if username_exists(username):
              raise HTTPException(
                     status_code=400,
                     detail='Username already exists, choose a different one'
              )

       hashed_password = hash_password(password)
       create_user(username, hashed_password)
       return {'message': 'Registration successful'}

@app.post('/login')
def login_user(form_data: OAuth2PasswordRequestForm = Depends()):

       username, password = form_data.username, form_data.password
       user = get_user_by_username(username)
       if user is None:
              raise HTTPException(
                     status_code=401,
                     detail='Invalid username or password'
              )
       
       user_id, hashed_password = user.get('user_id'), user.get('password_hash')
       if not verify_password(password, hashed_password):
              raise HTTPException(
                     status_code=401,
                     detail='Invalid username or password'
              )

       token = create_access_token(data={
              'sub': username,
              'user_id': user_id
       })

       return {
            "access_token": token,
            "token_type": "bearer"
      }
       
       

@app.post('/upload', description='Upload your PDF File here')
async def upload_and_save_pdf(file: UploadFile = File(...), current_user:dict = Depends(get_current_user)):

        if file.content_type != 'application/pdf':
            raise HTTPException(status_code=400, detail='Please upload a valid PDF file')
        
        user_id = current_user['user_id']

        # save PDF file into documents folder and documents table:
        if document_exists(user_id, file.filename):
                    raise HTTPException(
                          status_code=409,
                          detail="This document has already been uploaded."
                    )
        
        
        document_id, filepath, filename = await save_pdf_file(file, user_id)

            
        
        # load chunks in chunks table:
        chunks = load_and_chunk_pdf_file(user_id, document_id, filepath, filename)

        # create embeddings and load in vectorstore:
        update_vectorstore(chunks)

        return {'message': 'PDF saved successfully', 'filename': filename, 'filepath': filepath, 'document ID': document_id, 'Number of Chunks': len(chunks)}

@app.post('/chat', description='Start asking questions about uploaded PDFs and save responses in a chatbox')
def user_llm_convo(question: str, current_user: dict = Depends(get_current_user)):

      user_id = current_user['user_id']
      response = get_response(user_id, question)
      return response

@app.get('/chathistory', description='Get the entire chat thread you have communicated with the LLM till now')
def return_chat_history(current_user: dict = Depends(get_current_user)):
      user_id = current_user['user_id']
      return {'history': get_chat_history(user_id)}

@app.delete('/deletechat', description='delete the chat history and start a fresh conversation')
def delete_chat(current_user: Annotated[dict, Depends(get_current_user)]):

      user_id = current_user['user_id']
      conn = get_connection()
      cursor = conn.cursor()
      SQL_query = """
            DELETE FROM chat_history WHERE user_id = ?
        """
      cursor.execute(SQL_query, (user_id,))
      conn.commit()
      conn.close()

      return {'message':'Chat history deleted succesfully'}

@app.get('/documents', description='fetches the PDF file name and associated document ID')
def get_docs(current_user: dict = Depends(get_current_user)):
      user_id = current_user['user_id']
      rows = get_documents(user_id)
      result = []
      for row in rows:
            result.append({
                  'document_ID': row[0],
                  'filename': row[1]
            })

      return result

@app.delete('/deletedocuments', description='Delete any document by referencing the document ID')
def delete_docss(current_user: Annotated[dict, Depends(get_current_user)], document_id: int):

      user_id = current_user['user_id']
      delete_document(user_id, document_id)
      return {'message': 'Document deleted succesfully!'}

