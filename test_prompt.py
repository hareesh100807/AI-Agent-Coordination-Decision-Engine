from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash"
)

prompt = ChatPromptTemplate.from_template(
    """
    You are a helpful AI assistant.

    Answer the following request clearly and professionally.

    Request:
    {user_request}
    """
)

user_request = "Explain what an AI agent is in simple words."

formatted_prompt = prompt.invoke({
    "user_request": user_request
})

response = llm.invoke(formatted_prompt)

print("Response:")
print(response.text)