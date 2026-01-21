import google.generativeai as genai
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("에러: .env 파일에서 GOOGLE_API_KEY를 찾을 수 없습니다.")
else:
    genai.configure(api_key=api_key)
    print(f"연결 시도 중... (Key: {api_key[:10]}...)")
    
    try:
        print("--- 사용 가능한 모델 목록 ---")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"에러 발생: {e}")