from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    temperature=0.2,
)

response = llm.invoke(
    "Explain what an AI agent is in one simple sentence."
)

print("LangChain + Gemini Response:")
print(response.text)