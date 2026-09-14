from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse, Response
from RAG import get_response
from pydantic import BaseModel, Field
import sqlite3
from database import load_chat_history, save_chat_history, load_and_chunk_pdf_file, save_pdf_file, update_vectorstore, get_chat_history, get_documents, delete_document, document_exists, create_user, username_exists, get_user_by_username, get_connection, create_projects, get_projects, delete_project, verify_project_owner, document_belongs_to_project, summary_exists, get_summary, save_summary
from auth import hash_password, verify_password, create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated, Literal
from content_generator import generate_summary, generate_flashcard, generate_quiz
from schemas import PaperSummary
from pdf_generator import generate_summary_pdf


app = FastAPI()

class User(BaseModel):

       username: str
       password: str

class SummaryLength(BaseModel):

       summary_length: Annotated[Literal['short', 'long', 'medium'], Field(..., description='Determine the overall length of summary you would prefer')]

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
       
@app.post('/projects', description='Create a new project here')
def register_project(current_user: Annotated[dict, Depends(get_current_user)], project_name: str):

         user_id = current_user['user_id']   
         project_id = create_projects(user_id, project_name)
         return {
                'message': 'Project successfully registered', 
                'Project ID': project_id,
                'Project Name': project_name
                }

@app.get('/current_projects', description='View all the projects details you own.')
def get_current_projects(current_user: Annotated[dict, Depends(get_current_user)]):

       user_id = current_user['user_id']
       return get_projects(user_id)

@app.delete('/deleteproject', description='chokeslam the shit out of a project')
def kill_project(current_user: Annotated[dict, Depends(get_current_user)], project_id: int):

       user_id = current_user['user_id']
       if verify_project_owner(project_id, user_id):
              delete_project(project_id, user_id)
              return {
                     'message': 'Project deleted successfully'
              }

       else:
              raise HTTPException(
                     status_code=403, 
                     detail='Unauthorized access!'
              )



@app.post('/upload', description='Upload your PDF File here')
async def upload_and_save_pdf(project_id: int, file: UploadFile = File(...), current_user:dict = Depends(get_current_user)):

        if file.content_type != 'application/pdf':
            raise HTTPException(status_code=400, detail='Please upload a valid PDF file')
        
        user_id = current_user['user_id']
        if not verify_project_owner(project_id, user_id):
               raise HTTPException(
                      status_code=403,
                      detail='Unauthorized access'
               )
        
        # save PDF file into documents folder and documents table:
        if document_exists(project_id, file.filename):
                    raise HTTPException(
                          status_code=409,
                          detail="This document has already been uploaded."
                    )
        
        
        document_id, filepath, filename = await save_pdf_file(file, project_id)

            
        
        # load chunks in chunks table:
        chunks = load_and_chunk_pdf_file(project_id, document_id, filepath, filename)

        # create embeddings and load in vectorstore:
        update_vectorstore(chunks)

        return {'message': 'PDF saved successfully', 'filename': filename, 'filepath': filepath, 'document ID': document_id, 'Number of Chunks': len(chunks)}

@app.post('/chat', description='Start asking questions about uploaded PDFs and save responses in a chatbox')
def user_llm_convo(project_id: int, question: str, current_user: dict = Depends(get_current_user)):

      user_id = current_user['user_id']
      if not verify_project_owner(project_id, user_id):
             raise HTTPException(
                    status_code=403, 
                    detail='Unauthorized access'
             )
      response = get_response(project_id, question)
      return response

@app.get('/chathistory', description='Get the entire chat thread you have communicated with the LLM till now')
def return_chat_history(project_id: int, current_user: dict = Depends(get_current_user)):
      user_id = current_user['user_id']
      if not verify_project_owner(project_id, user_id):
             raise HTTPException(
                    status_code=403,
                    detail='Unauthorized access'
             )
      return {'history': get_chat_history(project_id)}

@app.delete('/deletechat', description='delete the chat history and start a fresh conversation')
def delete_chat(project_id: int, current_user: Annotated[dict, Depends(get_current_user)]):

      user_id = current_user['user_id']
      if not verify_project_owner(project_id, user_id):
             raise HTTPException(
                    status_code=403,
                    detail='Unauthorized access'
             )
      conn = get_connection()
      cursor = conn.cursor()
      SQL_query = """
            DELETE FROM chat_history WHERE project_id = ?
        """
      cursor.execute(SQL_query, (project_id,))
      conn.commit()
      conn.close()

      return {'message':'Chat history deleted succesfully'}

