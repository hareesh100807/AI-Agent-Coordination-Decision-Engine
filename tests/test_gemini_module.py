from app.llm.gemini import llm

response = llm.invoke(
    "Explain in one sentence what an AI agent is."
)

print("Gemini Response:")
print(response.text)