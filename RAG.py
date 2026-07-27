from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_classic.retrievers import MultiQueryRetriever
from database import load_chat_history, save_chat_history

load_dotenv()

llm = ChatGroq(model='llama-3.3-70b-versatile')

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

parser = StrOutputParser()

vectorstore = Chroma(
    embedding_function=embedding_model,
    persist_directory='RAG_vectorstore_db',
    collection_name='research_papers'
)

retriever = MultiQueryRetriever.from_llm(
    retriever=vectorstore.as_retriever(search_kwargs={'k':10}, search_type='similarity'),
    llm=llm
)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a helpful AI Research Assistant.

Answer the user's question ONLY using the retrieved context below.

The retrieved context would also include the filename as the source and page number, state that to the user as citations of the answer.

If the retrieved context does not contain sufficient information, respond that you have inadequate information to answer the question.

Retrieved Context:
{context}
"""
    ),

    MessagesPlaceholder(variable_name="chat_history"),

    (
        "human",
        "{question}"
    )
])

def format_docs(docs):
    formatted = []

    for doc in docs:
        formatted.append(
            f"""
Source: {doc.metadata['filename']}
Page: {doc.metadata['page'] + 1}

{doc.page_content}
"""
        )

    return "\n\n------------------\n\n".join(formatted)


chain = prompt | llm | parser

def get_response(user_input: str):

    chunks = retriever.invoke(user_input)
    context = format_docs(chunks)
    citations = []
    seen = set()

    for chunk in chunks:
        citation = (chunk.metadata.get('filename'), chunk.metadata.get('page', -1) + 1)
        if citation not in seen:
            seen.add(citation)
            citations.append({'Filename': citation[0], 'Page Number': citation[1]})

    response = chain.invoke({'question': user_input, 'context': context, 'chat_history': load_chat_history(None)})
    save_chat_history(user_input, response)
    return {'response': response, 'citations': citations}



