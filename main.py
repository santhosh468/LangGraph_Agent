import streamlit as st
import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv

# LangChain & LangGraph Imports
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage, HumanMessage

# 1. Load environment variables
load_dotenv()

# 2. Configure the Page
st.set_page_config(page_title="Agentic AI Researcher", page_icon="🤖")
st.title("🌐 Agentic AI Researcher")
st.caption("Powered by LangGraph, Groq (Llama 3.1), and DuckDuckGo")

# 3. Define the Graph State
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 4. Initialize Tools and LLM
@st.cache_resource
def init_graph():
    search_tool = DuckDuckGoSearchRun()
    tools = [search_tool]
    
    # Using llama-3.1-8b-instant for stability and tool-use performance
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0).bind_tools(tools)
    
    def assistant(state: State):
        # System Message prevents the "brave_search" hallucination
        sys_msg = SystemMessage(content=(
        "You are a professional AI Analyst. When you use search tools, do not just repeat the snippets. "
        "Synthesize the information into a concise, direct answer. "
        "Always state the person's name and their current role clearly."
     ))
        return {"messages": [llm.invoke([sys_msg] + state["messages"])]}

    # Build Graph
    workflow = StateGraph(State)
    workflow.add_node("assistant", assistant)
    workflow.add_node("tools", ToolNode(tools=[search_tool]))
    
    workflow.add_edge(START, "assistant")
    workflow.add_conditional_edges("assistant", tools_condition)
    workflow.add_edge("tools", "assistant")
    
    return workflow.compile()

graph_app = init_graph()

# 5. Chat Interface Logic
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display existing chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle User Input
if prompt := st.chat_input("What would you like me to research?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # Run the LangGraph Agent
        inputs = {"messages": [HumanMessage(content=prompt)]}
        
        # We stream the events to show progress in the UI
        for event in graph_app.stream(inputs, stream_mode="values"):
            # Get the last message from the current state
            if "messages" in event:
                last_msg = event["messages"][-1]
                if last_msg.content:
                    full_response = last_msg.content
                    response_placeholder.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})