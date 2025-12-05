import streamlit as st
import sys

# --- 시스템 진단 모드 ---
st.set_page_config(page_title="시스템 진단", page_icon="🛠")

st.title("🛠 Gongyou 시스템 진단 모드")
st.markdown("앱이 실행되지 않는 원인을 찾고 있습니다...")

# 1. 라이브러리 설치 확인
st.subheader("1. 라이브러리 설치 상태")
try:
    import pandas as pd
    st.success("✅ Pandas 라이브러리: 정상")
except ImportError:
    st.error("❌ Pandas 설치 실패 (requirements.txt 확인 필요)")

try:
    import google.oauth2
    import googleapiclient
    from googleapiclient.discovery import build
    st.success("✅ Google 연동 라이브러리: 정상")
except ImportError:
    st.error("❌ Google 라이브러리 설치 실패 (requirements.txt 확인 필요)")


# 2. Secrets(비밀키) 형식 확인
st.subheader("2. Secrets(비밀키) 상태")
try:
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Secrets에 `[gcp_service_account]` 섹션이 없습니다.")
        st.info("Streamlit Cloud 설정의 Secrets 탭을 확인해주세요.")
    else:
        st.success("✅ `[gcp_service_account]` 섹션 발견됨")
        
        # 키 내용 검사 (내용은 보여주지 않음)
        key_data = st.secrets["gcp_service_account"]
        
        if "type" in key_data and key_data["type"] == "service_account":
            st.success("✅ type: service_account 확인됨")
        else:
            st.warning("⚠️ type 항목이 없거나 service_account가 아닙니다.")

        if "private_key" in key_data:
            pk = key_data["private_key"]
            if "-----BEGIN PRIVATE KEY-----" in pk:
                st.success("✅ private_key 헤더 확인됨")
                
                # 줄바꿈 문자 확인
                if "\\n" in pk:
                    st.warning("⚠️ private_key에 문자열 `\\n`이 포함되어 있습니다. (자동 수정 가능)")
                elif "\n" in pk:
                    st.success("✅ private_key 줄바꿈 정상")
            else:
                st.error("❌ private_key 형식이 올바르지 않습니다. (`-----BEGIN...` 으로 시작해야 함)")
        else:
            st.error("❌ private_key 항목이 없습니다.")

        if "client_email" in key_data:
            st.success(f"✅ 봇 이메일 확인됨: `{key_data['client_email']}`")
        else:
            st.error("❌ client_email 항목이 없습니다.")

except Exception as e:
    st.error(f"❌ Secrets를 읽는 중 치명적인 오류 발생: {e}")
    st.markdown("Secrets 형식이 TOML이 아닌 JSON으로 되어 있을 가능성이 높습니다.")

st.divider()
st.info("위 진단 내용을 확인한 후, 문제가 없다면 다시 원래 코드로 복구해 주세요.")
