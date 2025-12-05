import streamlit as st

# 어떤 라이브러리도 임포트하지 않고, 오직 기본 기능만 실행합니다.
st.set_page_config(page_title="생존 신고", page_icon="🏳️")

st.title("🎉 앱이 드디어 켜졌습니다!")
st.balloons()

st.write("### 1단계 성공")
st.success("이 화면이 보인다는 것은, 적어도 파이썬 서버는 살아있다는 뜻입니다.")
st.info("이전 오류의 원인은 'Secrets 파일 형식'이 잘못되어 앱이 시작조차 못한 것일 가능성이 큽니다.")

st.divider()

st.write("### 2단계: 문제 찾기")
st.write("아래 버튼을 하나씩 눌러보세요. 어느 버튼에서 에러가 나는지 확인하면 됩니다.")

if st.button("1. 라이브러리 불러오기 테스트"):
    try:
        import pandas as pd
        import google.oauth2
        import googleapiclient
        from googleapiclient.discovery import build
        st.success("✅ 라이브러리 설치 완벽함!")
    except Exception as e:
        st.error(f"❌ 라이브러리 오류: {e}")

if st.button("2. Secrets(비밀키) 읽기 테스트"):
    try:
        # Secrets 내용에 접근 시도
        if "gcp_service_account" in st.secrets:
            secrets_data = st.secrets["gcp_service_account"]
            st.success("✅ Secrets 파일 읽기 성공!")
            st.json(list(secrets_data.keys())) # 보안상 키 이름만 보여줌
        else:
            st.warning("⚠️ [gcp_service_account] 섹션이 없습니다.")
    except Exception as e:
        st.error("❌ Secrets 파일 형식이 깨져 있습니다 (TOML 문법 오류).")
        st.error(f"에러 메시지: {e}")
