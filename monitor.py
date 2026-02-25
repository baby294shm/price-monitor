import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
from io import BytesIO

# 데이터 저장 파일명
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]
VIEW_TYPES = ["가격비교", "자주구매"]

# 1. 가격 수집 함수 (가볍고 빠른 requests 방식 + 차단 방지 헤더)
def get_live_price(product_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }
    try:
        res = requests.get(product_url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            # 컴퓨존의 가격 태그 ID: product_content_2_price
            price_tag = soup.select_one("#product_content_2_price")
            if price_tag:
                return int(''.join(filter(str.isdigit, price_tag.get_text())))
        return None
    except:
        return None

# 2. 데이터 불러오기 (파일이 없거나 칸이 부족하면 자동으로 보정)
def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            # 필요한 칸(컬럼)이 없으면 자동 생성
            required_cols = ["구분", "카테고리", "상품명", "우리판매가", "컴퓨존등록가", "실시간가", "메모", "링크"]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = 0 if "가" in col else "-"
            return df
        except:
            pass
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "우리판매가", "컴퓨존등록가", "실시간가", "메모", "링크"])

# 3. 데이터 저장
def save_data(df):
    df.to_excel(DB_FILE, index=False)

# 4. 엑셀 다운로드용 변환
def to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 화면 구성 시작 ---
st.set_page_config(page_title="가격 통합 관리자", layout="wide")
st.title("🖥️ 컴퓨존 가격 변동 추적 시스템")

# 데이터 세션 초기화
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 상단: 신규 상품 등록 섹션 ---
with st.expander("➕ 신규 상품 정보 등록", expanded=False):
    c1, c2, c3, c4 = st.columns([1, 1, 2, 1])
    reg_type = c1.selectbox("📋 구분 선택", VIEW_TYPES) # 가격비교 / 자주구매 선택박스
    reg_cat = c2.selectbox("📁 카테고리", CATEGORY_LIST)
    reg_name = c3.text_input("📦 상품명 (관리용 이름)")
    reg_memo = c4.text_input("📝 메모 (비고)")
    
    c5, c6, c7 = st.columns([2, 1, 1])
    reg_link = c5.text_input("🔗 컴퓨존 상품 URL 주소")
    reg_my_price = c6.number_input("💰 우리 판매가 (원)", min_value=0, step=1000)
    reg_comp_price = c7.number_input("🏢 현재 컴퓨존 판매가 (원)", min_value=0, step=1000)
    
    if st.button("🚀 목록에 상품 추가하기", use_container_width=True):
        if reg_name and reg_link:
            new_row = {
                "구분": reg_type, "카테고리": reg_cat, "상품명": reg_name, 
                "우리판매가": reg_my_price, "컴퓨존등록가": reg_comp_price, 
                "실시간가": reg_comp_price, "메모": reg_memo, "링크": reg_link
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df)
            st.success(f"'{reg_type}' 항목에 성공적으로 추가되었습니다!")
            st.rerun()
        else:
            st.warning("상품명과 링크를 입력해주세요.")

st.divider()

# --- 메인 대시보드 리스트 ---
if not st.session_state.df.empty:
    # 필터 라인
    f_col1, f_col2, f_col3 = st.columns([3, 4, 3])
    with f_col1:
        view_mode = st.radio("🔍 보기 모드", VIEW_TYPES, horizontal=True)
    with f_col2:
        view_cat = st.selectbox("📂 카테고리 필터", ["전체보기"] + CATEGORY_LIST)
    
    # 필터 적용 데이터 추출
    display_df = st.session_state.df[st.session_state.df['구분'] == view_mode]
    if view_cat != "전체보기":
        display_df = display_df[display_df['카테고리'] == view_cat]

    with f_col3:
        btn_update = st.button("🔄 현재 리스트 가격 갱신", use_container_width=True)
        if btn_update:
            with st.spinner("가격을 업데이트 중입니다..."):
                for i in display_df.index:
                    new_p = get_live_price(st.session_state.df.at[i, '링크'])
                    if new_p: st.session_state.df.at[i, '실시간가'] = new_p
                save_data(st.session_state.df)
                st.rerun()

    # 표 헤더
    st.write("")
    h_cols = st.columns([0.8, 1, 2.5, 1.2, 1.2, 1.2, 1.2, 1.5, 0.5, 0.5])
    headers = ["구분", "카테고리", "상품명", "우리판매", "등록가", "실시간", "변동폭", "메모", "링크", "삭제"]
    for col, h in zip(h_cols, headers):
        col.write(f"**{h}**")

    # 리스트 본문 출력
    for idx, row in display_df.iterrows():
        r_cols = st.columns([0.8, 1, 2.5, 1.2, 1.2, 1.2, 1.2, 1.5, 0.5, 0.5])
        r_cols[0].write(row['구분'])
        r_cols[1].write(row['카테고리'])
        r_cols[2].write(row['상품명'])
        r_cols[3].write(f"{int(row['우리판매가']):,}")
        r_cols[4].write(f"{int(row['컴퓨존등록가']):,}")
        
        # 가격 및 변동폭 로직
        now_p = row['실시간가']
        if pd.notna(now_p) and now_p != 0:
            diff = int(now_p) - int(row['컴퓨존등록가'])
            r_cols[5].write(f"{int(now_p):,}")
            if diff > 0: r_cols[6].markdown(f":red[▲{diff:,}]")
            elif diff < 0: r_cols[6].markdown(f":blue[▼{abs(diff):,}]")
            else: r_cols[6].write("변동없음")
        else:
            r_cols[5].write("연결확인")
            r_cols[6].write("-")
            
        r_cols[7].write(row['메모'])
        r_cols[8].markdown(f"[🔗]({row['링크']})")
        
        if r_cols[9].button("❌", key=f"del_{idx}"):
            st.session_state.df = st.session_state.df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.df)
            st.rerun()

    st.divider()
    # 엑셀 다운로드 버튼 (하단 배치)
    st.download_button(
        label="📥 전체 데이터 엑셀 파일 다운로드",
        data=to_excel_bytes(st.session_state.df),
        file_name="compuzone_price_list.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
else:
    st.info("아직 등록된 상품이 없습니다. 상단 '신규 상품 정보 등록'을 눌러주세요.")