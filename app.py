import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import json
import requests
from dotenv import load_dotenv

# ==========================================
# 1. 초기 설정 및 API 키 로드
# ==========================================
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# .env 파일에 'Decoding' 버전의 인증키가 들어있어야 가장 안전합니다.
AIRPORT_API_KEY = os.getenv("AIRPORT_API_KEY")

# 페이지 설정
st.set_page_config(page_title="GateFinder", page_icon="✈️", layout="centered")

# 간단한 CSS 스타일 적용 (가독성 향상)
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

st.title("✈️ GateFinder")
st.markdown("##### 항공권 한 장으로 시작하는 스마트 공항 가이드")

# ==========================================
# 2. 1단계: 항공권 이미지 업로드 및 AI 분석
# ==========================================
uploaded_file = st.file_uploader("항공권 이미지를 업로드하세요 (JPG, PNG)", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # 이미지 로드 및 최적화 (AI 전송 속도 향상을 위해 가로 1000px로 축소)
    image = Image.open(uploaded_file)
    base_width = 1000
    w_percent = (base_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    optimized_image = image.resize((base_width, h_size), Image.LANCZOS)
    
    st.image(image, caption="업로드된 항공권", use_container_width=True)
    
    # [분석하기] 버튼 클릭 시 로직 실행
    if st.button("AI 항공권 분석 시작 ✨", use_container_width=True):
        with st.status("AI가 항공권을 읽고 있습니다...", expanded=True) as status:
            try:
                # 사용 가능한 가장 빠른 모델 선택
                model = genai.GenerativeModel('gemini-flash-latest') 
                
                # AI에게 전달할 프롬프트 (JSON 형식 강제)
                prompt = """
                이 항공권 이미지에서 다음 정보를 추출해서 JSON 형식으로만 답해줘.
                - flight_no: 항공편명 (예: KE723)
                - gate: 게이트 번호 (숫자만)
                - departure_time: 출발 시간 (HH:mm 형식)
                - destination: 목적지 도시명
                결과에 JSON 외에 다른 설명은 포함하지 마.
                """
                
                # AI 분석 실행
                response = model.generate_content([prompt, optimized_image])
                
                # 응답에서 JSON 데이터만 추출하여 파싱
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_json)
                
                # 분석 결과를 세션 상태(메모리)에 저장
                st.session_state['flight_info'] = data
                status.update(label="AI 분석 완료!", state="complete", expanded=False)
                
                # 화면에 분석 결과 표시
                st.subheader("📋 분석된 티켓 정보")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("항공편명", data.get("flight_no"))
                col2.metric("목적지", data.get("destination"))
                col3.metric("게이트", data.get("gate"))
                col4.metric("출발시간", data.get("departure_time"))

            except Exception as e:
                st.error(f"AI 분석 중 오류가 발생했습니다: {e}")

# ==========================================
# 3. 2단계: 인천공항 실시간 API 연동 (에러 해결 버전)
# ==========================================
if 'flight_info' in st.session_state:
    st.divider()
    st.subheader("🔄 실시간 공항 정보 교차 검증")
    st.info("인천공항 실시간 데이터를 통해 현재 게이트를 최종 확인합니다.")
    
    if st.button("실시간 정보 가져오기 🔍", use_container_width=True):
        with st.spinner("인천공항 서버에 접속 중입니다..."):
            # 항공편명에서 공백 제거 (예: 'KE 723' -> 'KE723')
            raw_id = st.session_state['flight_info'].get('flight_no', '')
            flight_id = raw_id.replace(" ", "").upper()
            
            # [핵심] API 키 인코딩 문제를 피하기 위해 URL을 직접 조립합니다.
            base_url = 'http://apis.data.go.kr/B551177/StatusOfPassengerFlightsDS/getPassengerDeparturesDS'
            # params 옵션을 쓰는 대신 f-string으로 주소를 만듭니다.
            full_url = f"{base_url}?serviceKey={AIRPORT_API_KEY}&flightId={flight_id}&type=json"
            
            try:
                # API 호출
                response = requests.get(full_url, timeout=10)
                
                # 1단계 확인: 응답 내용이 JSON인지 확인
                # 만약 서버가 XML(에러 메시지)을 보냈다면 여기서 JSON 변환 시 에러가 납니다.
                try:
                    api_data = response.json()
                except Exception:
                    # JSON 변환 실패 시 서버가 보낸 실제 응답(XML 등)을 화면에 출력 (디버깅용)
                    st.error("서버로부터 올바른 JSON 데이터를 받지 못했습니다.")
                    with st.expander("에러 원인 분석 (서버 응답 내용)"):
                        st.code(response.text)
                    st.stop() # 이후 로직 실행 중단

                # 2단계 확인: 데이터 존재 여부
                items = api_data.get('response', {}).get('body', {}).get('items')
                
                if items:
                    flight_details = items[0] # 가장 첫 번째 검색 결과 사용
                    
                    real_gate = str(flight_details.get('gateno', '미정'))
                    terminal_id = flight_details.get('terminalid', 'P01')
                    status = flight_details.get('remark', '정보없음')
                    
                    # 터미널 ID를 읽기 쉬운 이름으로 변환
                    terminal_name = "제1여객터미널(T1)" if terminal_id == "P01" else "제2여객터미널(T2)"
                    ticket_gate = str(st.session_state['flight_info'].get('gate'))

                    # 최종 정보를 세션에 저장
                    st.session_state['real_data'] = {
                        "gate": real_gate,
                        "terminal": terminal_name,
                        "status": status
                    }

                    # 비교 UI 출력
                    st.success("실시간 조회 성공!")
                    res_col1, res_col2, res_col3 = st.columns(3)
                    with res_col1:
                        st.write("🏛️ 터미널")
                        st.subheader(terminal_name)
                    with res_col2:
                        st.write("🎫 티켓 게이트")
                        st.subheader(ticket_gate)
                    with res_col3:
                        st.write("📡 실시간 게이트")
                        # 티켓과 실시간 게이트가 다르면 경고 표시
                        if ticket_gate == real_gate:
                            st.subheader(f"✅ {real_gate}")
                        else:
                            st.subheader(f"⚠️ {real_gate}")
                            st.warning("게이트 변경!")
                    
                    st.info(f"🚩 현재 항공기 상태: **{status}**")
                
                else:
                    st.warning(f"항공편 {flight_id}에 대한 당일 운항 정보를 찾을 수 없습니다. (공항 전광판에 뜬 비행기만 조회 가능)")
            
            except Exception as e:
                st.error(f"연결 오류 발생: {e}")

# ==========================================
# 4. 3단계: 지도 시각화 (좌표 매핑 예정)
# ==========================================
if 'real_data' in st.session_state:
    st.divider()
    st.subheader("📍 게이트 위치 안내")
    st.write(f"현재 비행기는 **{st.session_state['real_data']['terminal']} {st.session_state['real_data']['gate']}번 게이트**에 있습니다.")
    
    # 맵 시각화 로직이 들어갈 자리
    st.info("준비 중: 공항 평면도 위에 게이트 위치를 핀으로 표시하는 기능이 추가될 예정입니다.")