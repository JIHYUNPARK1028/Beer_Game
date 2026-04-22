import streamlit as st
import pandas as pd
import random

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="Beer Game Station", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f4f9; }
    .station-title { text-align: center; font-size: 2.5em; font-weight: bold; margin-bottom: 20px; color: #333; }
    .component-card {
        background-color: white; border-radius: 15px; padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px;
    }
    .label { font-size: 0.9em; color: #666; font-weight: bold; margin-bottom: 10px; }
    .value { font-size: 3em; font-weight: bold; }
    .order-card { border-top: 8px solid #ff4b4b; }
    .inv-card { border-top: 8px solid #1f77b4; }
    .delay-card { border-top: 8px solid #2ca02c; }
    .production-card { border-top: 8px solid #9467bd; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 로직 클래스 ---
class BeerGameChain:
    def __init__(self):
        self.roles = ["Retailer", "Wholesaler", "Distributor", "Factory"]
        self.inventory = {role: 8 for role in self.roles}
        self.backorder = {role: 0 for role in self.roles}
        self.order_delay = {r: [4, 4] for r in ["Wholesaler", "Distributor", "Factory"]}
        self.supply_delay = {r: [4, 4] for r in self.roles}
        self.full_history = {role: pd.DataFrame(index=range(1, 31), 
                            columns=['C1', 'C2', 'C3', 'C4', 'C5']) for role in self.roles}

    def proceed_week(self, week, user_role, user_order, consumer_demand):
        inputs = {
            "Retailer": {"d": consumer_demand, "s": self.supply_delay["Retailer"].pop(0)},
            "Wholesaler": {"d": self.order_delay["Wholesaler"].pop(0), "s": self.supply_delay["Wholesaler"].pop(0)},
            "Distributor": {"d": self.order_delay["Distributor"].pop(0), "s": self.supply_delay["Distributor"].pop(0)},
            "Factory": {"d": self.order_delay["Factory"].pop(0), "s": self.supply_delay["Factory"].pop(0)}
        }
        
        actual_shipments = {}
        for role in self.roles:
            c1 = self.inventory[role] if self.backorder[role] == 0 else -self.backorder[role]
            self.inventory[role] += inputs[role]["s"]
            total_demand = inputs[role]["d"] + self.backorder[role]
            ship = min(self.inventory[role], total_demand)
            self.inventory[role] -= ship
            self.backorder[role] = total_demand - ship
            c4 = self.inventory[role] if self.backorder[role] == 0 else -self.backorder[role]
            
            order_dec = user_order if role == user_role else inputs[role]["d"] + random.randint(0, 5)
            
            self.full_history[role].at[week, 'C1'] = c1
            self.full_history[role].at[week, 'C2'] = inputs[role]["s"]
            self.full_history[role].at[week, 'C3'] = inputs[role]["d"]
            self.full_history[role].at[week, 'C4'] = c4
            self.full_history[role].at[week, 'C5'] = order_dec
            actual_shipments[role] = ship

        # 물리적 흐름 업데이트
        self.order_delay["Wholesaler"].append(self.full_history["Retailer"].at[week, 'C5'])
        self.order_delay["Distributor"].append(self.full_history["Wholesaler"].at[week, 'C5'])
        self.order_delay["Factory"].append(self.full_history["Distributor"].at[week, 'C5'])
        self.supply_delay["Retailer"].append(actual_shipments["Wholesaler"])
        self.supply_delay["Wholesaler"].append(actual_shipments["Distributor"])
        self.supply_delay["Distributor"].append(actual_shipments["Factory"])
        self.supply_delay["Factory"].append(self.full_history["Factory"].at[week, 'C5'])

# --- 3. 세션 관리 ---
CUSTOMER_ORDERS = [4, 4, 10, 8, 9, 8, 8, 10, 4, 4, 5, 3, 8, 8, 9, 8, 7, 8, 10, 11, 8, 7, 8, 10, 7, 7, 8, 7, 10, 9]
if "chain" not in st.session_state:
    st.session_state.chain = BeerGameChain()
    st.session_state.week = 1

# --- 4. 역할 선택 및 헤더 ---
user_role = st.sidebar.selectbox("역할(Station) 선택", ["Retailer", "Wholesaler", "Distributor", "Factory"])
if st.sidebar.button("게임 초기화"):
    st.session_state.chain = BeerGameChain(); st.session_state.week = 1; st.rerun()

st.markdown(f"<div class='station-title'>{user_role.upper()} STATION</div>", unsafe_allow_html=True)

# --- 5. 역할별 맞춤 보드 레이아웃 ---
def draw_card(label, value, card_class="inv-card"):
    st.markdown(f"""
        <div class="component-card {card_class}">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

chain = st.session_state.chain
week = st.session_state.week

# 역할에 따라 구성 요소를 다르게 배치
if user_role == "Retailer":
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1: draw_card("ORDERS SOLD (C3)", CUSTOMER_ORDERS[week-1], "order-card")
    with col2: draw_card("INVENTORY (C4)", chain.inventory["Retailer"] if chain.backorder["Retailer"]==0 else -chain.backorder["Retailer"])
    with col3: 
        st.write("🚚 **DELAYS (Incoming)**")
        draw_card("Truck", chain.supply_delay["Retailer"][1], "delay-card")
        draw_card("Train", chain.supply_delay["Retailer"][0], "delay-card")

elif user_role in ["Wholesaler", "Distributor"]:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.write("📥 **INCOMING**")
        draw_card("Order Delay", chain.order_delay[user_role][0], "order-card")
        draw_card("Shipment Delay (Truck)", chain.supply_delay[user_role][1], "delay-card")
    with col2:
        draw_card("INVENTORY", chain.inventory[user_role] if chain.backorder[user_role]==0 else -chain.backorder[user_role])
    with col3:
        st.write("📤 **OUTGOING**")
        draw_card("Shipment Delay (Train)", chain.supply_delay[user_role][0], "delay-card")

elif user_role == "Factory":
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        draw_card("INCOMING ORDERS", chain.order_delay["Factory"][0], "order-card")
        draw_card("RAW MATERIALS", chain.supply_delay["Factory"][1], "delay-card")
    with col2:
        draw_card("INVENTORY", chain.inventory["Factory"] if chain.backorder["Factory"]==0 else -chain.backorder["Factory"])
    with col3:
        st.write("🏭 **PRODUCTION**")
        draw_card("Production Delay 1", chain.supply_delay["Factory"][1], "production-card")
        draw_card("Production Delay 2", chain.supply_delay["Factory"][0], "production-card")

st.divider()

# --- 6. 인터렉티브 액션 및 장부 ---
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader(f"Week {week} 의사결정")
    s1 = st.checkbox("1. 배송물 및 주문서 확인")
    if s1:
        order_val = st.number_input("2. 발주량 결정 (C5):", min_value=0, value=4)
        if st.button("물건 보내기 (주차 종료)", type="primary"):
            chain.proceed_week(week, user_role, order_val, CUSTOMER_ORDERS[week-1])
            st.session_state.week += 1
            st.rerun()

with c2:
    st.subheader("📊 30주 전면 회계 장부")
    df = chain.full_history[user_role].copy()
    df.columns = ['기초재고(C1)', '배송도착(C2)', '받은주문(C3)', '기말재고(C4)', '발주결정(C5)']
    st.dataframe(df.fillna(""), height=400, use_container_width=True)
