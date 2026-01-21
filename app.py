import streamlit as st

st.set_page_config(page_title="GateFinder", page_icon="✈️")

st.title("✈️ GateFinder")
st.subheader("항공권 사진 한 장으로 시작하는 스마트 공항 가이드")

uploaded_file = st.file_uploader("항공권 이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    st.image(uploaded_file, caption="업로드된 항공권", use_container_width=True)
    st.success("이미지가 성공적으로 업로드되었습니다! 이제 AI가 분석할 차례입니다.")