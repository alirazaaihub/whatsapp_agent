import os
from dotenv import load_dotenv
from typing import TypedDict
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found in .env file")

class AgentState(TypedDict):
    question: str
    context: str
    answer: str

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001"
)

vectorstore = Chroma(
    persist_directory="vector_store",
    embedding_function=embeddings,
)
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 4}
)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=GROQ_API_KEY
)

def retrieve(state: AgentState) -> AgentState:
    print("\n🔍 Retrieving relevant documents...")
    docs = retriever.invoke(state["question"])
    # No docs found
    if not docs:
        return {
            **state,
            "context": "NO_CONTEXT"
        }
    context = "\n\n".join(doc.page_content for doc in docs)
    return {
        **state,
        "context": context
    }

def generate(state: AgentState) -> AgentState:
    print("🧠 Generating answer...")
    if state["context"] == "NO_CONTEXT":
        return {
            **state,
            "answer": "Mujhe is sawal ka jawab nahi pata. Kisi expert se rabta karein."
        }
    prompt = f"""
You are a helpful assistant.
Answer the user's question ONLY using the context below.
If the context does not contain the answer,
reply exactly with:
"Mujhe is sawal ka jawab nahi pata. Kisi expert se rabta karein."
================ CONtEXT ================\n
{state["context"]}\n
=========================================\n
Question:
{state["question"]}\n
Answer:
"""
    result = llm.invoke([
        SystemMessage(content=prompt)
    ])

    return {
        **state,
        "answer": result.content.strip()
    }

def build_graph():

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)

    # Entry point
    graph.set_entry_point("retrieve")

    # Edges
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()

rag_graph = build_graph()

def get_answer(question: str) -> str:
    result = rag_graph.invoke({
        "question": question,
        "context": "",
        "answer": ""
    })

    return result["answer"]

# if __name__ == "__main__":

#     print("=" * 60)
#     print("📚 RAG Assistant Started")
#     print("Type 'exit' or 'quit' to stop")
#     print("=" * 60)

#     while True:

#         question = input("\n💬 Ask Question: ")

#         # Exit condition
#         if question.lower() in ["exit", "quit"]:
#             print("\n👋 Goodbye!")
#             break

#         try:
#             answer = get_answer(question)

#             print("\n🤖 Answer:")
#             print(answer)

#         except Exception as e:
#             print(f"\n❌ Error: {e}")
