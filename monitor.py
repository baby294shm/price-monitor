import streamlit as st
import pandas as pd
import os

# --- [제목 확정 및 설정] ---
st.set_page_config(page_title="컴퓨존 비교표 및 구매링크", layout="wide")
st.title("🍁 컴퓨존 비교표 및 구매링크")

DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

# --- [디자인 고정] 이미지 1번 스타일 (작은 글씨) ---
st.markdown("""
    <style>
    .stApp { background-color: #F9FAFB; }
    .product-card {
        background-color: white; padding: 8px 12px; border-radius: 6px;
        border: 1px solid #E5E7EB; margin-bottom: 4px;
    }
    .price-label { font-size: 11px; color: #6B7280; margin: 0; }
    .price-value { font-size: 13px; font-weight: 600; color: #1F2937; margin: 0; }
    .prod-name { font-size: 13px; font-weight: 700; color: #374151; }
    .memo-txt { font-size: 11px; color: #9CA3AF; }
    </style>
""", unsafe_allow_html=True)

# 데이터 로드 (오류가 나도 멈추지 않음)
@st.cache_data
def load_data_initial():
    cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            for col in cols:
                if col not in df.columns: df[col] = "자주구매" if col == "구분" else 0
            return df.fillna("")
        except: pass
    return pd.DataFrame(columns=cols)

if 'df' not in st.session_state:
    st.session_state.df = load_data_initial()
if 'edit_idx' not in st.session_state:
    st.session_state.edit_idx = None

# --- [상단 수정 및 등록창] ---
is_edit = st.session_state.edit_idx is not None
expand_label = "📝 선택한 상품 수정하기" if is_edit else "➕ 신규 상품 등록"

with st.expander(expand_label, expanded=is_edit):
    if is_edit:
        curr = st.session_state.df.iloc[st.session_state.edit_idx]
        v_type, v_cat, v_name = curr['구분'], curr['카테고리'], curr['상품명']
        v_link, v_my, v_cp, v_memo = curr['링크'], int(curr['가을판매가']), int(curr['컴퓨존판매가']), str(curr['메모'])
    else:
        v_type, v_cat, v_name, v_link, v_my, v_cp, v_memo = "자주구매", "PC", "", "", 0, 0, ""

    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"], index=0 if v_type=="가격비교" else 1)
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST[1:], index=CATEGORY_LIST[1:].index(v_cat) if v_cat in CATEGORY_LIST[1:] else 0)
    r_name = c3.text_input("상품명", value=v_name)
    
    r_link = st.text_input("컴퓨존 URL", value=v_link)
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", value=v_my)
    r_cp = c5.number_input("기준가", value=v_cp)
    r_memo = c6.text_input("메모", value=v_memo)
    
    if st.button("💾 데이터 저장 (새로고침은 브라우저 F5)" , type="primary", use_container_width=True):
        new_row = [r_type, r_cat, r_name, r_my, r_cp, r_cp, r_memo, r_link]
        if is_edit:
            st.session_state.df.iloc[st.session_state.edit_idx] = new_row
            st.session_state.edit_idx = None
        else:
            st.session_state.df.loc[len(st.session_state.df)] = new_row
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.success("저장되었습니다. 수동으로 새로고침(F5) 해주세요.")

# --- [리스트 영역] ---
search_q = st.text_input("🔍 검색")
t1, t2, t3 = st.tabs(["전체보기", "가격비교", "자주구매"])

def render(target_df, tab_id):
    if tab_id == "가격비교": d_df = target_df[target_df['구분'] == "가격비교"]
    elif tab_id == "자주구매": d_df = target_df[target_df['구분'] == "자주구매"]
    else: d_df = target_df

    for idx, row in d_df.iterrows():
        with st.container(border=True):
            col1, col2, col3 = st.columns([0.5, 0.4, 0.1])
            with col1:
                st.markdown(f"<div class='prod-name'><span style='color:#2563EB'>[{row['카테고리']}]</span> {row['상품명']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='memo-txt'>{row['메모']}</div>", unsafe_allow_html=True)
            with col2:
                p1, p2, p3 = st.columns(3)
                p1.markdown(f"<p class='price-label'>기준가</p><p class='price-value'>{int(row['컴퓨존판매가']):,}</p>", unsafe_allow_html=True)
                p2.markdown(f"<p class='price-label'>실시간</p><p class='price-value' style='color:#2563EB'>{int(row['실시간가']):,}</p>", unsafe_allow_html=True)
                diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
                diff_txt = f"<span style='color:red'>▲{diff:,}</span>" if diff > 0 else (f"<span style='color:blue'>▼{abs(diff):,}</span>" if diff < 0 else "-")
                p3.markdown(f"<p class='price-label'>변동액</p><p class='price-value'>{diff_txt}</p>", unsafe_allow_html=True)
            with col3:
                if st.button("수정", key=f"ed_{tab_id}_{idx}"):
                    st.session_state.edit_idx = idx
                    # 무한로딩 방지를 위해 rerun 대신 간단히 상태만 변경

# 필터링 및 출력
f_df = st.session_state.df.copy()
if search_q: f_df = f_df[f_df['상품명'].str.contains(search_q, case=False)]

with t1: render(f_df, "전체")
with t2: render(f_df, "가격비교")
with t3: render(f_df, "자주구매")
