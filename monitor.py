import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 설정 및 데이터 로드 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# --- 에러 방지용 최적화 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; background-color: #FDFDFD; }
    
    /* 리스트 카드 디자인 */
    .product-row {
        background: white; padding: 15px 20px; border-radius: 12px;
        border: 1px solid #E5E7EB; margin-bottom: 10px;
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .info-area { flex: 1; min-width: 0; }
    .name-text { font-size: 14px; font-weight: 700; color: #334155; margin-bottom: 4px; }
    .memo-text { font-size: 12px; color: #94A3B8; }
    
    .price-area { display: flex; align-items: center; gap: 20px; }
    .price-box { text-align: center; width: 90px; }
    .label-txt { font-size: 10px; color: #94A3B8; margin-bottom: 4px; display: block; }
    
    /* 강조 배지 스타일 */
    .fall-badge { background: #2563EB; color: white; padding: 6px 12px; border-radius: 6px; font-weight: 700; font-size: 14px; }
    .diff-badge { padding: 4px 8px; border-radius: 5px; font-weight: 700; font-size: 11px; min-width: 60px; text-align: center; }
    .up { background: #FEE2E2; color: #EF4444; }
    .down { background: #DBEAFE; color: #3B82F6; }
    .same { background: #F3F4F6; color: #94A3B8; }

    /* 열기 버튼 */
    .open-btn {
        text-decoration: none !important; background: #10B981; color: white !important;
        padding: 7px 15px; border-radius: 6px; font-size: 12px; font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

def get_live_price(url):
    try:
        u = str(url).strip()
        if not u.startswith('http'): u = 'https://' + u
        res = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        p_tag = soup.select_one("#product_content_2_price")
        return int(''.join(filter(str.isdigit, p_tag.get_text()))) if p_tag else None
    except: return None

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
        for c in cols:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state: st.session_state.df = load_data()

st.markdown('<h2 style="color:#1E293B; margin-bottom:25px;">🍁 가을 가전 통합 관리 대시보드</h2>', unsafe_allow_html=True)

# 1. 상품 등록 (아코디언 형태)
with st.expander("➕ 상품 신규 등록", expanded=False):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명")
    r_link = st.text_input("컴퓨존 URL")
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", step=1000)
    r_cp = c5.number_input("기준가(컴퓨존)", step=1000)
    r_memo = c6.text_input("비고(메모)")
    if c7.button("목록에 추가", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link.strip()}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

# 2. 필터 및 검색
f1, f2 = st.columns([7, 3])
with f1: s_q = st.text_input("🔍 상품명 또는 메모 검색")
with f2: s_cat = st.selectbox("📂 카테고리 필터", CATEGORY_LIST)

t1, t2, t3 = st.tabs(["전체보기", "가격비교", "자주구매"])
sel_mode = "전체보기" if t1 else "가격비교" if t2 else "자주구매"

# 데이터 필터링
df = st.session_state.df.copy()
if sel_mode != "전체보기": df = df[df['구분'] == sel_mode]
if s_cat != "전체보기": df = df[df['카테고리'] == s_cat]
if s_q: df = df[df['상품명'].str.contains(s_q, case=False) | df['메모'].astype(str).str.contains(s_q, case=False)]

# 3. 액션 버튼
act1, act2, act3 = st.columns([7, 1.5, 1.5])
with act2: refresh_btn = st.button("🔄 실시간 가격 갱신", use_container_width=True)
with act3: delete_btn = st.button("🗑️ 선택 상품 삭제", use_container_width=True)

# 4. 리스트 출력 (핵심: HTML 깨짐 방지 구조)
selected_indices = []
for idx, row in df.iterrows():
    c_chk, c_body = st.columns([0.04, 0.96])
    with c_chk:
        if st.checkbox("", key=f"check_{idx}"): selected_indices.append(idx)
    with c_body:
        # 변동액 계산
        diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
        d_cls = "up" if diff > 0 else "down" if diff < 0 else "same"
        d_val = f"▲{diff:,}" if diff > 0 else f"▼{abs(diff):,}" if diff < 0 else "-"
        
        # 탭에 따른 가격 구성 (가격비교 탭은 가을판매가 제외)
        if sel_mode == "가격비교":
            price_html = f"""
                <div class="price-box"><span class="label-txt">기준가</span><div style="font-size:14px; color:#64748B;">{int(row['컴퓨존판매가']):,}</div></div>
                <div class="price-box"><span class="label-txt">실시간가</span><div style="font-size:14px; font-weight:700;">{int(row['실시간가']):,}</div></div>
                <div class="price-box"><span class="label-txt">변동액</span><div class="diff-badge {d_cls}">{d_val}</div></div>
            """
        else:
            price_html = f"""
                <div class="price-box"><span class="label-txt">가을판매가</span><div class="fall-badge">{int(row['가을판매가']):,}</div></div>
                <div class="price-box"><span class="label-txt">실시간가</span><div style="font-size:14px; font-weight:700;">{int(row['실시간가']):,}</div></div>
                <div class="price-box"><span class="label-txt">변동</span><div class="diff-badge {d_cls}">{d_val}</div></div>
            """

        st.markdown(f"""
        <div class="product-row">
            <div class="info-area">
                <div style="font-size:10px; color:#3B82F6; font-weight:700; margin-bottom:2px;">{row['카테고리']}</div>
                <div class="name-text">{row['상품명']}</div>
                <div class="memo-text">📝 {row['메모'] if str(row['메모']) != 'nan' else '메모 없음'}</div>
            </div>
            <div class="price-area">
                {price_html}
                <div style="width:50px; text-align:right;">
                    <a href="{row['링크']}" target="_blank" class="open-btn">열기</a>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 5. 하단 정보 수정 창 (사장님 요청 기능)
if selected_indices:
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.subheader("🛠️ 선택 상품 정보/기준가 수정")
    e_idx = selected_indices[0]
    target = st.session_state.df.loc[e_idx]
    with st.form("edit_form"):
        e_c1, e_c2, e_c3 = st.columns([1, 1, 2])
        new_f = e_c1.number_input("가을판매가", value=int(target['가을판매가']), step=1000)
        new_c = e_c2.number_input("컴퓨존기준가", value=int(target['컴퓨존판매가']), step=1000)
        new_m = e_c3.text_input("메모수정", value=str(target['메모']))
        if st.form_submit_button("변경사항 저장"):
            st.session_state.df.at[e_idx, '가을판매가'] = new_f
            st.session_state.df.at[e_idx, '컴퓨존판매가'] = new_c
            st.session_state.df.at[e_idx, '메모'] = new_m
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.success("수정되었습니다!")
            st.rerun()

# 6. 로직 처리
if delete_btn and selected_indices:
    st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
    st.session_state.df.to_excel(DB_FILE, index=False)
    st.rerun()

if refresh_btn:
    with st.spinner("가격을 업데이트 중입니다..."):
        for i in df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p: st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()
