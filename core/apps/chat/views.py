# 最新一版views，可以成功执行的
from django.views.generic import TemplateView
from web_project import TemplateLayout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
import glob
import time
from django.conf import settings
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re

from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain import hub


def remove_think(text):
    # 使用正则表达式匹配<think>...</think>标签及其内容
    pattern = r'<think>.*?</think>'
    # 使用re.sub()函数将匹配到的内容替换为空字符串
    cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
    return cleaned_text

#以下是core内容
import glob
from langchain.document_loaders import PDFPlumberLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OllamaEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOllama
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser

# 配置信息
PDF_FILES_PATH = 'KB3/pdfs/*.pdf'
EMBEDDING_MODEL = "nomic-embed-text"
QA_MODEL = "deepseek-r1:8b"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100


# 1. 加载 多个PDF 文档并将其切分为适当大小的文本块
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


# 2. 初始化向量存储
def initialize_vector_store():
    try:
        local_embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        vectorstore = Chroma(persist_directory='/home/luyu/agent2_sales_qa/core/apps/chat/chroma_db', embedding_function=local_embeddings)
        print("成功加载持久化向量数据库")
        return vectorstore
    except Exception as e:
        print(f"加载向量数据库失败: {e}")
        return None


# 3. 定义 format_docs 函数
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Define prompt for question-answering 提示词还能拉取现成的
# prompt = hub.pull("rlm/rag-prompt")

# 4. 构建 QA 链
def build_qa_chain(vectorstore, model_name):
    print("step 4")
    if vectorstore is None:
        print("向量存储未正确初始化，无法构建问答链。")
        return None
    try:
        # model = ChatOllama(model=model_name)
        model = ChatOllama(model=model_name,
                            base_url="http://10.168.6.34:11434",temperature = 0.2,mirostat_tau=2.0,top_k=10,top_p=0.5
                            )
        RAG_TEMPLATE = """
        从现在起，如果别人问你是谁，你就回答你是一个由允思拓公司部署的本地大语言模型，模型基于DeepSeek-8b开源模型开发。
    你可以帮助回答三类问题，分别是科学问题（特别是关于健康、疾病、传染病相关知识以及医院的服务信息）、技术问题（关于生物信息相关的技术内容）、本公司的业务问题。对于上下文搜索不到的内容，你可以直接回答“不好意思，我目前不知道如何回答您的问题，您可以继续提问关于允思拓公司的信息和业务介绍。”。
        当回答关于价格的问题，第一个段落回答对应业务的价格，第二个段落介绍该业务，第三个段落提出允思拓公司在该业务上的优势，最后附上公司联系方式。
        <context>
        {context}
        </context>
    在理解你自己是谁的情况下，按照用户的要求，以简洁的方式回答下面的问题：
        {question}"""
        
        # 提示词工程
        rag_prompt = ChatPromptTemplate.from_template(RAG_TEMPLATE)
        # 创建检索器
        # retriever = vectorstore.as_retriever(search_type="similarity",search_kwargs={"k": 10})
        
        #from langchain.retrievers.multi_query import MultiQueryRetriever
        
        # Retrieve and generate using the relevant snippets of the blog.
        # retriever = vectorstore.as_retriever()
        
        # 把query转换为多种同义问句再提问，回答会更准确
        retriever_from_llm = MultiQueryRetriever.from_llm(
            # retriever=vectorstore.as_retriever(search_type="similarity_score_threshold",search_kwargs={"score_threshold": .5}), llm=model
            retriever=vectorstore.as_retriever(search_type="similarity",search_kwargs={"k": 10}), llm=model
            
            )
            

        #prompt = hub.pull("rlm/rag-prompt")
        
        #
        
        #重排序
        
        results = retriever_from_llm.get_relevant_documents(RunnablePassthrough())
        # 打印结果
        i =1
        for result in results:
            print(i,"根据问题检索到相关信息如下")
            print(result.page_content)
            i=i+1
        qa_chain = (
                {"context": retriever_from_llm | format_docs, "question": RunnablePassthrough()}
                | rag_prompt
                | model
                | StrOutputParser()
        )
        return qa_chain
    except Exception as e:
        print(f"构建问答链时出错: {e}")
        return None


# 记录问答情况到文件
def log_qa(question, answer):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_entry = f"时间: {timestamp}\n问题: {question}\n答案: {answer}\n\n"
    with open('qa_log.txt', 'a', encoding='utf-8') as file:
        file.write(log_entry)

     

class ChatView(TemplateView):
    # Predefined function
    def get_context_data(self, **kwargs):
        # A function to init the global layout. It is defined in web_project/__init__.py file
        context = TemplateLayout.init(self, super().get_context_data(**kwargs))

        return context



@csrf_exempt  # 如果你没有处理CSRF令牌，可以使用这个装饰器（不推荐在生产环境中这样做）
def receive_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('messages', '')
            
            # 获取预构建的向量存储
            vectorstore = initialize_vector_store()
            
            print(vectorstore, "VVVVVVV")
            if not vectorstore:
                return JsonResponse({'success': False, 'error': '向量存储初始化失败'}, status=500)
            
            qa_chain = build_qa_chain(vectorstore, QA_MODEL)
            
            answer = qa_chain.invoke(question)
            print(answer)
            clean_answer = remove_think(answer)
            log_qa(question, answer)
            # 待修改，建一个异步函数，可以提速
            # docs = await vectorstore.asimilarity_search(question)
            # print(docs)
            return JsonResponse({'success': True, 'message': clean_answer})
        except Exception as e:
            print(f"处理请求时发生错误: {e}")
            return JsonResponse({'success': False, 'error': '服务器内部错误'}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
