import streamlit as st
import os
import json
import io
import sys

# --- 1. 안전한 시작 및 라이브러리 검사 ---
st.set_page_config(page_title="Gongyou Drive", page_icon="☁️", layout="wide")

try:
    import pandas as pd
    import streamlit.components.v1 as components
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
except ImportError as e:
    st.error("🚨 **치명적인 오류: 필수 라이브러리를 찾을 수 없습니다.**")
    st.warning(f"누락된 라이브러리: {e}")
    st.info("GitHub의 `requirements.txt` 파일에 오타가 있거나, 설치가 덜 된 상태입니다.")
    st.stop()

# ==========================================
# [설정] 사용자 정보
# ==========================================
TARGET_FOLDER_ID = "1yp5QvbHIkvSO0OqmwhPW2bsF63ebpU-q"
# ==========================================

# --- 2. 인증 함수 (예외 처리 강화) ---
@st.cache_resource
def get_drive_service():
    # 읽기 전용 권한
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    creds = None
    bot_email = "알 수 없음"

    # A. Streamlit Cloud Secrets 확인
    if "gcp_service_account" in st.secrets:
        try:
            # Secrets 데이터를 딕셔너리로 변환
            key_dict = dict(st.secrets["gcp_service_account"])
            
            # 줄바꿈 문자(\n)가 문자열로 잘못 들어간 경우 수정
            if "private_key" in key_dict:
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")

            creds = service_account.Credentials.from_service_account_info(
                key_dict, scopes=SCOPES)
            bot_email = key_dict.get('client_email', '알 수 없음')
        except Exception as e:
            return None, None, f"Secrets 키 파싱 오류: {e}"

    # B. 로컬 파일 확인 (보조 수단)
    elif os.path.exists('gong_key.json'):
        try:
            creds = service_account.Credentials.from_service_account_file(
                'gong_key.json', scopes=SCOPES)
            bot_email = creds.service_account_email
        except Exception as e:
            return None, None, f"로컬 파일 오류: {e}"
    
    else:
        return None, None, "인증 정보를 찾을 수 없습니다. (Secrets 설정을 확인하세요)"

    # C. 서비스 연결
    try:
        service = build('drive', 'v3', credentials=creds)
        return service, bot_email, None
    except Exception as e:
        return None, None, f"구글 API 연결 실패: {e}"

# --- 3. 기능 함수들 ---
def list_files_in_folder(folder_id):
    service, _, error = get_drive_service()
    if error:
        st.error(f"❌ {error}")
        return []
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query, pageSize=50, fields="files(id, name, mimeType)").execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"폴더 접근 실패: {e}")
        return []

def download_file_content(file_id):
    service, _, _ = get_drive_service()
    if not service: return None
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()
    except: return None

# --- 4. 화면 구성 ---
if 'pin' not in st.session_state:
    st.session_state.pin = st.secrets.get("admin_password", "0000")
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def main():
    if not st.session_state.authenticated:
        st.title("🔒 로그인")
        pw = st.text_input("비밀번호", type="password")
        if st.button("접속"):
            if pw == st.session_state.pin:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
        return

    # 로그인 후 화면
    st.sidebar.title("Gongyou Drive")
    if st.button("로그아웃"):
        st.session_state.authenticated = False
        st.rerun()

    service, bot_email, error = get_drive_service()
    if error:
        st.error("⚠️ 인증 오류 발생")
        st.code(error)
        st.info("Streamlit Cloud 설정의 'Secrets' 형식을 다시 확인해주세요.")
    else:
        st.sidebar.success("연결됨")
        st.sidebar.code(bot_email)
        
        st.subheader(f"폴더 내용 ({TARGET_FOLDER_ID})")
        files = list_files_in_folder(TARGET_FOLDER_ID)
        
        if not files:
            st.warning("파일이 없습니다.")
        
        for file in files:
            col1, col2 = st.columns([4, 1])
            col1.write(f"📄 {file['name']}")
            if col2.button("실행", key=file['id']):
                content = download_file_content(file['id'])
                if content:
                    components.html(content.decode('utf-8'), height=800, scrolling=True)

if __name__ == "__main__":
    main()
