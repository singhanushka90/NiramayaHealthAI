import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

embedding_model=SentenceTransformer("BAAI/bge-small-en-v1.5")

def extract_text_from_pdf(file_path:str):
    document=fitz.open(file_path)
    text=""
    for page in document:
        text+=page.get_text()
    document.close()
    return text


def split_text_into_chunks(text:str):
    splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
    chunks=splitter.split_text(text)
    return chunks

def generate_embeddings(chunks):
    embeddings=embedding_model.encode(chunks,normalize_embeddings=True)
    return embeddings