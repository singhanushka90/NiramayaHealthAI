import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from app.services.ocr_processor import extract_text_with_ocr
from app.services.document_classifier import classify_document_by_rules

embedding_model=SentenceTransformer("BAAI/bge-small-en-v1.5")

def detect_pdf_type(file_path:str):
    document=fitz.open(file_path)
    total_text_length=0
    total_pages=len(document)
    for page in document:
        text=page.get_text().strip()
        total_text_length+=len(text)
    document.close()
    if total_text_length<50:
        return {
            "document_type":"scanned",
            "total_pages":total_pages,
            "text_length":total_text_length
        }
    return {
        "document_type":"digital",
        "total_pages":total_pages,
        "text_length":total_text_length
    }

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


def process_document(file_path:str):
    pdf_info=detect_pdf_type(file_path)
    if pdf_info["document_type"]=="scanned":
        ocr_result=extract_text_with_ocr(file_path)
        extracted_text=ocr_result["text"]
    else:
        extracted_text=extract_text_from_pdf(file_path)
    if not extracted_text.strip():
        return{
            "status":"error",
            "message":"No text could be extracted from the PDF",
            "pdf_info": pdf_info
        }
    classification=classify_document_by_rules(extracted_text)
    chunks=split_text_into_chunks(extracted_text)
    embeddings=generate_embeddings(chunks) if chunks else []
    return{
        "status":"success",
        "pdf_info": pdf_info,
        "classification":classification,
        "extracted_text":extracted_text,
        "chunks":chunks,
        "embeddings":embeddings
    }

