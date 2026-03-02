
from openai import OpenAI
from langchain_openai import AzureChatOpenAI
from config_env import settings
from langchain_groq import ChatGroq

import os
from dotenv import load_dotenv


load_dotenv()


# -----------------------------
# Config
# -----------------------------
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN environment variable not set")

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

MODEL_NAME = "Qwen/Qwen3-VL-235B-A22B-Instruct:novita"



llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    max_retries=2,
    api_key=os.getenv("GROQ_API_KEY")
)



# llm = AzureChatOpenAI(
#     azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,  # or your deployment
#     api_key=settings.AZURE_OPENAI_API_KEY,
#     api_version=settings.AZURE_OPENAI_API_VERSION,
#     model=settings.AZURE_OPENAI_DEPLOYMENT,
#     temperature=0,
#     max_tokens=None,
#     timeout=None,
#     max_retries=2,
# )
