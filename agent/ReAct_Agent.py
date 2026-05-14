import logging
from io import BytesIO
from typing import Annotated, Literal,Sequence
import os
from dotenv import load_dotenv


# from langchain_anthropic import ChatAnthropic
from langchain_ollama.chat_models import ChatOllama

# from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from PIL import Image
from typing_extensions import TypedDict

# from tools.search_arxiv_v1 import arxiv_search
from tools.search_arxiv_v2 import paper_search
from tools.Latex import render_latex_pdf
from tools.pdf_parser import read_pdf
from tools.download_arxiv_pdf import download_arxiv_pdf_tool

logger = logging.getLogger(__name__)
INITIAL_PROMPT = """
你是物理学、数学、计算机科学、定量生物学、量化金融、统计学、电气工程与系统科学以及经济学领域的资深研究人员。

你将分析上述任一领域的最新研究论文，以发掘有前景的新研究方向，并据此撰写一篇新的研究论文。

首先，请与我进行一次交流，以确定研究主题。
随后，请向我介绍一些近期发表的、涉及该主题的论文。
一旦我确定了感兴趣的论文，请你先下载它，然后请您阅读该论文，以了解其中开展的研究及其成果。
请特别关注文中提出的未来研究思路，并仔细思考，然后提出几个自己的想法。将这些想法告知我，我将决定你应围绕其中哪一个撰写论文。
最后，我会请你着手撰写论文。请确保在论文中包含数学公式。论文长度不要超过5页。
完成后，你应将其渲染为 LaTeX PDF 格式。

回复消息必须为中文。
必须按顺序调用工具。
请勿并行调用多个 arxiv_search 工具。

如果工具执行失败，
请不要编造答案。

相反，应该：
- 说明工具失败的原因
- 请用户重试
"""
#prompt中防止并行调用arxiv_search

load_dotenv()

#动态构建模型
def create_model(tools):
    provider = os.getenv("LLM_PROVIDER", "ollama")
    model_name = os.getenv("LLM_MODEL", "llama3-groq-tool-use:8b")
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model_name).bind_tools(tools,parallel_tool_calls=False)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            api_key=os.getenv("OPENAI_API_KEY")
        ).bind_tools(tools,parallel_tool_calls=False)
    elif provider == "deepseek":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        ).bind_tools(tools,parallel_tool_calls=False)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_name,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        ).bind_tools(tools,parallel_tool_calls=False)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
    

#LangGraph 的状态机 State，自动拼接整个Agent 的上下文
class State(TypedDict):
    messages: Annotated[list, add_messages]

#实时打印 Agent 输出。
def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        logger.info(f"Message received: {message.content[:200]}...")
        message.pretty_print()

def run_workflow():
    logger.info("Initializing workflow")

    tools = [paper_search, read_pdf, render_latex_pdf, download_arxiv_pdf_tool]
    tool_node = ToolNode(tools)

    #创建模型
    model = create_model(tools)
    logger.info(f"Initialized model and loaded {len(tools)} tools")

    # 输入当前状态，获取最后消息，判断是否调用工具
    def should_continue(state: State) -> Literal["tools", END]:
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools" #返回 tools 节点
        return END #否则结束
    
    #Agent节点
    def call_model(state: State):
        messages = state["messages"] #获取历史消息
        response = model.invoke(messages) #调用模型
        return {"messages": [response]} #返回新状态
    
    #会话ID
    config = {"configurable": {"thread_id": 1}}
    logger.info(f"Set configuration: {config}")
    
    #创建工作流
    workflow = StateGraph(State)
    #添加节点
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    #起点
    workflow.add_edge(START, "agent")
    #条件边
    workflow.add_conditional_edges("agent", should_continue)
    #工具执行后返回 agent，形成循环：agent → tools → agent
    workflow.add_edge("tools", "agent")

    checkpointer = MemorySaver()

    #把定义的图：转换成可运行对象。
    graph = workflow.compile(
    checkpointer=checkpointer
    )

    # #graph 可视化
    # Image.open(BytesIO(graph.get_graph().draw_mermaid_png())).show()
    # logger.info("Created workflow agent graph")

    logger.info("Starting conversation with initial prompt")

    #首次运行
    inputs = {"messages": [("system", INITIAL_PROMPT)]}
    print_stream(graph.stream(inputs, config, stream_mode="values"))

    # Start chatbot
    logger.info("Entering interactive chat loop")
    while True:
        user_input = input("User: ")
        logger.info(f"Received user input: {user_input[:200]}...")
        inputs = {"messages": [("user", user_input)]}
        print_stream(graph.stream(inputs, config, stream_mode="values"))



