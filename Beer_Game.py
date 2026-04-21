# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:29:31 2026

@author: admir
"""

import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="Beer Game - Strategic Board", layout="wide")

# --- 상수 데이터 ---
CUSTOMER_ORDERS = [4, 4, 10, 8, 9, 8, 8, 10, 4, 4, 5, 3, 8, 8, 9, 8, 7, 8, 10, 11, 8, 7, 8, 10, 7, 7, 8, 7, 10, 9]
MAX_WEEKS = len(CUSTOMER_ORDERS)

# --- 로직 클래스 ---
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
            res.update({"C6_Order": order_decision, "Role": role, "Week": week, "C3_Demand": current_inputs[role]["demand"], "C2_Arrived": current_inputs[role]["supply"]})
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

# --- 스타일 정의 (사진의 레이아웃 + 보안 적용) ---
def render_fog_of_war_board(chain, user_role):
    cols = st.columns(4)
    # 사진의 이미지 순서와 동일: Retailer -> Wholesaler -> Distributor -> Factory
    colors = {"Retailer": "#0056b3", "Wholesaler": "#28a745", "Distributor": "#333", "Factory": "#dc3545"}
    
    for i, role in enumerate(chain.roles):
        node = chain.nodes[role]
        color = colors[role]
        is_me = (role == user_role)
        
        with cols[i]:
            # 나만 볼 수 있는 데이터 처리
            display_inv = f"{node.inventory if node.backorder == 0 else -node.backorder}" if is_me else "???"
            display_incoming = ""
            if role == 'Retailer':
                display_incoming = f"{CUSTOMER_ORDERS[st.session_state.week-1]}"
            else:
                display_incoming = f"{chain.order_delay[role][0]}" if is_me else "???"
            
            display_truck = f"{chain.supply_delay[role][1]}" if is_me else "?"
            display_train = f"{chain.supply_delay[role][0]}" if is_me else "?"

            st.markdown(f"""
                <div style="border: 4px solid {color if is_me else '#ddd'}; border-radius: 12px; padding: 20px; text-align: center; background-color: {'#fff' if is_me else '#f1f1f1'}; opacity: {1.0 if is_me else 0.6};">
                    <h2 style="color: {color if is_me else '#888'}; margin-bottom: 5px;">{role.upper()}</h2>
                    <p style="font-size: 0.8em; color: gray;">{"(나의 역할)" if is_me else "(상대방)"}</p>
                    <hr>
                    <div style="margin-bottom: 15px;">
                        <span style="font-size: 0.85em; color: #555;">📥 이번 주 받은 주문</span><br>
                        <b style="font-size: 1.8em; color: red;">{display_incoming}</b>
                    </div>
                    <div style="background-color: {'#eef' if is_me else '#eee'}; border: 2px solid #ccc; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                        <span style="font-size: 0.9em; font-weight: bold;">현재 재고 현황</span><br>
                        <b style="font-size: 3em; color: {color if is_me else '#888'};">{display_inv}</b>
                    </div>
                    <div style="display: flex; justify-content: space-around; border-top: 1px solid #ddd; padding-top: 10px;">
                        <div><small>Truck Delay</small><br><b style="color:blue;">{display_truck}</b></div>
                        <div><small>Train Delay</small><br><b style="color:blue;">{display_train}</b></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- 사이드바 설정 ---
st.sidebar.header("🎮 GAME SETTINGS")
user_role = st.sidebar.radio("자신의 역할을 선택하세요", ["Retailer", "Wholesaler", "Distributor", "Factory"])
if st.sidebar.button("게임 리셋"):
    st.session_state.chain = BeerGameChain(); st.session_state.history = []; st.session_state.week = 1; st.rerun()

# --- 메인 화면 ---
st.title("🍺 Beer Game Board Simulation")
st.info(f"📅 **Week {st.session_state.week}** / {MAX_WEEKS}")

# 상단 비주얼 보드판 (포그 오브 워 적용)
render_fog_of_war_board(st.session_state.chain, user_role)

st.divider()

# 하단 인터랙션 영역
if st.session_state.week <= MAX_WEEKS:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📝 주문 의사결정")
        order_val = st.number_input(f"{user_role}의 이번 주 발주량:", min_value=0, value=4)
        if st.button("주문 확정 (Next Week)", use_container_width=True, type="primary"):
            c_demand = CUSTOMER_ORDERS[st.session_state.week - 1]
            res = st.session_state.chain.proceed_week(st.session_state.week, user_role, order_val, c_demand)
            st.session_state.history.append(res)
            st.session_state.week += 1
