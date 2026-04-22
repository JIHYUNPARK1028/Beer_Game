import streamlit as st
import pandas as pd
import random

# 1. 페이지 설정
st.set_page_config(page_title="Beer Game Pro", layout="wide")

# --- CSS: 개별 박스 디자인 및 장부 스타일 ---
st.markdown("""
    <style>
    .board-title { text-align: center; font-weight: bold; margin-bottom: 10px; }
    .unit-box {
        border-radius: 10px; padding: 15px; margin: 5px 0;
        text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        min-height: 100px; display: flex; flex-direction: column; justify-content: center;
    }
    .order-style { background-color: #fff5f5; border: 2px dashed #ff4b4b; color: #d62728; }
    .inv-style { background-color: #e7f3ff; border: 3px solid #1f77b4; color: #1f77b4; }
    .ship-style { background-color: #f0fff0; border: 2px solid #2ca02c; color: #2ca02c; }
    .label-text { font-size: 0.85em; color: #555; font-weight: bold; margin-bottom: 5px; }
    .value-text { font-size: 2.2em; font-weight: bold; }
    
    /* 장부 스타일: 빈 칸 느낌 강조 */
    .stTable td { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 로직 클래스 (통합본) ---
class BeerGameChain:
    def __init__(self):
        self.roles = ["Retailer", "Wholesaler", "Distributor", "Factory"]
        self.inventory = {role: 8 for role in self.roles}
        self.backorder = {role: 0 for role in self.roles}
        self.order_delay = {r: [4, 4] for r in ["Wholesaler", "Distributor", "Factory"]}
        self.supply_delay = {r: [4, 4] for r in self.roles}
        # 30주차 전체 장부 미리 생성 (None으로 초기화)
        self.full_history = {role: pd.DataFrame(index=range(1, 31), 
                            columns=['C1_Initial', 'C2_Arrived', 'C3_NewOrder', 'C4_Final', 'C5_OrderDec']) 
                            for role in self.roles}

    def proceed_week(self, week, user_role, user_order, consumer_demand):
        inputs = {
            "Retailer": {"d": consumer_demand, "s": self.supply_delay["Retailer"].pop(0)},
            "Wholesaler": {"d": self.order_delay["Wholesaler"].pop(0), "s": self.supply_delay["Wholesaler"].pop(0)},
            "Distributor": {"d": self.order_delay["Distributor"].pop(0), "s": self.supply_delay["Distributor"].pop(0)},
            "Factory": {"d": self.order_delay["Factory"].pop(0), "s": self.supply_delay["Factory"].pop(0)}
        }
        
        current_results = {}
        for role in self.roles:
            # 1. 기초 재고 기록
            c1 = self.inventory[role] if self.backorder[role] == 0 else -self.backorder[role]
            
            # 2. 로직 계산
            self.inventory[role] += inputs[role]["s"]
            total_demand = inputs[role]["d"] + self.backorder[role]
            actual_ship = min(self.inventory[role], total_demand)
            self.inventory[role] -= actual_ship
            self.backorder[role] = total_demand - actual_ship
            
            c4 = self.inventory[role] if self.backorder[role] == 0 else -self.backorder[role]
            order_dec = user_order if role == user_role else inputs[role]["d"] + random.randint(0, 20)
            
            # 3. 미리 생성된 DataFrame의 해당 주차(week) 행 채우기
            self.full_history[role].at[week, 'C1_Initial'] = c1
            self.full_history[role].at[week, 'C2_Arrived'] = inputs[role]["s"]
            self.full_history[role].at[week, 'C3_NewOrder'] = inputs[role]["d"]
            self.full_history[role].at[week, 'C4_Final'] = c4
            self.full_history[role].at[week, 'C5_OrderDec'] = order_dec
            
            current_results[role] = actual_ship
            
        # 물류 및 정보 흐름 업데이트
        self.order_delay["Wholesaler"].append(self.full_history["Retailer"].at[week, 'C5_OrderDec'])
        self.order_delay["Distributor"].append(self.full_history["Wholesaler"].at[week, 'C5_OrderDec'])
        self.order_delay["Factory"].append(self.full_history["Distributor"].at[week, 'C5_OrderDec'])
        
        self.supply_delay["Retailer"].append(current_results["Wholesaler"])
        self.supply_delay["Wholesaler"].append(current_results["Distributor"])
        self.supply_delay["Distributor"].append(current_results["Factory"])
        self.supply_delay["Factory"].append(self.full_history["Factory"].at[week, 'C5_OrderDec'])

# --- 3. 세션 초기화 ---
CUSTOMER_ORDERS = [4, 4, 10, 8, 9, 8, 8, 10, 4, 4, 5, 3, 8, 8, 9, 8, 7, 8, 10, 11, 8, 7, 8, 10, 7, 7, 8, 7, 10, 9]
if "chain" not in st.session_state:
    st.session_state.chain = BeerGameChain()
    st.session_state.week = 1

# --- 4. 메인 인터페이스 ---
st.title("🍺 Beer Game: Professional Research Board")
user_role = st.sidebar.selectbox("내 역할", ["Retailer", "Wholesaler", "Distributor", "Factory"])
if st.sidebar.button("시뮬레이션 초기화"):
    st.session_state.chain = BeerGameChain(); st.session_state.week = 1; st.rerun()

is_finished = st.session_state.week > 30

# --- 보드판 구역 (완전 분리형 박스) ---
cols = st.columns(4)
role_colors = {"Retailer": "#0056b3", "Wholesaler": "#28a745", "Distributor": "#333", "Factory": "#d62728"}

for i, role in enumerate(st.session_state.chain.roles):
    is_me = (role == user_role) or is_finished
    with cols[i]:
        st.markdown(f"<div class='board-title' style='color:{role_colors[role]}'>{role.upper()}</div>", unsafe_allow_html=True)
        
        # 1. Incoming Order
        val_order = "END" if is_finished else (CUSTOMER_ORDERS[st.session_state.week-1] if role=="Retailer" else st.session_state.chain.order_delay[role][0])
        st.markdown(f"<div class='unit-box order-style'><div class='label-text'>INCOMING ORDER</div><div class='value-text'>{val_order if is_me else '???'}</div></div>", unsafe_allow_html=True)
        
        # 2. Inventory
        curr_inv = st.session_state.chain.inventory[role] if st.session_state.chain.backorder[role] == 0 else -st.session_state.chain.backorder[role]
        st.markdown(f"<div class='unit-box inv-style'><div class='label-text'>INVENTORY</div><div class='value-text'>{curr_inv if is_me else '???'}</div></div>", unsafe_allow_html=True)
        
        # 3. Truck & Train (Shipments)
        s1, s2 = st.columns(2)
        with s1: st.markdown(f"<div class='unit-box ship-style'><div class='label-text'>TRUCK</div><div class='value-text' style='font-size:1.5em'>{st.session_state.chain.supply_delay[role][1] if is_me else '?'}</div></div>", unsafe_allow_html=True)
        with s2: st.markdown(f"<div class='unit-box ship-style'><div class='label-text'>TRAIN</div><div class='value-text' style='font-size:1.5em'>{st.session_state.chain.supply_delay[role][0] if is_me else '?'}</div></div>", unsafe_allow_html=True)

st.divider()

# --- 5. 인터렉티브 제어 구역 ---
if not is_finished:
    c_ctl, c_space = st.columns([1, 2])
    with c_ctl:
        st.subheader(f"📅 Week {st.session_state.week} Action")
        
        # 단계별 인터렉션
        step1 = st.checkbox("🚚 1. 물류 입고 확인 (Truck/Train)")
        step2 = st.checkbox("📩 2. 새로운 주문 확인", disabled=not step1)
        
        if step2:
            st.write("📈 3. 발주 수량 결정")
            order_input = st.select_slider("결정량 선택", options=list(range(0, 51)), value=4)
            if st.button("물건 발송 및 주차 종료", type="primary"):
                st.session_state.chain.proceed_week(st.session_state.week, user_role, order_input, CUSTOMER_ORDERS[st.session_state.week-1])
                st.session_state.week += 1
                st.rerun()

# --- 6. 전면 회계 장부 (30주차 전체 노출) ---
st.subheader(f"📋 {user_role} Full Accounting Sheet (Week 1-30)")
display_df = st.session_state.chain.full_history[user_role].copy()
display_df.index.name = "Week"
display_df.columns = ["기초재고(C1)", "배송도착(C2)", "새 주문(C3)", "기말재고(C4)", "주문결정(C5)"]

# 데이터가 없는 곳은 빈칸으로 표시되도록 처리
st.table(display_df.fillna(""))
