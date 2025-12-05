import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.title("구글 연동 테스트 앱 🚀")

# 1. Secrets에서 인증 정보 가져오기
# 주의: Streamlit Cloud의 Secrets에 적은 섹션 이름(예: [gcp_service_account])과 일치해야 합니다.
try:
    # secrets.toml 파일의 [gcp_service_account] 부분을 가져옵니다.
    gcp_info = st.secrets["gcp_service_account"]
    
    # 인증 자격 증명 생성
    credentials = service_account.Credentials.from_service_account_info(
        gcp_info,
        scopes=["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/spreadsheets"]
    )
    st.success("✅ 비밀 키(Secrets)를 성공적으로 불러왔습니다!")

    # 2. 구글 드라이브 API 연결 테스트
    service = build('drive', 'v3', credentials=credentials)
    
    # 구글 드라이브의 파일 목록 5개만 가져와 보기
    results = service.files().list(pageSize=5, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        st.info("구글 드라이브에 파일이 없거나, 서비스 계정에 공유된 파일이 없습니다.")
    else:
        st.write("📂 **서비스 계정이 접근 가능한 파일 목록:**")
        df = pd.DataFrame(items)
        st.dataframe(df)

except Exception as e:
    st.error(f"❌ 오류가 발생했습니다: {e}")
    st.warning("Streamlit Cloud의 Secrets 설정과 키 이름이 정확한지 확인해주세요.")
