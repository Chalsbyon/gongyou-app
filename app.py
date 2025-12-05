import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="Gongyou 진단", page_icon="🚑")

st.title("✅ 앱 서버 실행 성공!")
st.write("이 화면이 보인다면, **`requirements.txt`와 파이썬 서버**는 정상입니다.")
st.info("이제 문제가 '라이브러리'인지 'Secrets(비밀키)'인지 확인해 봅시다.")

st.divider()

# 1. 라이브러리 설치 확인
st.subheader("1. 라이브러리 설치 진단")
try:
    import pandas as pd
    import google.oauth2
    import googleapiclient
    from googleapiclient.discovery import build
    st.success("성공: 모든 필수 라이브러리가 잘 설치되어 있습니다.")
except ImportError as e:
    st.error(f"실패: 라이브러리 설치에 문제가 있습니다. ({e})")

# 2. Secrets(비밀키) 형식 확인
st.subheader("2. Secrets(비밀키) 진단")
try:
    # Secrets가 있는지 확인
    if not st.secrets:
        st.warning("Secrets가 비어있습니다. 설정이 필요합니다.")
    else:
        st.success("Secrets 파일이 감지되었습니다.")
        st.write(f"감지된 설정 섹션: `{list(st.secrets.keys())}`")
        
        if "gcp_service_account" in st.secrets:
            st.success("성공: `[gcp_service_account]` 섹션이 존재합니다.")
            
            # 내부 키 확인
            keys = st.secrets["gcp_service_account"]
            if "private_key" in keys and "-----BEGIN PRIVATE KEY-----" in keys["private_key"]:
                 st.success("성공: `private_key` 형식이 올바릅니다.")
            else:
                 st.error("실패: `private_key`가 없거나 형식이 잘못되었습니다.")
        else:
            st.error("실패: `[gcp_service_account]` 섹션을 찾을 수 없습니다.")

except Exception as e:
    st.error("❌ **치명적인 오류: Secrets 형식이 깨져 있습니다.**")
    st.error(f"에러 내용: {e}")
    st.markdown("""
    **해결 방법:**
    1. Streamlit Cloud 설정의 **Secrets** 탭으로 가세요.
    2. JSON 내용을 그대로 붙여넣지 말고, 반드시 **TOML 형식**으로 넣었는지 확인하세요.
    3. 맨 윗줄에 `[gcp_service_account]` 라고 적혀 있어야 합니다.
    """)
