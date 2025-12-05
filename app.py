import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os
import json

# --- 1. 기본 설정 ---
st.set_page_config(page_title="Gongyou Drive", page_icon="☁️", layout="wide")

# ==========================================
# [설정] 공유 폴더 ID (여기를 수정하세요)
TARGET_FOLDER_ID = "1yp5QvbHIkvSO0OqmwhPW2bsF63ebpU-q"
# ==========================================

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 2. 인증 및 드라이브 연결 ---
@st.cache_resource
def get_drive_service():
    """구글 드라이브 연결 서비스 생성"""
    creds = None
    bot_email = "알 수 없음"
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

    # Secrets 확인
    if "gcp_service_account" in st.secrets:
        try:
            key_dict = dict(st.secrets["gcp_service_account"])
            
            # [안전장치 1] private_key 줄바꿈 처리
            if "private_key" in key_dict:
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            
            # [안전장치 2] token_uri 누락 시 자동 추가 (이 부분이 에러를 해결합니다)
            if "token_uri" not in key_dict:
                key_dict["token_uri"] = "https://oauth2.googleapis.com/token"

            creds = service_account.Credentials.from_service_account_info(
                key_dict, scopes=SCOPES)
            bot_email = key_dict.get('client_email', '알 수 없음')
        except Exception as e:
            return None, None, f"비밀키(Secrets) 설정 오류: {e}"
    else:
        return None, None, "Secrets 설정을 찾을 수 없습니다."

    try:
        service = build('drive', 'v3', credentials=creds)
        return service, bot_email, None
    except Exception as e:
        return None, None, f"구글 API 연결 실패: {e}"

# --- 3. 파일 관련 함수 ---
def list_files_in_folder(folder_id):
    service, _, error = get_drive_service()
    if error:
        st.error(error)
        return []
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query, pageSize=100, fields="files(id, name, mimeType)").execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"폴더 읽기 실패: {e}")
        return []

def download_file(file_id):
    service, _, error = get_drive_service()
    if error: return None
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()
    except: return None

def find_data_file(folder_id, name_part):
    service, _, error = get_drive_service()
    if error: return None
    try:
        query = f"'{folder_id}' in parents and name contains '{name_part}' and trashed = false"
        results = service.files().list(q=query, pageSize=1, fields="files(id, name)").execute()
        files = results.get('files', [])
        return files[0] if files else None
    except: return None

# --- 4. 화면 UI ---
def login():
    st.title("🔒 로그인")
    # Secrets에 비밀번호가 없으면 0000으로 기본 설정
    admin_pw = st.secrets.get("admin_password", "0000")
    
    pw = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("접속"):
        if pw == admin_pw:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("비밀번호가 일치하지 않습니다.")

def main_app():
    service, bot_email, error = get_drive_service()
    
    with st.sidebar:
        st.title("Gongyou Cloud")
        
        if error:
            st.error("⚠️ 인증 오류")
            st.warning(error)
            # st.stop() # 에러 시 여기서 멈추도록 설정 가능
        else:
            st.success("✅ 서버 연결됨")
            if st.button("로그아웃"):
                st.session_state.authenticated = False
                st.rerun()
            
            st.divider()
            st.caption("구글 드라이브 봇 계정:")
            st.code(bot_email, language="text")
            st.info("👆 위 이메일을 구글 드라이브 폴더에 '뷰어'로 공유해주세요.")

    if error:
        return

    st.subheader("📂 파일 브라우저")
    
    with st.spinner("파일 목록을 가져오는 중..."):
        files = list_files_in_folder(TARGET_FOLDER_ID)

    if not files:
        st.warning("폴더에 표시할 파일이 없습니다.")
        st.markdown("1. 왼쪽 사이드바의 **봇 이메일**이 폴더에 초대되었는지 확인하세요.\n2. `TARGET_FOLDER_ID`가 올바른지 확인하세요.")
    
    for file in files:
        with st.container():
            col1, col2 = st.columns([4, 1])
            icon = "🌐" if "html" in file.get('mimeType', '') else "📄"
            col1.markdown(f"### {icon} {file['name']}")
            
            if "html" in file.get('mimeType', ''):
                if col2.button("실행 ▶️", key=file['id']):
                    st.session_state['active_file'] = file
            
            # 실행 화면 표시
            if st.session_state.get('active_file') and st.session_state['active_file']['id'] == file['id']:
                st.info(f"🚀 **{file['name']}** 실행 중...")
                html_data = download_file(file['id'])
                
                if html_data:
                    # 데이터 파일(JSON) 자동 주입 시도
                    json_file = find_data_file(TARGET_FOLDER_ID, "weekly-task-backup")
                    script_inject = ""
                    if json_file:
                        json_data = download_file(json_file['id'])
                        if json_data:
                            try:
                                json_str = json.dumps(json.loads(json_data.decode('utf-8')))
                                script_inject = f"<script>window.db_data = {json_str}; console.log('Data Injected');</script>"
                                st.toast("데이터 연결 성공!")
                            except: pass
                    
                    final_html = script_inject + html_data.decode('utf-8')
                    components.html(final_html, height=800, scrolling=True)
                    
                    if st.button("닫기 ❌", key=f"close_{file['id']}"):
                        del st.session_state['active_file']
                        st.rerun()
        st.divider()

# 메인 실행 로직
if not st.session_state.authenticated:
    login()
else:
    main_app()
