import os
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

# Load your token
token = os.getenv("GITHUB_TOKEN")
if not token:
    raise ValueError("❌ GITHUB_TOKEN not found. Make sure it's set.")

# Endpoint + model
endpoint = "https://models.github.ai/inference"
model = "openai/gpt-4o-mini"  # free-tier option

# Initialize client
client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(token))

# Send a sample query
response = client.complete(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ],
    model=model
)

# Print model reply
print("✅ Response:", response.choices[0].message["content"])
