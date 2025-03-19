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
from langchain.schema import BaseMessage

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
def initialize_vector_store(documents):
    if not documents:
        print("文档列表为空，无法初始化向量存储。")
        return None
    try:
        local_embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        vectorstore = Chroma.from_documents(documents=documents, embedding=local_embeddings)
        return vectorstore
    except Exception as e:
        print(f"初始化向量存储时出错: {e}")
        return None


# 3. 定义 format_docs 函数
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# 4. 构建 QA 链
def build_qa_chain(vectorstore, model_name):
    if vectorstore is None:
        print("向量存储未正确初始化，无法构建问答链。")
        return None
    try:
        # model = ChatOllama(model=model_name)
        model = ChatOllama(model=model_name,
                            base_url="http://10.168.6.34:11434",
                            )
        RAG_TEMPLATE = """
        从现在起，如果别人问你是谁，你就回答你是一个由允思拓公司部署的本地大语言模型，模型基于DeepSeek-8b开源模型开发。
    你可以帮助回答三类问题，分别是科学问题（特别是关于健康、疾病、传染病相关知识以及医院的服务信息）、技术问题（关于生物信息相关的技术内容）、本公司的业务问题。对于其他问题，你可以直接回答“不好意思，我目前不知道如何回答您的问题，您可以继续提问关于允思拓公司的信息和业务介绍。”。
    
        <context>
        {context}
        </context>
    在理解你自己是谁的情况下，按照用户的要求，以简洁的方式回答下面的问题：
        {question}"""
        rag_prompt = ChatPromptTemplate.from_template(RAG_TEMPLATE)
        retriever = vectorstore.as_retriever()
        qa_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
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


'''
@csrf_exempt  # 如果你没有处理CSRF令牌，可以使用这个装饰器（不推荐在生产环境中这样做）
def receive_message(request):
    if request.method == 'POST':
        
        data = json.loads(request.body)
        question = data.get('messages', '')
        print("XXX", question)

        # qa_chain = build_qa_chain("deepseek-r1:8b")
        pdf_path = os.path.join(settings.BASE_DIR, 'apps','chat', PDF_FILES_PATH)
        print(pdf_path)
        
        # 初始化文档处理和 QA 链
        all_splits = load_and_split_pdf(pdf_path)
        vectorstore = initialize_vector_store(all_splits)
        qa_chain = build_qa_chain(vectorstore, QA_MODEL)

        
        answer = qa_chain.invoke(question)
        print(answer)

        clean_answer = remove_think(answer)
        log_qa(question, answer)

        return JsonResponse({'success': True, 'message': clean_answer})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
'''
@csrf_exempt  # 如果你没有处理CSRF令牌，可以使用这个装饰器（不推荐在生产环境中这样做）
def receive_message(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        question = data.get('messages', '')
        print("XXX", question)

        # 初始化 ChatOllama 模型
        model = ChatOllama(model=QA_MODEL,
                            base_url="http://10.168.6.34:11434",
                            )

        pdf_path = os.path.join(settings.BASE_DIR, 'apps', 'chat', PDF_FILES_PATH)
        print(pdf_path)

        # 初始化文档处理和 QA 链
        all_splits = load_and_split_pdf(pdf_path)
        vectorstore = initialize_vector_store(all_splits)
        qa_chain = build_qa_chain(vectorstore, QA_MODEL)

        # 构建消息列表以使用 get_num_tokens_from_messages
        messages = [
            BaseMessage(content=question, type="user")
        ]
        # 获取输入消息的 token 数
        input_token_used = model.get_num_tokens_from_messages(messages)

        answer = qa_chain.invoke(question)
        print(answer)

        # 获取输出结果的 token 数
        output_token_used = model.get_num_tokens(answer)

        # 总 token 数
        total_token_used = input_token_used + output_token_used
        print("tokens:",total_token_used)
        
        clean_answer = remove_think(answer)

        # 所有问答记录到文件中，同时记录 token 数
        # log_qa(question, answer, total_token_used)

        return JsonResponse({'success': True, 'message': clean_answer, 'token_used': total_token_used})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)