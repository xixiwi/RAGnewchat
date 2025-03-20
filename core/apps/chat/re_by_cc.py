# from langchain.document_loaders import TextLoader
from langchain_community.document_loaders import TextLoader
import os

file_path = 'test/similarity/test1.txt'
absolute_path = os.path.abspath(file_path)
print(absolute_path)
loader = TextLoader(absolute_path)

from langchain.text_splitter import CharacterTextSplitter
# from langchain.vectorstores import FAISS
from langchain_community.vectorstores import FAISS
# from langchain_community.embeddings import OllamaEmbeddings
from langchain_ollama import OllamaEmbeddings

documents = loader.load()
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
texts = text_splitter.split_documents(documents)
# embeddings = OpenAIEmbeddings()
EMBEDDING_MODEL = "nomic-embed-text"
local_embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
db = FAISS.from_documents(texts, local_embeddings,normalize_L2=True)

retriever = db.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": .1})

from langchain_ollama import ChatOllama

model_name="deepseek-r1:8b"
llm = ChatOllama(model=model_name,
                            base_url="http://10.168.6.88:11434",temperature = 0,mirostat_tau=2.0,top_k=10,top_p=0.5
                            )
# Helper function for printing docs
def pretty_print_docs(docs):
    print(
        f"\n{'-' * 100}\n".join(
            [f"Document {i+1}:\n\n" + d.page_content for i, d in enumerate(docs)]
        )
    )
    
# 另一种更简单但更强大的过滤器
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainFilter

_filter = LLMChainFilter.from_llm(llm)
compression_retriever = ContextualCompressionRetriever(
    base_compressor=_filter, base_retriever=retriever
)

