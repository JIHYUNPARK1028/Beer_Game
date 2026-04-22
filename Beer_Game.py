import streamlit as st
import pandas as pd
import altair as alt
import random

# 1. 페이지 설정 및 디자인 CSS
st.set_page_config(page_title="Interactive Beer Game", layout="wide")

st.markdown("""
    <style>
    .element-container { margin-bottom: 1rem; }
    .stButton>button { width: 100%; border-radius: 20px; }
    /* 보드판 개별 박스 스타일 */
    .board-box {
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
        text-align: center;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .order-card { background-color: #fff5f5; border: 2px dashed #ff4b4b; }
    .inv-card { background-color: #e7f3ff; border: 3px solid #1f77b4; }
    .ship-card { background-color: #f0fff0; border: 2px solid #2ca02c; }
    .label { font-size: 0.8em; color: #666; font-weight: bold; }
    .value { font-size: 2em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 로직 클래스 (기존 로직 유지) ---
class BeerGameNode:
    def __init__(self, role_name):
        self.role_name = role_name
        self.inventory = 8
        self.backorder = 0

    def calculate_step(self, incoming_order, arrived_supply):
        self.inventory += arrived_supply
        total_demand = incoming_order + self.backorder
        actual_ship = min(self.inventory, total_demand)
        self.inventory -= actual_ship
        self.backorder = total_demand - actual_ship
        return {"Shipment": actual_ship, "Inv": self.inventory, "Back": self.backorder}

class BeerGameChain:
    def __init__(self):
        self.roles = ["Retailer", "Wholesaler", "Distributor", "Factory"]
        self.nodes = {role: BeerGameNode(role) for role in self.roles}
        self.order_delay = {"Wholesaler": [4, 4], "Distributor": [4, 4], "Factory": [4, 4]}
        self.supply_delay = {"Retailer": [4, 4], "Wholesaler": [4, 4], "Distributor": [4, 4], "Factory": [4, 4]}

    def proceed_week(self, week, user_role, user_order, consumer_demand):
        results = {}
        inputs = {
            "Retailer": {"d": consumer_demand, "s": self.supply_delay["Retailer"].pop(0)},
            "Wholesaler": {"d": self.order_delay["Wholesaler"].pop(0), "s": self.supply_delay["Wholesaler"].pop(0)},
            "Distributor": {"d": self.order_delay["Distributor"].pop(0), "s": self.supply_delay["Distributor"].pop(0)},
            "Factory": {"d": self.order_delay["Factory"].pop(0), "s": self.supply_delay["Factory"].pop(0)}
        }
        for role in self.roles:
            init_stock = self.nodes[role].inventory if self.nodes[role].backorder == 0 else -self.nodes[role].backorder
            res = self.nodes[role].calculate_step(inputs[role]["d"], inputs[role]["s"])
            order_dec = user_order if role == user_role else inputs[role]["d"] + random.randint(0, 20)
            
            res.update({
                "Week": week, "Role": role, "C1_Initial": init_stock, "C2_Arrived": inputs[role]["s"],
                "C3_NewOrder": inputs[role]["d"], "C4_Final": (res["Inv"] if res["Back"]==0 else -res["Back"]),
                "C5_OrderDec": order_dec, "Weekly_Cost": res["Inv"]*1 + res["Back"]*2
            })
            results[role] = res
            
            if role == "Retailer": self.order_delay["Wholesaler"].append(order_dec)
            elif role == "Wholesaler":
                self.order_delay["Distributor"].append(order_dec); self.supply_delay["Retailer"].append(res["Shipment"])
            elif role == "Distributor":
                self.order_delay["Factory"].append(order_dec); self.supply_delay["Wholesaler"].append(res["Shipment"])
            elif role == "Factory":
                self.supply_delay["Distributor"].append(res["Shipment"]); self.supply_delay["Factory"].append(order_dec)
        return results

# --- 3. 데이터 및 세션 ---
CUSTOMER_ORDERS = [4, 4, 10, 8, 9, 8, 8, 10, 4, 4, 5, 3, 8, 8, 9, 8, 7, 8, 10, 11, 8, 7, 8, 10, 7, 7, 8, 7, 10, 9]
if "chain" not in st.session_state:
    st.session_state.chain = BeerGameChain()
    st.session_state.history = []
    st.session_state.week = 1
    st.session_state.step = 0 # 인터렉티브 단계를 위한 변수

# --- 4. 메인 화면 ---
st.title("🍺 Beer Game: Interactive Board")

user_role = st.sidebar.selectbox("내 역할 선택", ["Retailer", "Wholesaler", "Distributor", "Factory"])
if st.sidebar.button("게임 리셋"):
    st.session_state.chain = BeerGameChain(); st.session_state.history = []; st.session_state.week = 1; st.session_state.step = 0; st.rerun()

is_finished = st.session_state.week > len(CUSTOMER_ORDERS)

# --- 5. 보드판 렌더링 (개별 박스 분리) ---
cols = st.columns(4)
colors = {"Retailer": "#0056b3", "Wholesaler": "#28a745", "Distributor": "#333", "Factory": "#d62728"}

for i, role in enumerate(st.session_state.chain.roles):
    node = st.session_state.chain.nodes[role]
    is_me = (role == user_role) or is_finished
    
    with cols[i]:
        st.markdown(f"<h3 style='text-align:center; color:{colors[role]};'>{role.upper()}</h3>", unsafe_allow_html=True)
        
        # 1. Incoming Order Box
        inc_order = "END" if is_finished else (CUSTOMER_ORDERS[st.session_state.week-1] if role=="Retailer" else st.session_state.chain.order_delay[role][0])
        st.markdown(f"<div class='board-box order-card'><div class='label'>INCOMING ORDER</div><div class='value'>{inc_order if is_me else '???'}</div></div>", unsafe_allow_html=True)
        
        # 2. Inventory Box
        stock = node.inventory if node.backorder == 0 else -node.backorder
        st.markdown(f"<div class='board-box inv-card'><div class='label'>INVENTORY</div><div class='value'>{stock if is_me else '???'}</div></div>", unsafe_allow_html=True)
        
        # 3. Shipments (Truck/Train) 분리
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown(f"<div class='board-box ship-card'><div class='label'>TRUCK</div><div class='value' style='font-size:1.2em;'>{st.session_state.chain.supply_delay[role][1] if is_me else '?'}</div></div>", unsafe_allow_html=True)
        with t_col2:
            st.markdown(f"<div class='board-box ship-card'><div class='label'>TRAIN</div><div class='value' style='font-size:1.2em;'>{st.session_state.chain.supply_delay[role][0] if is_me else '?'}</div></div>", unsafe_allow_html=True)

st.divider()

# --- 6. 인터렉티브 제어 구역 (단계별 진행) ---
if not is_finished:
    st.subheader(f"📅 Week {st.session_state.week} - 진행 단계")
    
    # 실제 보드판 게임처럼 단계별로 확인하도록 구성
    step_cols = st.columns(3)
    
    with step_cols[0]:
        check_arrived = st.checkbox("1. 배송 도착 확인 (Truck/Train)", key="s1")
        if check_arrived: st.info("물건이 창고에 입고되었습니다.")
        
    with step_cols[1]:
        check_order = st.checkbox("2. 새 주문 확인 (Incoming Order)", key="s2", disabled=not check_arrived)
        if check_order: st.warning(f"이번 주 수요는 {inc_order}개 입니다.")
        
    with step_cols[2]:
        if check_order:
            st.write("3. 발주 결정 (Order Placed)")
            order_val = st.slider("수량을 선택하세요", 0, 50, 4)
            if st.button("물건 보내기 및 주문 완료", type="primary"):
                res = st.session_state.chain.proceed_week(st.session_state.week, user_role, order_val, CUSTOMER_ORDERS[st.session_state.week-1])
                st.session_state.history.append(res)
                st.session_state.week += 1
                st.rerun()
        else:
            st.write("앞의 단계를 먼저 진행하세요.")

    # 하단 회계 장부
    with st.expander("📊 실시간 회계 장부 확인", expanded=True):
        if st.session_state.history:
            my_data = [w[user_role] for w in st.session_state.history]
            df = pd.DataFrame(my_data)[['Week', 'C1_Initial', 'C2_Arrived', 'C3_NewOrder', 'C4_Final', 'C5_OrderDec']]
            df.columns = ['주차', '기초재고', '배송입고', '받은주문', '기말재고', '나의발주']
            st.table(df.sort_values('주차', ascending=False).head(5))
