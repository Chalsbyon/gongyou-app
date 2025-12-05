import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os
import json

# ==========================================
# [설정] 사용자 정보
# ==========================================
# 공유한 구글 드라이브 폴더의 ID (브라우저 주소창의 folders/ 뒷부분)
TARGET_FOLDER_ID = "1yp5QvbHIkvSO0OqmwhPW2bsF63ebpU-q"
SERVICE_ACCOUNT_FILE = 'gong_key.json' 
# ==========================================

# --- 1. 초기 설정 및 인증 ---
st.set_page_config(page_title="Gongyou Drive", page_icon="☁️", layout="wide")

if 'pin' not in st.session_state:
    # Secrets에 'admin_password'가 있으면 그걸 쓰고, 없으면 0000
    if "admin_password" in st.secrets:
        st.session_state.pin = st.secrets["admin_password"]
    else:
        st.session_state.pin = '0000'

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

@st.cache_resource
def get_drive_service():
    """구글 드라이브 서비스 객체와 봇 이메일 주소를 반환합니다."""
    creds = None
    bot_email = "알 수 없음"
    
    # 읽기 전용 권한 (안전함)
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

    # 1. 로컬 환경: 파일이 있는지 확인
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            bot_email = creds.service_account_email
        except Exception as e:
            return None, None, f"로컬 인증 파일 오류: {e}"
            
    # 2. 클라우드 환경: Streamlit Secrets 확인
    elif "gcp_service_account" in st.secrets:
        try:
            key_dict = dict(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(
                key_dict, scopes=SCOPES)
            bot_email = key_dict.get('client_email', '알 수 없음')
        except Exception as e:
            return None, None, f"Secrets 인증 오류: {e}"
    
    else:
        return None, None, "인증 키를 찾을 수 없습니다. (Secrets 설정 필요)"

    try:
        service = build('drive', 'v3', credentials=creds)
        return service, bot_email, None
    except Exception as e:
        return None, None, f"서비스 연결 오류: {e}"

# --- 2. 구글 드라이브 기능 함수 ---

def list_files_in_folder(folder_id):
    service, _, error = get_drive_service()
    if error: return []
    try:
        # 폴더 안의 파일만 검색 (삭제된 파일 제외)
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query, 
            pageSize=100, 
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"파일 목록을 불러오지 못했습니다. 폴더 공유가 되어 있나요? ({e})")
        return []

def download_file_content(file_id):
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

def find_file_id_by_name_part(folder_id, name_part):
    service, _, error = get_drive_service()
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
    st.markdown("관리자 비밀번호를 입력하세요.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        input_pin = st.text_input("Password", type="password")
        if st.button("로그인", use_container_width=True):
            if input_pin == st.session_state.pin:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")

def file_manager_drive():
    # 봇 이메일 정보 가져오기
    _, bot_email, _ = get_drive_service()
    
    st.sidebar.success("✅ 구글 드라이브 연결 성공")
    st.sidebar.markdown("---")
    st.sidebar.caption("아래 이메일을 구글 드라이브 폴더에 '공유'해주세요:")
    st.sidebar.code(bot_email, language="text")
    st.sidebar.info(f"대상 폴더 ID:\n{TARGET_FOLDER_ID}")

    st.subheader("☁️ 파일 목록")
    st.markdown(f"> **폴더:** `{TARGET_FOLDER_ID}`")

    with st.spinner("파일 목록을 불러오는 중..."):
        files = list_files_in_folder(TARGET_FOLDER_ID)
    
    if not files:
        st.warning("폴더에 파일이 없거나, 봇 계정에 공유되지 않았습니다.")
        st.markdown("👈 왼쪽 사이드바의 **이메일 주소**를 복사해서 폴더에 초대해주세요!")
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
                
                # 데이터 주입 (weekly-task-backup 포함된 파일 찾기)
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
                            
                            # HTML 상단에 데이터 변수(window.db_data)로 주입
                            injected_script = f"""
                            <script>
                                console.log("✅ 데이터 주입 시작 (Gongyou App)");
                                window.db_data = {json_str_safe};
                            </script>
                            """
                            st.toast(f"데이터 연결 성공: {json_file_info['name']}")
                        except Exception as e:
                            st.error(f"JSON 데이터 파싱 오류: {e}")
                else:
                    st.warning(f"데이터 파일('{target_json_name}')을 찾을 수 없습니다.")

                html_content = html_bytes.decode('utf-8')
                # 주입된 스크립트 + 원본 HTML
                final_html = injected_script + html_content
                
                st.markdown("⬇️ **미리보기 화면**")
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
