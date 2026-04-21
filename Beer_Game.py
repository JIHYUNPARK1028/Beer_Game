# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:29:31 2026

@author: admir
"""

import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="Beer Game Visual Board", layout="wide")

# --- 상수 데이터 ---
CUSTOMER_ORDERS = [4, 4, 10, 8, 9, 8, 8, 10, 4, 4, 5, 3, 8, 8, 9, 8, 7, 8, 10, 11, 8, 7, 8, 10, 7, 7, 8, 7, 10, 9]
MAX_WEEKS = len(CUSTOMER_ORDERS)

# --- 로직 클래스 (이전과 동일하되 시각화 데이터 보강) ---
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
        current_inputs = {
            "Retailer": {"demand": consumer_demand, "supply": self.supply_delay["Retailer"].pop(0)},
            "Wholesaler": {"demand": self.order_delay["Wholesaler"].pop(0), "supply": self.supply_delay["Wholesaler"].pop(0)},
            "Distributor": {"demand": self.order_delay["Distributor"].pop(0), "supply": self.supply_delay["Distributor"].pop(0)},
            "Factory": {"demand": self.order_delay["Factory"].pop(0), "supply": self.supply_delay["Factory"].pop(0)}
        }

        for role in self.roles:
            res = self.nodes[role].calculate_step(current_inputs[role]["demand"], current_inputs[role]["supply"])
            order_decision = user_order if role == user_role else current_inputs[role]["demand"]
            
            res.update({"C6_Order": order_decision, "Role": role, "Week": week, 
                        "C3_Demand": current_inputs[role]["demand"], "C2_Arrived": current_inputs[role]["supply"]})
            results[role] = res

            if role == "Retailer": self.order_delay["Wholesaler"].append(order_decision)
            elif role == "Wholesaler":
                self.order_delay["Distributor"].append(order_decision); self.supply_delay["Retailer"].append(res["Shipment"])
            elif role == "Distributor":
                self.order_delay["Factory"].append(order_decision); self.supply_delay["Wholesaler"].append(res["Shipment"])
            elif role == "Factory":
                self.supply_delay["Distributor"].append(res["Shipment"]); self.supply_delay["Factory"].append(order_decision)
        return results

# --- 세션 초기화 ---
if "chain" not in st.session_state:
    st.session_state.chain = BeerGameChain()
    st.session_state.history = []
    st.session_state.week = 1

# --- 스타일 정의 (사진의 레이아웃 재현) ---
def render_visual_board(chain, user_role):
    cols = st.columns(4)
    colors = {"Retailer": "#0056b3", "Wholesaler": "#28a745", "Distributor": "#333", "Factory": "#dc3545"}
    
    for i, role in enumerate(chain.roles):
        node = chain.nodes[role]
        color = colors[role]
        is_user = " (YOU)" if role == user_role else ""
        
        with cols[i]:
            # 사진의 각 노드 박스 디자인 구현
            st.markdown(f"""
                <div style="border: 3px solid {color}; border-radius: 10px; padding: 15px; text-align: center; background-color: white;">
                    <h3 style="color: {color}; margin-bottom: 5px;">{role.upper()}{is_user}</h3>
                    <div style="display: flex; justify-content: space-around; margin-bottom: 10px;">
                        <div style="font-size: 0.8em; color: gray;">ORDERS PLACED<br><b style="color:red; font-size:1.5em;">{chain.order_delay.get(chain.roles[i+1] if i<3 else "", [0,0])[-1] if i<3 else "-"}</b></div>
                        <div style="font-size: 0.8em; color: gray;">INCOMING ORDERS<br><b style="color:red; font-size:1.5em;">{chain.order_delay.get(role, [0,0])[0] if role != 'Retailer' else CUSTOMER_ORDERS[st.session_state.week-1]}</b></div>
                    </div>
                    <div style="background-color: #f8f9fa; border: 2px solid #ddd; padding: 10px; margin-bottom: 10px;">
                        <span style="font-size: 0.9em;">CURRENT INVENTORY</span><br>
                        <b style="font-size: 2.5em; color: {color};">{node.inventory if node.backorder == 0 else -node.backorder}</b>
                    </div>
                    <div style="display: flex; justify-content: space-around;">
                        <div style="font-size: 0.8em; color: gray;">TRUCK. DELAY<br><b style="color:blue; font-size:1.2em;">{chain.supply_delay[role][1]}</b></div>
                        <div style="font-size: 0.8em; color: gray;">TRAIN. DELAY<br><b style="color:blue; font-size:1.2em;">{chain.supply_delay[role][0]}</b></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- 메인 화면 구성 ---
st.sidebar.title("⚙️ SETTINGS")
user_role = st.sidebar.selectbox("역할 선택", ["Retailer", "Wholesaler", "Distributor", "Factory"])
if st.sidebar.button("게임 초기화"):
    st.session_state.chain = BeerGameChain(); st.session_state.history = []; st.session_state.week = 1; st.rerun()

st.title(f"🍻 Beer Game Simulation - Week {st.session_state.week}")

# 상단 비주얼 보드판 출력
render_visual_board(st.session_state.chain, user_role)

st.divider()

# 의사결정 및 입력 섹션
if st.session_state.week <= MAX_WEEKS:
    c_demand = CUSTOMER_ORDERS[st.session_state.week - 1]
    
    col_input, col_info = st.columns([1, 2])
    with col_input:
        st.subheader("📝 주문 결정")
        order_val = st.number_input("이번 주 발주 수량(C6):", min_value=0, value=4, step=1)
        if st.button("결정 완료", use_container_width=True):
            res = st.session_state.chain.proceed_week(st.session_state.week, user_role, order_val, c_demand)
            st.session_state.history.append(res)
            st.session_state.week += 1
            st.rerun()
    
    with col_info:
        st.subheader("💡 현재 상황 요약")
        my_node = st.session_state.chain.nodes[user_role]
        if user_role == "Retailer":
            st.warning(f"이번 주 소비자 주문(C3)은 **{c_demand} PKG** 입니다.")
        else:
            in_demand = st.session_state.chain.order_delay[user_role][0]
            st.info(f"이번 주 하위 단계로부터의 주문(C3)은 **{in_demand} PKG** 입니다.")
        
        if my_node.backorder > 0:
            st.error(f"⚠️ 현재 **{my_node.backorder} PKG**의 미납 주문이 발생했습니다! 빠른 배송이 필요합니다.")

# 데이터 시각화 (기존 탭 구조 유지)
if st.session_state.history:
    flat_data = [d for w in st.session_state.history for d in w.values()]
    df = pd.DataFrame(flat_data)
    
    tab1, tab2 = st.tabs(["📉 전체 공급망 주문 추이", "📋 상세 장부 기록"])
    with tab1:
        chart = alt.Chart(df).mark_line(point=True).encode(
            x='Week:O', y='C6_Order:Q', color='Role:N', tooltip=['Role', 'Week', 'C6_Order']
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)
    with tab2:
        st.dataframe(df[df['Role'] == user_role])
