import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io
import os
import json

# ==========================================
# [설정] 사용자 정보
# ==========================================
TARGET_FOLDER_ID = "1yp5QvbHIkvSO0OqmwhPW2bsF63ebpU-q" 
SERVICE_ACCOUNT_FILE = 'gong_key.json' 
# ==========================================

# --- 1. 초기 설정 및 인증 ---
st.set_page_config(page_title="Gongyou Drive", page_icon="☁️", layout="wide")

if 'pin' not in st.session_state:
    st.session_state.pin = '0000'
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

@st.cache_resource
def get_drive_service():
    creds = None
    
    # 1. 로컬 환경: 파일이 있는지 확인
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            SCOPES = ['https://www.googleapis.com/auth/drive']
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        except Exception as e:
            return None, f"로컬 인증 파일 오류: {e}"
            
    # 2. 클라우드 환경: Streamlit Secrets 확인
    # (GitHub에는 키 파일을 올리면 안되므로, 배포 환경에서는 이 코드가 실행됩니다)
    elif "gcp_service_account" in st.secrets:
        try:
            SCOPES = ['https://www.googleapis.com/auth/drive']
            # st.secrets에 저장된 정보를 딕셔너리로 불러옴
            key_dict = dict(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(
                key_dict, scopes=SCOPES)
        except Exception as e:
            return None, f"Secrets 인증 오류: {e}"
    
    else:
        return None, "인증 키를 찾을 수 없습니다. (로컬: gong_key.json 없음 / 클라우드: Secrets 설정 안됨)"

    try:
        return build('drive', 'v3', credentials=creds), None
    except Exception as e:
        return None, f"서비스 연결 오류: {e}"

# --- 2. 구글 드라이브 기능 함수 ---

def list_files_in_folder(folder_id):
    service, error = get_drive_service()
    if error: return []
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(q=query, pageSize=100, 
                                     fields="nextPageToken, files(id, name, mimeType)").execute()
        return results.get('files', [])
    except: return []

def download_file_content(file_id):
    service, error = get_drive_service()
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

def find_file_id_by_name_part(folder_id, name_part):
    service, error = get_drive_service()
    if error: return None
    try:
        query = f"'{folder_id}' in parents and name contains '{name_part}' and trashed = false"
        results = service.files().list(q=query, pageSize=1, fields="files(id, name)").execute()
        files = results.get('files', [])
        return files[0] if files else None
    except: return None

# --- 3. UI 화면 구성 ---

def login_screen():
    st.title("☁️ Gongyou (With Google Drive)")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_pin = st.text_input("비밀번호 4자리", type="password", max_chars=4)
        if st.button("로그인", use_container_width=True):
            if input_pin == st.session_state.pin:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")

def file_manager_drive():
    st.success(f"✅ 구글 드라이브 연결됨 (폴더 ID: ...{TARGET_FOLDER_ID[-5:]})")
    
    st.divider()
    st.subheader("☁️ 파일 목록")

    with st.spinner("파일 목록을 불러오는 중..."):
        files = list_files_in_folder(TARGET_FOLDER_ID)
    
    if not files:
        st.info("파일이 없습니다.")
    else:
        for file in files:
            with st.container():
                col_icon, col_name, col_action = st.columns([0.5, 3, 2])
                mime = file.get('mimeType', '')
                
                if 'html' in mime: icon = "🌐"
                elif 'json' in mime: icon = "⚙️"
                else: icon = "📄"
                
                with col_icon: st.markdown(f"### {icon}")
                with col_name: st.markdown(f"**{file['name']}**")
                
                with col_action:
                    if 'html' in mime:
                        if st.button("▶️ 데이터와 함께 실행", key=f"run_{file['id']}"):
                            st.session_state['preview_id'] = file['id']
                            st.session_state['preview_name'] = file['name']

            # --- 미리보기 로직 ---
            if st.session_state.get('preview_id') == file['id']:
                st.markdown("""<hr style="border-top: 3px solid #4CAF50;">""", unsafe_allow_html=True)
                st.info(f"🚀 **[{file['name']}] 실행 준비 중...**")
                
                html_bytes = download_file_content(file['id'])
                if not html_bytes:
                    st.error("❌ HTML 파일 로드 실패")
                    continue
                
                # 데이터 주입
                target_json_name = 'weekly-task-backup'
                json_file_info = find_file_id_by_name_part(TARGET_FOLDER_ID, target_json_name)
                injected_script = ""
                
                if json_file_info:
                    json_bytes = download_file_content(json_file_info['id'])
                    if json_bytes:
                        try:
                            json_str_raw = json_bytes.decode('utf-8')
                            json_obj = json.loads(json_str_raw)
                            json_str_safe = json.dumps(json_obj)
                            
                            injected_script = f"""
                            <script>
                                console.log("✅ 데이터 주입 시작");
                                window.db_data = {json_str_safe};
                            </script>
                            """
                            st.toast("데이터 연결 성공!")
                        except Exception as e:
                            st.error(f"데이터 파싱 오류: {e}")
                else:
                    st.warning("데이터 파일(weekly-task-backup)을 찾을 수 없습니다.")

                html_content = html_bytes.decode('utf-8')
                final_html = injected_script + html_content
                
                st.markdown("⬇️ **미리보기**")
                components.html(final_html, height=800, scrolling=True)
                
                if st.button("닫기", key=f"close_{file['id']}"):
                    del st.session_state['preview_id']
                    st.rerun()
            st.divider()

# --- 4. 메인 실행 ---
if not st.session_state.authenticated:
    login_screen()
else:
    with st.sidebar:
        st.title("Gongyou")
        if st.button("로그아웃"):
            st.session_state.authenticated = False
            st.rerun()
    file_manager_drive()