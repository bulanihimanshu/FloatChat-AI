# ollama_test.py

import ollama

# Choose your model (must be installed locally via Ollama)
model_name = "llama3"

# Define a simple prompt
prompt = "Explain the ocean circulation system in simple terms."

# Send the prompt to the model
response = ollama.chat(model=model_name, messages=[
    {"role": "user", "content": prompt}
])

# Print the model's reply
print("Model response:\n")
print(response['message']['content'])