import streamlit as st
import requests
import os
from dotenv import load_dotenv

# 1. 환경 설정 및 API 키 로드
load_dotenv()
# .env 파일에 AIRPORT_API_KEY가 있는지 확인하세요.
AIRPORT_API_KEY = os.getenv("AIRPORT_API_KEY")

st.set_page_config(page_title="API Debugger v2", page_icon="🔍")
st.title("🔍 인천공항 API 최종 진단기 v2")
st.markdown("""
이 도구는 **상세 조회(DS)**와 **일반 조회** 두 가지 API를 모두 테스트합니다.  
`500 Unexpected errors`가 나오면 서버 점검 중이거나 키 활성화 대기 중일 확률이 높습니다.
""")

# 2. 항공편명 입력 (현재 실제 운항 중인 편명 권장: KE005, KE723 등)
flight_id = st.text_input("테스트할 항공편명 입력", value="KE005").strip().upper()

# 3. 테스트 실행 버튼
col1, col2 = st.columns(2)

with col1:
    test_general = st.button("1. 일반 조회 API 테스트 🚀")
with col2:
    test_detailed = st.button("2. 상세 조회(DS) API 테스트 🚀")

def call_airport_api(url_type, flight_no):
    """
    url_type: 'general' 또는 'detailed'
    flight_no: 항공편명
    """
    if not AIRPORT_API_KEY:
        st.error(".env 파일에서 API 키를 찾을 수 없습니다.")
        return

    # API 주소 설정
    if url_type == 'general':
        base_url = 'http://apis.data.go.kr/B551177/StatusOfPassengerFlights/getPassengerDepartures'
        st.info("📡 일반 조회 API 시도 중...")
    else:
        base_url = 'http://apis.data.go.kr/B551177/StatusOfPassengerFlightsDS/getPassengerDeparturesDS'
        st.info("📡 상세 조회(DS) API 시도 중...")

    # [치트키] URL 직접 조립 (인코딩 방지)
    # 파이썬 requests의 자동 인코딩 기능을 우회하기 위해 전체 주소를 문자열로 만듭니다.
    full_url = f"{base_url}?serviceKey={AIRPORT_API_KEY}&flightId={flight_no}&type=json"
    
    with st.expander("🛠️ 호출 디버깅 정보 확인"):
        st.write(f"**요청 URL (일부 가림):** `{full_url[:80]}...` ")
    
    try:
        # params 인자를 쓰지 않고 직접 만든 full_url을 전달
        response = requests.get(full_url, timeout=10)
        
        st.write(f"**HTTP 상태 코드:** `{response.status_code}`")
        
        # 원본 데이터 출력
        st.markdown("**RAW 응답 내용:**")
        st.code(response.text)

        if "Unexpected errors" in response.text:
            st.error("❌ 서버 결과: Unexpected errors 발생")
            st.warning("이 에러는 보통 서버 점검 중이거나 키 승인 대기(1~24시간) 중일 때 발생합니다.")
        elif "SERVICE_KEY_IS_NOT_REGISTERED" in response.text:
            st.error("❌ 서버 결과: 인증키 미등록 에러")
            st.info("💡 해결책: .env의 키를 'Encoding' 버전 또는 'Decoding' 버전으로 바꿔서 다시 시도하세요.")
        else:
            try:
                data = response.json()
                st.success("✅ 진짜 데이터 수신 성공!")
                st.json(data)
            except:
                st.warning("데이터를 받았으나 JSON 형식이 아닙니다.")
                
    except Exception as e:
        st.error(f"연결 오류 발생: {e}")

# 버튼 클릭 로직
if test_general:
    call_airport_api('general', flight_id)

if test_detailed:
    call_airport_api('detailed', flight_id)

st.divider()
st.markdown("""
### 💡 에러별 조치 방법
1. **500 에러 + Unexpected errors**: 
   - 항공편명이 현재 전광판에 있는지 확인 (KE005 등).
   - 어제 저녁에 키를 받았다면 오늘 자정 이후 혹은 내일 아침에 다시 시도.
2. **SERVICE_KEY_IS_NOT_REGISTERED**: 
   - 공공데이터포털 마이페이지에서 **Encoding 키**와 **Decoding 키**를 각각 `.env`에 넣어보며 테스트.
3. **결과는 성공인데 데이터가 비어있음 (`items: []`)**: 
   - 해당 비행기가 아직 출발 전이거나 편명이 틀린 경우입니다.
""")