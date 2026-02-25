import streamlit as st
import pandas as pd
import os

# --- 1. 기본 설정 및 데이터 로드 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="컴퓨존 비교표 관리자", layout="wide")

# 이미지 1번 스타일 완벽 고정 (CSS)
st.markdown("""
    <style>
    .stApp { background-color: #F9FAFB; }
    .product-card {
        background-color: white; padding: 10px 15px; border-radius: 8px;
        border: 1px solid #E5E7EB; margin-bottom: 5px;
    }
    .price-label { font-size: 11px; color: #6B7280; }
    .price-value { font-size: 13px; font-weight: 600; color: #1F2937; }
    .prod-name { font-size: 13px; font-weight: 700; color: #374151; }
    .memo-txt { font-size: 11px; color: #9CA3AF; }
    </style>
""", unsafe_allow_html=True)

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            # 필수 컬럼이 없을 경우를 대비한 안전장치 (KeyError 방지)
            cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
            for c in cols:
                if c not in df.columns:
                    df[c] = "자주구매" if c == "구분" else 0
            return df.fillna("")
        except: pass
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state: st.session_state.df = load_data()
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None

# --- 2. 상단 등록/수정창 (통합형) ---
st.title("🍁 컴퓨존 비교표 및 구매링크")

is_edit = st.session_state.edit_idx is not None
expand_title = "📝 상품 정보 수정" if is_edit else "➕ 신규 상품 등록"

with st.expander(expand_title, expanded=is_edit):
    # 데이터 가져오기
    if is_edit:
        row = st.session_state.df.iloc[st.session_state.edit_idx]
        v_type, v_cat, v_name = row['구분'], row['카테고리'], row['상품명']
        v_link, v_my, v_cp, v_memo = row['링크'], int(row['가을판매가']), int(row['컴퓨존판매가']), str(row['메모'])
    else:
        v_type, v_cat, v_name, v_link, v_my, v_cp, v_memo = "자주구매", CATEGORY_LIST[1], "", "", 0, 0, ""

    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"], index=0 if v_type=="가격비교" else 1)
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST[1:], index=CATEGORY_LIST[1:].index(v_cat) if v_cat in CATEGORY_LIST else 0)
    r_name = c3.text_input("상품명", value=v_name)
    r_link = st.text_input("컴퓨존 URL", value=v_link)
    
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", value=v_my, step=1000)
    r_cp = c5.number_input("기준가", value=v_cp, step=1000)
    r_memo = c6.text_input("메모", value=v_memo)
    
    with c7:
        st.write("")
        if st.button("💾 저장하기", use_container_width=True, type="primary"):
            new_row = [r_type, r_cat, r_name, r_my, r_cp, r_cp, r_memo, r_link]
            if is_edit:
                st.session_state.df.iloc[st.session_state.edit_idx] = new_row
                st.session_state.edit_idx = None
            else:
                st.session_state.df.loc[len(st.session_state.df)] = new_row
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

    if is_edit and st.button("❌ 수정 취소", use_container_width=True):
        st.session_state.edit_idx = None
        st.rerun()

# --- 3. 리스트 영역 ---
st.write("")
f1, f2 = st.columns([7, 3])
search_q = f1.text_input("🔍 검색")
cat_q = f2.selectbox("📂 카테고리 필터", CATEGORY_LIST)

tabs = st.tabs(["전체보기", "가격비교", "자주구매"])

def render_list(df_in, tab_name):
    # 탭별 정밀 필터링 (섞임 방지)
    if tab_name == "가격비교": d_df = df_in[df_in['구분'] == "가격비교"]
    elif tab_name == "자주구매": d_df = df_in[df_in['구분'] == "자주구매"]
    else: d_df = df_in

    if d_df.empty:
        st.info(f"'{tab_name}' 탭에 상품이 없습니다.")
        return

    for idx, row in d_df.iterrows():
        with st.container(border=True):
            col_info, col_price, col_btn = st.columns([0.5, 0.4, 0.1])
            with col_info:
                st.markdown(f"<div class='prod-name'><small style='color:#2563EB;'>[{row['카테고리']}]</small> {row['상품명']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='memo-txt'>📝 {row['메모']}</div>", unsafe_allow_html=True)
            with col_price:
                p1, p2, p3, p4 = st.columns(4)
                if tab_name != "가격비교":
                    p1.markdown(f"<div class='price-label'>가을가</div><div class='price-value'>{int(row['가을판매가']):,}</div>", unsafe_allow_html=True)
                p2.markdown(f"<div class='price-label'>기준가</div><div class='price-value'>{int(row['컴퓨존판매가']):,}</div>", unsafe_allow_html=True)
                p3.markdown(f"<div class='price-label'>실시간</div><div class='price-value' style='color:#2563EB;'>{int(row['실시간가']):,}</div>", unsafe_allow_html=True)
                diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
                diff_txt = f"<span style='color:red;'>▲{diff:,}</span>" if diff > 0 else (f"<span style='color:blue;'>▼{abs(diff):,}</span>" if diff < 0 else "-")
                p4.markdown(f"<div class='price-label'>변동액</div><div class='price-value'>{diff_txt}</div>", unsafe_allow_html=True)
            with col_btn:
                if st.button("수정", key=f"ed_{tab_name}_{idx}"):
                    st.session_state.edit_idx = idx
                    st.rerun()
                st.link_button("열기", row['링크'])

# 필터 적용
filtered_df = st.session_state.df.copy()
if cat_q != "전체보기": filtered_df = filtered_df[filtered_df['카테고리'] == cat_q]
if search_q: filtered_df = filtered_df[filtered_df['상품명'].str.contains(search_q, case=False)]

with tabs[0]: render_list(filtered_df, "전체보기")
with tabs[1]: render_list(filtered_df, "가격비교")
with tabs[2]: render_list(filtered_df, "자주구매")
