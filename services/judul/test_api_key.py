from config.settings import settings

print("Testing API Key configuration...\n")

# Jangan mencetak isi atau potongan kunci.
print("OpenAI API Key:", "terisi" if settings.OPENAI_API_KEY else "belum diisi")
print(
    "Semantic Scholar API Key:",
    "terisi" if settings.SEMANTIC_SCHOLAR_API_KEY else "belum diisi",
)

if settings.OPENAI_API_KEY:
    print("\n OpenAI API Key is configured!")
else:
    print("\n OpenAI API Key is NOT configured!")

if settings.SEMANTIC_SCHOLAR_API_KEY:
    print(" Semantic Scholar API Key is configured!")
else:
    print(" Semantic Scholar API Key is NOT configured!")
