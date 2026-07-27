from fastapi import FastAPI, UploadFile, File, HTTPException
from RAG import get_response
import sqlite3
from database import load_chat_history, save_chat_history, load_and_chunk_pdf_file, save_pdf_file, update_vectorstore, get_chat_history, get_documents, delete_document, document_exists

app = FastAPI()

@app.get('/', description='might be mapped to homme page later')
def root():
      return {'message': 'Greetings, upload your doc and talk to Groq LLM about it'}

@app.post('/upload', description='Upload your PDF File here')
async def upload_and_save_pdf(file: UploadFile = File(...)):

        if file.content_type != 'application/pdf':
            raise HTTPException(status_code=400, detail='Please upload a valid PDF file')

        # save PDF file into documents folder and documents table:
        if document_exists(file.filename):
                    raise HTTPException(
                          status_code=409,
                          detail="This document has already been uploaded."
                    )
        
        
        
        document_id, filepath, filename = await save_pdf_file(file)

            
        
        # load chunks in chunks table:
        chunks = load_and_chunk_pdf_file(document_id, filepath, filename)

        # create embeddings and load in vectorstore:
        update_vectorstore(chunks)

        return {'message': 'PDF saved successfully', 'filename': filename, 'filepath': filepath, 'document ID': document_id, 'Number of Chunks': len(chunks)}

@app.post('/chat', description='Start asking questions about uploaded PDFs and save responses in a chatbox')
def user_llm_convo(question: str):

      response = get_response(question)
      return response

@app.get('/chathistory', description='Get the entire chat thread you have communicated with the LLM till now')
def return_chat_history():
      return {'history': get_chat_history()}

@app.delete('/deletechat', description='delete the chat history and start a fresh conversation')
def delete_chat():

      conn = sqlite3.connect("research_assistant.db")
      cursor = conn.cursor()
      SQL_query = """
            DELETE FROM chat_history
        """
      cursor.execute(SQL_query)
      conn.commit()
      conn.close()

      return {'message':'Chat history deleted succesfully'}

@app.get('/documents', description='fetches the PDF file name and associated document ID')
def get_docs():
      rows = get_documents()
      result = []
      for row in rows:
            result.append({
                  'document_ID': row[0],
                  'filename': row[1]
            })

      return result

@app.delete('/deletedocuments', description='Delete any document by referencing the document ID')
def delete_docss(document_id: int):

      delete_document(document_id)
      return {'message': 'Document deleted succesfully!'}

