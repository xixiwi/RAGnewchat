from langchain_community.document_loaders import PDFPlumberLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
import glob

# 配置信息
PDF_FILES_PATH = 'KB3/pdfs/*.pdf'
EMBEDDING_MODEL = "nomic-embed-text"
CHROMA_DB_PATH = 'chroma_db'
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

def load_and_split_pdf(files_path):
    try:
        pdf_files = glob.glob(files_path)
        if not pdf_files:
            print(f"未找到符合路径 {files_path} 的PDF文件。")
            return []
        all_docs = []
        for file in pdf_files:
            loader = PDFPlumberLoader(file)
            docs = loader.load()
            all_docs.extend(docs)

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        all_splits = text_splitter.split_documents(all_docs)
        print(f"成功加载并分割 {len(all_splits)} 个文本块。")
        return all_splits
    except Exception as e:
        print(f"加载和切分 PDF 文件时出错: {e}")
        return []

def build_vector_store():
    all_splits = load_and_split_pdf(PDF_FILES_PATH)
    if not all_splits:
        return None
    try:
        local_embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        vectorstore = Chroma.from_documents(documents=all_splits, embedding=local_embeddings, persist_directory=CHROMA_DB_PATH)
        vectorstore.persist()
        print("向量存储构建完成并持久化到目录")
        return vectorstore
    except Exception as e:
        print(f"初始化向量存储时出错: {e}")
        return None