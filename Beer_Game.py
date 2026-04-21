# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:29:31 2026

@author: admir
"""

import streamlit as st
import pandas as pd
import altair as alt
import random

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
        # 1. 기초 재고 (C1) = 지난 주의 기말재고 (이미 self.inventory에 저장됨)
        # 2. 배송 도착 (C2) 처리
        self.inventory += arrived_supply
        
        # 3. 새로운 주문 (C3) + 지난 이월주문 처리
        total_demand = incoming_order + self.backorder
        
        # 4. 실제 배송 및 기말재고(C4) 계산
        actual_ship = min(self.inventory, total_demand)
        self.inventory -= actual_ship
        self.backorder = total_demand - actual_ship
        
        return {
            "Shipment": actual_ship, 
            "Inv": self.inventory, 
            "Back": self.backorder,
            "Stock_Level": self.inventory if self.backorder == 0 else -self.backorder
        }

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
            initial_stock = self.nodes[role].inventory if self.nodes[role].backorder == 0 else -self.nodes[role].backorder
            res = self.nodes[role].calculate_step(current_inputs[role]["demand"], current_inputs[role]["supply"])
            
            # --- 알고리즘 수정 부분 ---
            if role == user_role:
                order_decision = user_order
            else:
                # 컴퓨터 알고리즘: 받은 주문량(demand) + (0~20 사이의 난수)
                noise = random.randint(0, 20)
                order_decision = current_inputs[role]["demand"] + noise
            # ------------------------
            
            weekly_cost = res["Inv"] * 1 + res["Back"] * 2
            
            res.update({
                "Week": week, "Role": role,
                "C1_Initial": initial_stock,
                "C2_Arrived": current_inputs[role]["supply"],
                "C3_NewOrder": current_inputs[role]["demand"],
                "C4_Final": res["Stock_Level"],
                "C5_OrderDec": order_decision,
                "Weekly_Cost": weekly_cost
            })
            results[role] = res
            
            # 물류 및 정보 흐름 업데이트
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

# --- 스타일 및 보드판 ---
def render_board(chain, user_role, is_finished=False):
    cols = st.columns(4)
    colors = {"Retailer": "#0056b3", "Wholesaler": "#28a745", "Distributor": "#333", "Factory": "#dc3545"}
    
    for i, role in enumerate(chain.roles):
        node = chain.nodes[role]
        color = colors[role]
        is_visible = True if is_finished else (role == user_role)
        
        with cols[i]:
            stock = node.inventory if node.backorder == 0 else -node.backorder
            display_stock = f"{stock}" if is_visible else "???"
            
            st.markdown(f"""
                <div style="border: 3px solid {color if is_visible else '#ddd'}; border-radius: 10px; padding: 15px; text-align: center; background-color: white;">
                    <h3 style="color: {color}; margin:0;">{role.upper()}</h3>
                    <p style="font-size: 0.8em; color: gray;">{"(You)" if role == user_role else "(Opponent)"}</p>
                    <div style="background-color: #f1f3f5; padding: 10px; border-radius: 5px;">
                        <small>현재 재고</small><br><b style="font-size: 2em;">{display_stock}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- 메인 레이아웃 ---
st.title("🍺 Beer Game: Strategic Supply Chain")
is_finished = st.session_state.week > MAX_WEEKS

# 사이드바 역할 선택
user_role = st.sidebar.selectbox("내 역할 확인", ["Retailer", "Wholesaler", "Distributor", "Factory"])
if st.sidebar.button("게임 초기화"):
    st.session_state.chain = BeerGameChain(); st.session_state.history = []; st.session_state.week = 1; st.rerun()

# 상단 현황판
render_board(st.session_state.chain, user_role, is_finished)

st.divider()

if not is_finished:
    # 1. 입력 섹션
    col_in, col_space = st.columns([1, 2])
    with col_in:
        st.subheader(f"📅 Week {st.session_state.week} 주문 결정")
        order_val = st.number_input("이번 주 발주량(C6):", min_value=0, value=4, step=1)
        if st.button("주문 확정 및 다음 주로 이동", type="primary"):
            res = st.session_state.chain.proceed_week(st.session_state.week, user_role, order_val, CUSTOMER_ORDERS[st.session_state.week-1])
            st.session_state.history.append(res)
            st.session_state.week += 1
            st.rerun()

    # 2. 하단 회계 장부 (Accounting Sheet)
    st.subheader(f"📋 {user_role} 회계 장부 (Accounting Sheet)")
    if st.session_state.history:
        # 내 역할의 기록만 필터링
        my_data = [w[user_role] for w in st.session_state.history]
        df_sheet = pd.DataFrame(my_data)
        
        # 제공된 워드 양식 컬럼명 반영
        df_sheet = df_sheet[['Week', 'C1_Initial', 'C2_Arrived', 'C3_NewOrder', 'C4_Final', 'C5_OrderDec']]
        df_sheet.columns = ['Week', '(C1) 기초재고', '(C2) 배송도착', '(C3) 새 주문', '(C4) 기말재고', '(C5) 주문결정']
        
        # 최신 데이터가 위로 오게 하거나, 전체 흐름을 보게 함
        st.table(df_sheet.sort_values('Week', ascending=False))
    else:
        st.info("첫 주차 주문을 완료하면 회계 장부가 기록되기 시작합니다.")

else:
    # 종료 후 분석 리포트
    st.header("🏁 Game Over: Supply Chain Analysis")
    flat_data = [d for w in st.session_state.history for d in w.values()]
    full_df = pd.DataFrame(flat_data)
    
    # 전체 비용 요약
    summary = full_df.groupby('Role')['Weekly_Cost'].sum().reset_index()
    st.dataframe(summary.rename(columns={'Role':'역할', 'Weekly_Cost':'총 누적 비용($)'}))
    
    # 채찍효과 그래프
    chart = alt.Chart(full_df).mark_line(point=True).encode(
        x='Week:O', y='C5_OrderDec:Q', color='Role:N', tooltip=['Role', 'Week', 'C5_OrderDec']
    ).properties(title="주문량 변화 (Bullwhip Effect)", height=400).interactive()
    st.altair_chart(chart, use_container_width=True)
