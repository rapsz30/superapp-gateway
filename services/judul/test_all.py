# test_all.py
print("="*50)
print("TESTING ALL MODULES")
print("="*50)

# Test 1: Config
try:
    from config.settings import settings
    print("✅ 1. settings imported")
    print(f"   Model: {settings.GROQ_MODEL}")
except Exception as e:
    print(f"❌ 1. Error: {e}")

# Test 2: Schemas
try:
    from models.schemas import UserInput
    print("✅ 2. UserInput imported")
    test_input = UserInput(interests="machine learning")
    print(f"   Test input: {test_input.interests}")
except Exception as e:
    print(f"❌ 2. Error: {e}")

# Test 3: Prompt Service
try:
    from services.prompt_service import prompt_service
    print("✅ 3. prompt_service imported")
    prompt = prompt_service.create_recommendation_prompt("AI")
    print(f"   Prompt length: {len(prompt)}")
except Exception as e:
    print(f"❌ 3. Error: {e}")

# Test 4: AI Service
try:
    from services.ai_service import ai_service
    print("✅ 4. ai_service imported")
    print(f"   Model: {ai_service.model}")
except Exception as e:
    print(f"❌ 4. Error: {e}")

print("="*50)
print("TEST COMPLETED!")
print("="*50)
