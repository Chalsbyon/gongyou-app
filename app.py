import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os
import json

# --- 1. 초기 설정 (가장 먼저 실행) ---
st.set_page_config(page_title="Gongyou Drive", page_icon="☁️", layout="wide")

# ==========================================
# [설정] 사용자 정보
# ==========================================
# 공유한 구글 드라이브 폴더의 ID
TARGET_FOLDER_ID = "1yp5QvbHIkvSO0OqmwhPW2bsF63ebpU-q"
SERVICE_ACCOUNT_FILE = 'gong_key.json' 
# ==========================================

# 세션 상태 초기화
if 'pin' not in st.session_state:
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
    
    # 읽기 전용 권한
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

    # 1. 로컬 파일 확인 (개발 환경)
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            bot_email = creds.service_account_email
        except Exception as e:
            return None, None, f"로컬 키 파일 로드 실패: {e}"
            
    # 2. Streamlit Cloud Secrets 확인 (배포 환경)
    elif "gcp_service_account" in st.secrets:
        try:
            # Secrets 정보를 딕셔너리로 변환
            key_dict = dict(st.secrets["gcp_service_account"])
            
            # [중요] private_key의 줄바꿈 문자(\n) 처리 보정
            if "private_key" in key_dict:
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")

            creds = service_account.Credentials.from_service_account_info(
                key_dict, scopes=SCOPES)
            bot_email = key_dict.get('client_email', '알 수 없음')
        except Exception as e:
            return None, None, f"Secrets 키 형식 오류: {e}"
    
    else:
        return None, None, "인증 키를 찾을 수 없습니다. (Secrets의 [gcp_service_account] 설정을 확인하세요)"

    try:
        service = build('drive', 'v3', credentials=creds)
        return service, bot_email, None
    except Exception as e:
        return None, None, f"API 연결 실패: {e}"

# --- 2. 구글 드라이브 기능 함수 ---

def list_files_in_folder(folder_id):
    service, _, error_msg = get_drive_service()
    if error_msg:
        st.error(error_msg) # 에러 발생 시 화면에 출력
        return []
    
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
        st.error(f"❌ 파일 목록을 불러올 수 없습니다.\n\n원인: {e}\n\n👉 1. 폴더 ID('{folder_id}')가 정확한지 확인하세요.\n👉 2. 봇 이메일이 해당 폴더에 초대되었는지 확인하세요.")
        return []

def download_file_content(file_id):
    service, _, error_msg = get_drive_service()
    if error_msg: return None
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()
    except Exception as e:
        st.error(f"파일 다운로드 실패 ({file_id}): {e}")
        return None

def find_file_id_by_name_part(folder_id, name_part):
    service, _, error_msg = get_drive_service()
    if error_msg: return None
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
    _, bot_email, error_msg = get_drive_service()
    
    if error_msg:
        st.error("⚠️ 인증 시스템 오류")
        st.code(error_msg)
        st.stop() # 더 이상 진행하지 않음

    st.sidebar.success("✅ 구글 드라이브 연결 성공")
    st.sidebar.markdown("---")
    st.sidebar.caption("아래 이메일을 구글 드라이브 폴더에 '공유'해주세요:")
    st.sidebar.code(bot_email, language="text")
    st.sidebar.info(f"대상 폴더 ID:\n{TARGET_FOLDER_ID}")

    st.subheader("☁️ 파일 목록")
    st.caption(f"Folder: {TARGET_FOLDER_ID}")

    with st.spinner("파일 목록을 불러오는 중..."):
        files = list_files_in_folder(TARGET_FOLDER_ID)
    
    if not files:
        st.warning("표시할 파일이 없습니다.")
        st.info("체크리스트:\n1. 왼쪽 사이드바의 이메일을 구글 드라이브 폴더에 초대하셨나요?\n2. 코드 상단의 `TARGET_FOLDER_ID`가 실제 존재하는 폴더인가요?")
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
                        if st.button("▶️ 실행", key=f"run_{file['id']}"):
                            st.session_state['preview_id'] = file['id']
                            st.session_state['preview_name'] = file['name']

            # --- 미리보기 로직 ---
            if st.session_state.get('preview_id') == file['id']:
                st.markdown("""<hr style="border-top: 3px solid #4CAF50;">""", unsafe_allow_html=True)
                st.info(f"🚀 **[{file['name']}] 실행 중...**")
                
                html_bytes = download_file_content(file['id'])
                if not html_bytes:
                    continue # 위에서 에러 메시지 출력됨
                
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
                    st.warning(f"데이터 파일('{target_json_name}')을 찾을 수 없습니다. (HTML만 실행됨)")

                html_content = html_bytes.decode('utf-8')
                final_html = injected_script + html_content
                
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