@app.get('/documents', description='fetches the PDF file name and associated document ID')
def get_docs(project_id: int, current_user: dict = Depends(get_current_user)):

      user_id = current_user['user_id']
      if not verify_project_owner(project_id, user_id):
             raise HTTPException(
                    status_code=403,
                    detail='Unauthorized access'
             )
      rows = get_documents(project_id)
      result = []
      for row in rows:
            result.append({
                  'document_ID': row[0],
                  'filename': row[1]
            })

      return result

@app.delete('/deletedocuments', description='Delete any document by referencing the document ID')
def delete_docss(project_id: int, current_user: Annotated[dict, Depends(get_current_user)], document_id: int):

      user_id = current_user['user_id']
      if not verify_project_owner(project_id, user_id):
             raise HTTPException(
                    status_code=403,
                    detail='Unauthorized access'
             )
      delete_document(project_id, document_id)
      return {'message': 'Document deleted succesfully!'}

@app.post('/summary', description='Generate the summary of the PDF file')
def generate_document_summary(project_id: int, document_id: int, summary_length: SummaryLength, current_user: Annotated[dict, Depends(get_current_user)]):

       user_id = current_user['user_id']
       if not verify_project_owner(project_id, user_id):

              raise HTTPException(
                     status_code=403,
                     detail='Unauthorized access'
              )

       if not document_belongs_to_project(project_id, document_id):

              raise HTTPException(
                     status_code=404,
                     detail='Document not found'
              )

       if summary_exists(document_id, summary_length.summary_length):
              summary = get_summary(document_id, summary_length.summary_length)
              return summary
       
       summary = generate_summary(document_id, summary_length.summary_length)
       save_summary(document_id, summary_length.summary_length, summary)
       return summary

@app.get('/summary/pdf', description='Download the entire summary report generated as a PDF file')
def get_download_pdf(current_user: Annotated[dict, Depends(get_current_user)], project_id: int, document_id: int, summary_length: Literal['short', 'long', 'medium']):

       user_id = current_user['user_id']
       if not verify_project_owner(project_id, user_id):
              raise HTTPException(
                     status_code=403,
                     detail='Unauthorized access'
              )

       if not document_belongs_to_project(project_id, document_id):
              raise HTTPException(
                     status_code=404,
                     detail='Document not found'
              )
       if not summary_exists(document_id, summary_length):

              raise HTTPException(
                     status_code=404,
                     detail="Summary has not been generated yet."
              )
       
       summary = get_summary(document_id, summary_length)
       filepath = generate_summary_pdf(summary, document_id, summary_length)

       return FileResponse(
              path=filepath,
              media_type='application/pdf',
              filename=f"summary_{document_id}_{summary_length}.pdf"
       )

@app.post('/documents/{document_id}/flashcard', description='Generate random flashcard from the paper')
def generate_document_flashcard(current_user: Annotated[dict, Depends(get_current_user)], project_id: int, document_id: int):

       user_id = current_user['user_id']
       if not verify_project_owner(project_id, user_id):
              raise HTTPException(
                     status_code=403,
                     detail='Unauthorized access'
              )

       if not document_belongs_to_project(project_id, document_id):
              raise HTTPException(
                     status_code=404,
                     detail='Document not found'
              )

       return generate_flashcard(document_id)

@app.post(
    "/documents/{document_id}/quiz",
    description="Generate a quiz from the paper"
)
def generate_document_quiz(
    current_user: Annotated[dict, Depends(get_current_user)],
    project_id: int,
    document_id: int,
    number_of_questions: int = 5,
    difficulty: Literal['easy', 'medium', 'tough'] = 'medium'
):
    user_id = current_user["user_id"]

    if not verify_project_owner(project_id, user_id):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized access"
        )

    if not document_belongs_to_project(project_id, document_id):
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return generate_quiz(
        document_id,
        number_of_questions,
        difficulty
    )

