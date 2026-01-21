import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import json
import requests
from dotenv import load_dotenv

# 1. 환경 설정 및 API 키 로드
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
AIRPORT_API_KEY = os.getenv("AIRPORT_API_KEY")

# 페이지 설정
st.set_page_config(page_title="GateFinder", page_icon="✈️", layout="centered")

# --- 스타일링 (CSS) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("✈️ GateFinder")
st.markdown("##### 항공권 사진 한 장으로 시작하는 스마트 공항 가이드")
st.info("티켓 사진을 업로드하면 AI 분석 후 실시간 게이트 정보를 가져옵니다.")

# --- 1단계: 항공권 이미지 업로드 및 AI 분석 ---
uploaded_file = st.file_uploader("항공권 이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # 이미지 처리 (속도 최적화를 위한 리사이징)
    image = Image.open(uploaded_file)
    base_width = 1000
    w_percent = (base_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    optimized_image = image.resize((base_width, h_size), Image.LANCZOS)
    
    st.image(image, caption="업로드된 항공권", use_container_width=True)
    
    if st.button("항공권 분석하기 ✨", use_container_width=True):
        with st.status("AI가 항공권을 분석 중입니다...", expanded=True) as status:
            try:
                # 확인된 가장 안정적인 모델명 사용
                model = genai.GenerativeModel('gemini-flash-latest') 
                
                prompt = """
                Analyze this boarding pass image. 
                Extract the following information and return ONLY a valid JSON object:
                - flight_no: The flight number (e.g., KE017)
                - gate: The gate number (e.g., 17)
                - departure_time: The departure time (e.g., 15:10)
                - destination: The destination city (e.g., LAX)
                
                Output strictly in JSON format.
                """
                
                response = model.generate_content([prompt, optimized_image])
                
                # 결과 텍스트 정제 및 JSON 파싱
                result_text = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(result_text)
                
                # 세션에 데이터 저장
                st.session_state['flight_info'] = data
                status.update(label="AI 분석 완료!", state="complete", expanded=False)
                
                # 분석 결과 표시
                st.subheader("📋 티켓 분석 결과")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("항공편명", data.get("flight_no"))
                col2.metric("목적지", data.get("destination"))
                col3.metric("티켓 게이트", data.get("gate"))
                col4.metric("출발 시간", data.get("departure_time"))

            except Exception as e:
                st.error(f"분석 중 오류 발생: {e}")

# --- 2단계: 인천공항 실시간 API 연동 ---
if 'flight_info' in st.session_state:
    st.divider()
    st.subheader("🔄 실시간 공항 정보 확인")
    st.write("티켓 정보가 실제 공항 상황과 일치하는지 확인합니다.")
    
    if st.button("실시간 정보 가져오기 🔍", use_container_width=True):
        with st.spinner("인천공항 실시간 데이터를 조회 중입니다..."):
            # 항공편명 정제
            raw_id = st.session_state['flight_info'].get('flight_no', '')
            flight_id = raw_id.replace(" ", "").upper()
            
            # API 호출 설정
            url = 'http://apis.data.go.kr/B551177/StatusOfPassengerFlightsDS/getPassengerDeparturesDS'
            params = {
                'serviceKey': AIRPORT_API_KEY,
                'flightId': flight_id,
                'type': 'json'
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                api_data = response.json()
                
                if api_data.get('response', {}).get('body', {}).get('items'):
                    flight_details = api_data['response']['body']['items'][0]
                    
                    real_gate = str(flight_details.get('gateno', '미정'))
                    terminal_id = flight_details.get('terminalid', 'P01')
                    status = flight_details.get('remark', '정보없음')
                    
                    terminal_name = "제1여객터미널(T1)" if terminal_id == "P01" else "제2여객터미널(T2)"
                    ticket_gate = str(st.session_state['flight_info'].get('gate'))

                    # 실시간 데이터 세션 저장
                    st.session_state['real_data'] = {
                        "gate": real_gate,
                        "terminal": terminal_name,
                        "status": status
                    }

                    # 비교 결과 UI
                    st.success(f"실시간 조회가 완료되었습니다.")
                    
                    res_col1, res_col2, res_col3 = st.columns(3)
                    with res_col1:
                        st.write("🏛️ 터미널")
                        st.subheader(terminal_name)
                    with res_col2:
                        st.write("🎫 티켓 게이트")
                        st.subheader(ticket_gate)
                    with res_col3:
                        st.write("📡 실시간 게이트")
                        if ticket_gate == real_gate:
                            st.subheader(f"✅ {real_gate}")
                        else:
                            st.subheader(f"⚠️ {real_gate}")
                            st.warning("게이트 변경됨!")
                    
                    st.info(f"🚩 현재 운항 상태: **{status}**")
                
                else:
                    st.warning(f"항공편 {flight_id}에 대한 실시간 정보를 찾을 수 없습니다. (당일 운항 정보만 조회 가능)")
            
            except Exception as e:
                st.error(f"실시간 조회 중 오류 발생: {e}")

# --- 3단계: 지도 시각화 (준비 단계) ---
if 'real_data' in st.session_state:
    st.divider()
    st.subheader("📍 게이트 위치 안내")
    st.write(f"현재 확정된 게이트는 **{st.session_state['real_data']['gate']}번**입니다.")
    
    # 임시 지도 이미지 표시 (다음 단계에서 실제 좌표 매핑 진행)
    st.info("🚧 3단계: 지도 시각화 기능이 곧 업데이트됩니다! (게이트 좌표 매핑 예정)")
    # 예: st.image("assets/airport_map.png")