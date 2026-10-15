from config.settings import settings

print("Testing API Key configuration...\n")

print(
    f"Groq API Key: {settings.GROQ_API_KEY[:20]}..." if settings.GROQ_API_KEY else "Not set"
)

print(
    f"Semantic Scholar API Key: {settings.SEMANTIC_SCHOLAR_API_KEY[:20]}..." if settings.SEMANTIC_SCHOLAR_API_KEY else "Not set"
)

if settings.SEMANTIC_SCHOLAR_API_KEY:
    print("\n Semantic Scholar API Key is configured!")
else:
    print("\n Semantic Scholar API Key is NOT configured!")
