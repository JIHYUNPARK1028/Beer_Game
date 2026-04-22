import streamlit as st
import pandas as pd
import altair as alt
import random

# 1. 페이지 설정
st.set_page_config(page_title="Beer Game Virtual Board", layout="wide")

# --- 보드판 스타일 (CSS) ---
st.markdown("""
    <style>
    .node-container {
        border: 4px solid #333;
        border-radius: 15px;
        background-color: #fcfcfc;
        padding: 15px;
        text-align: center;
        min-height: 480px;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.1);
    }
    .section-label {
        font-size: 0.7em;
        font-weight: bold;
        color: #777;
        margin-bottom: 2px;
        text-transform: uppercase;
    }
    .data-box {
        border: 2px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        background-color: white;
    }
    .inv-value {
        font-size: 2.8em;
        font-weight: bold;
        color: #1f77b4;
        line-height: 1;
    }
    .order-value {
        font-size: 1.8em;
        font-weight: bold;
        color: #d62728;
    }
    .delay-box {
        display: flex;
        justify-content: space-between;
        gap: 5px;
    }
    .delay-item {
        flex: 1;
        border: 1px solid #eee;
        border-radius: 5px;
        padding: 5px;
        background-color: #f9f9f9;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 로직 클래스 (파일 통합) ---
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
            
            # 컴퓨터 난수 알고리즘 (주문량 + 0~20)
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

# --- 3. 세션 관리 ---
CUSTOMER_ORDERS = [4, 4, 10, 8, 9, 8, 8, 10, 4, 4, 5, 3, 8, 8, 9, 8, 7, 8, 10, 11, 8, 7, 8, 10, 7, 7, 8, 7, 10, 9]
MAX_WEEKS = len(CUSTOMER_ORDERS)

if "chain" not in st.session_state:
    st.session_state.chain = BeerGameChain()
    st.session_state.history = []
    st.session_state.week = 1

# --- 4. 메인 화면 및 보드판 ---
st.title("🍻 Beer Game Virtual Physical Board")
user_role = st.sidebar.selectbox("내 역할 선택", ["Retailer", "Wholesaler", "Distributor", "Factory"])
if st.sidebar.button("게임 리셋"):
    st.session_state.chain = BeerGameChain(); st.session_state.history = []; st.session_state.week = 1; st.rerun()

is_finished = st.session_state.week > MAX_WEEKS

# 보드판 렌더링
cols = st.columns(4)
colors = {"Retailer": "#0056b3", "Wholesaler": "#28a745", "Distributor": "#333", "Factory": "#d62728"}

for i, role in enumerate(st.session_state.chain.roles):
    node = st.session_state.chain.nodes[role]
    is_me = (role == user_role) or is_finished
    
    with cols[i]:
        # 이미지의 'U'자형 흐름 구획 재현
        stock = node.inventory if node.backorder == 0 else -node.backorder
        inc_order = "END" if is_finished else (CUSTOMER_ORDERS[st.session_state.week-1] if role=="Retailer" else st.session_state.chain.order_delay[role][0])
        
        st.markdown(f"""
            <div class="node-container" style="border-color: {colors[role] if is_me else '#ddd'};">
                <div style="background-color:{colors[role]}; color:white; border-radius:5px; padding:5px; margin-bottom:15px;">
                    <b style="font-size:1.2em;">{role.upper()}</b><br>
                    <small>{'PLAYER' if role==user_role else 'COMPUTER'}</small>
                </div>
                
                <div class="section-label">Incoming Orders (포스트잇)</div>
                <div class="data-box order-value">{inc_order if is_me else '???'}</div>
                
                <div class="section-label">Current Inventory (칩 더미)</div>
                <div class="data-box inv-value">{stock if is_me else '???'}</div>
                
                <div class="section-label">Incoming Shipments (물류 대기)</div>
                <div class="delay-box">
                    <div class="delay-item"><small>Truck</small><br><b>{st.session_state.chain.supply_delay[role][1] if is_me else '?'}</b></div>
                    <div class="delay-item"><small>Train</small><br><b>{st.session_state.chain.supply_delay[role][0] if is_me else '?'}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# 5. 하단 제어창
if not is_finished:
    c_input, c_sheet = st.columns([1, 2])
    with c_input:
        st.subheader(f"📅 Week {st.session_state.week} Decision")
        order_val = st.number_input("이번 주 발주 결정량(C5):", min_value=0, value=4)
        if st.button("결정 완료 (Confirm)", type="primary"):
            res = st.session_state.chain.proceed_week(st.session_state.week, user_role, order_val, CUSTOMER_ORDERS[st.session_state.week-1])
            st.session_state.history.append(res)
            st.session_state.week += 1
            st.rerun()
    
    with c_sheet:
        st.subheader("📋 My Accounting Sheet")
        if st.session_state.history:
            my_data = [w[user_role] for w in st.session_state.history]
            df = pd.DataFrame(my_data)[['Week', 'C1_Initial', 'C2_Arrived', 'C3_NewOrder', 'C4_Final', 'C5_OrderDec']]
            df.columns = ['주차', '기초재고', '배송입고', '받은주문', '기말재고', '나의발주']
            st.table(df.sort_values('주차', ascending=False).head(5))
else:
    st.header("📊 결과 분석 (Analysis)")
    # (이전 비용 계산 및 그래프 로직 동일...)
