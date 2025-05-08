import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Embeddings and vectorstore
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma(persist_directory="honormind_chroma", embedding_function=embedding)
retriever = db.as_retriever(search_kwargs={"k": 4})

# Memory for conversation
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Prompt template for LLM
prompt = PromptTemplate(
    input_variables=["chat_history", "context", "question"],
    template="""
Use the following context and chat history to answer the question as helpfully as possible.

Chat History:
{chat_history}

Context:
{context}

Question:
{question}
"""
)

# LLM and chain setup
llm = OllamaLLM(model="llama3")
qa = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=memory,
    combine_docs_chain_kwargs={"prompt": prompt},
    return_source_documents=True,
    output_key="answer"  # ✅ FIXED HERE
)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def ask(ctx, *, query):
    await ctx.send("🧠 Thinking...")
    try:
        result = qa.invoke({"question": query})
        answer = result["answer"]
        sources = result.get("source_documents", [])

        confidence = "🔍 Confidence: High" if len(sources) >= 2 else "🔎 Confidence: Low"
        source_texts = "\n".join(
            [f"\n---\n📚 [{i+1}] {doc.metadata.get('title')} | <{doc.metadata.get('url')}>" for i, doc in enumerate(sources)]
        )

        await ctx.send(f"🎯 Answer: {answer}\n{confidence}\n{source_texts}")

    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
async def regenerate(ctx):
    last_q = memory.chat_memory.messages[-2].content if len(memory.chat_memory.messages) >= 2 else None
    if not last_q:
        await ctx.send("❗ No previous question found.")
        return
    await ask(ctx, query=last_q)

@bot.command()
async def history(ctx):
    history_str = "\n".join([f"🗨️ {msg.content}" for msg in memory.chat_memory.messages])
    await ctx.send(f"🧾 Conversation History:\n{history_str[:1800]}")

bot.run(DISCORD_TOKEN)
