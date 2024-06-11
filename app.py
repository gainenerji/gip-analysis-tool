import pandas as pd
import numpy as np
from datetime import date,timedelta
import warnings
import locale
import plotly.graph_objects as go
import requests

warnings.filterwarnings("ignore")

import streamlit as st
from streamlit_extras import add_vertical_space

locale.setlocale(locale.LC_ALL,"")
st.set_page_config(page_title="GİP Analiz Aracı", page_icon=":zap:", layout="wide")

st.title("GİP Analiz Aracı")

if "start_date" not in st.session_state:
    st.session_state.start_date = date.today() - timedelta(days=2)

if "end_date" not in st.session_state:
    st.session_state.end_date = date.today() - timedelta(days=1)

if "selected_contract" not in st.session_state:
    st.session_state.selected_contract = []

if "target_day_contracts" not in st.session_state:
    st.session_state.target_day_contracts = []

if "gip_history" not in st.session_state:
    gip_history = pd.DataFrame()
    st.session_state.gip_history = gip_history

if "target_contract_data" not in st.session_state:
    target_contract_data = pd.DataFrame()
    st.session_state.target_contract_data = target_contract_data

if "filtered_data" not in st.session_state:
    filtered_data = pd.DataFrame()
    st.session_state.filtered_data = filtered_data

if "zaman_filtre_tipi" not in st.session_state:
    st.session_state.zaman_filtre_tipi = "İlk-İlk"

if "hacim_filtre_tipi" not in st.session_state:
    st.session_state.hacim_filtre_tipi = "İlk-İlk"

start_date_str = st.session_state.start_date.strftime("%Y-%m-%dT00:00:00+03:00")
end_date_str = st.session_state.end_date.strftime("%Y-%m-%dT00:00:00+03:00")

day_year = st.session_state.end_date.strftime("%y")
day_month = st.session_state.end_date.strftime("%m")
day_day = st.session_state.end_date.strftime("%d")
day_contract_filter = "PH" + day_year + day_month + day_day

def transparency_call(method,service,endpoint,body,response_type):
    
    host = "https://seffaflik.epias.com.tr/"
    url = host + service + endpoint

    headers = {
        "Content-Type": "application/json",
    }

    response = requests.request(method, url, headers=headers, json=body)

    if response_type == "json":
        return response.json()
    elif response_type == "raw":
        return response
    elif response_type == "dataframe":
        return pd.DataFrame(response.json()["items"])
    
@st.cache_data
def get_history(start_date, end_date):
    gip_history_call = transparency_call(
        method = "POST",
        service = "electricity-service",
        endpoint = "/v1/markets/idm/data/transaction-history",
        body = {
            "startDate" : start_date,
            "endDate" : end_date,
        },
        response_type = "dataframe",
    )

    gip_history_call = gip_history_call.rename(columns={
    "date": "İşlem Zamanı",
    "price": "İşlem Fiyatı",
    "quantity": "Hacim",
    "contractName": "Kontrat",
    })

    gip_history_call = gip_history_call.drop(columns=["id","hour"])

    return gip_history_call

def time_filter(first_n_mins,last_n_mins,target_contract_data,filter_type):
    contract_opening_time = target_contract_data["İşlem Zamanı"].min()
    contract_closing_time = target_contract_data["İşlem Zamanı"].max()

    contract_opening_time = contract_opening_time.replace(minute=0, second=0, microsecond=0)
    contract_closing_time = contract_closing_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    if filter_type == "İlk-İlk":
        filter_opening_time = contract_opening_time + timedelta(minutes=first_n_mins)
        filter_closing_time = contract_opening_time + timedelta(minutes=last_n_mins)
    elif filter_type == "İlk-Son":
        filter_opening_time = contract_opening_time + timedelta(minutes=first_n_mins)
        filter_closing_time = contract_closing_time - timedelta(minutes=last_n_mins)
    elif filter_type == "Son-Son":
        filter_opening_time = contract_closing_time - timedelta(minutes=last_n_mins)
        filter_closing_time = contract_closing_time - timedelta(minutes=first_n_mins)
    return target_contract_data[(target_contract_data["İşlem Zamanı"] >= filter_opening_time) & (target_contract_data["İşlem Zamanı"] <= filter_closing_time)]

def quantity_filter(first_n_quantities,last_n_quantities,target_contract_data,filter_type):
    target_contract_data["Kümülatif Toplam"] = target_contract_data["Hacim"].cumsum()
    if filter_type == "İlk-İlk":
        filter_opening_quantity = first_n_quantities
        filter_closing_quantity = last_n_quantities
    elif filter_type == "İlk-Son":
        filter_opening_quantity = first_n_quantities
        filter_closing_quantity = target_contract_data["Kümülatif Toplam"].max() - last_n_quantities
    elif filter_type == "Son-Son":
        filter_opening_quantity = target_contract_data["Kümülatif Toplam"].max() - last_n_quantities
        filter_closing_quantity = target_contract_data["Kümülatif Toplam"].max() - first_n_quantities

    target_contract_data = target_contract_data[(target_contract_data["Kümülatif Toplam"] >= filter_opening_quantity) & (target_contract_data["Kümülatif Toplam"] <= filter_closing_quantity)]
    
    return target_contract_data[(target_contract_data["Kümülatif Toplam"] >= filter_opening_quantity) & (target_contract_data["Kümülatif Toplam"] <= filter_closing_quantity)]



col1, col2 = st.columns(2)
with col1:
    st.session_state.end_date = st.date_input("Tarih", value=st.session_state.end_date)
    if st.button("Tarihi Kaydet"):
        st.session_state.start_date = st.session_state.end_date - timedelta(days=1)
        start_date_str = st.session_state.start_date.strftime("%Y-%m-%dT00:00:00+03:00")
        end_date_str = st.session_state.end_date.strftime("%Y-%m-%dT00:00:00+03:00")
        st.session_state.gip_history = get_history(start_date_str, end_date_str)
        list_of_contracts = st.session_state.gip_history["Kontrat"].unique()
        st.session_state.target_day_contracts = st.session_state.gip_history[st.session_state.gip_history["Kontrat"].str.contains(day_contract_filter)]["Kontrat"].unique()
        st.session_state.target_day_contracts = sorted(st.session_state.target_day_contracts)
        
with col2:
    # select box for selecting the contract
    st.session_state.selected_contract  = st.selectbox("Kontrat", st.session_state.target_day_contracts)
    try:
        st.session_state.target_contract_data = st.session_state.gip_history[st.session_state.gip_history["Kontrat"] == st.session_state.selected_contract]
        st.session_state.target_contract_data["İşlem Zamanı"] = pd.to_datetime(st.session_state.target_contract_data["İşlem Zamanı"])
        st.session_state.target_contract_data = st.session_state.target_contract_data.reset_index(drop=True)
        st.session_state.filtered_data = st.session_state.target_contract_data
    except:
        pass

st.divider()

with st.popover("Filtrele",use_container_width=True):
    filtrecol1, filtrecol2 = st.columns(2)
    with filtrecol1:
        with st.form("Zaman Filtresi"):
            st.write("Zaman Filtresi")
            st.session_state.zaman_filtre_tipi = st.radio("Filtreleme Türü",["İlk-İlk","İlk-Son","Son-Son"],horizontal=True)
            n_mins_start = st.number_input("Zaman Başlangıç",step=1)
            n_mins_end = st.number_input("Zaman Bitiş",step=1)
            if st.form_submit_button("Uygula"):
                st.session_state.filtered_data = time_filter(n_mins_start,n_mins_end,st.session_state.target_contract_data,st.session_state.zaman_filtre_tipi)
    with filtrecol2:
        with st.form("Hacim Filtresi"):
            st.write("Hacim Filtresi")
            st.session_state.hacim_filtre_tipi = st.radio("Filtreleme Türü",["İlk-İlk","İlk-Son","Son-Son"],horizontal=True)
            n_quantities_start = st.number_input("Hacim Başlangıç",step=1)
            n_quantities_end = st.number_input("Hacim Bitiş",step=1)
            if st.form_submit_button("Uygula"):
                st.session_state.filtered_data = quantity_filter(n_quantities_start,n_quantities_end,st.session_state.target_contract_data,st.session_state.hacim_filtre_tipi)
try:
    with st.expander("İşlem Akışı",):
        st.dataframe(st.session_state.filtered_data,use_container_width=True,hide_index=True)

    infocol1, infocol2, infocol3, infocol4,infocol5 = st.columns(5)

    with infocol1:
        st.metric(label="Toplam İşlem Sayısı",
                  value = st.session_state.filtered_data.shape[0],
                  delta = f"{(round((st.session_state.filtered_data.shape[0] / st.session_state.target_contract_data.shape[0]),2)-1)*100} %",
                  )
        
    with infocol2:  
        st.metric(label="Toplam Hacim",
                  value = st.session_state.filtered_data["Hacim"].sum(),
                  delta = f"{(round((st.session_state.filtered_data['Hacim'].sum() / st.session_state.target_contract_data['Hacim'].sum()),2)-1)*100} %",
                  )
        
    with infocol3:
        st.metric(label="Ortalama Fiyat",
                  value = round((st.session_state.filtered_data["İşlem Fiyatı"].mean()),2),
                  delta = round((st.session_state.filtered_data["İşlem Fiyatı"].mean() - st.session_state.target_contract_data["İşlem Fiyatı"].mean()),2),
                  )
        
    with infocol4:
        st.metric(label="Maksimum Fiyat",
                  value = st.session_state.filtered_data["İşlem Fiyatı"].max(),
                  delta = round((st.session_state.filtered_data["İşlem Fiyatı"].max() - st.session_state.target_contract_data["İşlem Fiyatı"].max()),2),
                  )
        
    with infocol5:
        st.metric(label="Minimum Fiyat",
                  value = st.session_state.filtered_data["İşlem Fiyatı"].min(),
                  delta = round((st.session_state.filtered_data["İşlem Fiyatı"].min() - st.session_state.target_contract_data["İşlem Fiyatı"].min()),2),
                  )
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=st.session_state.filtered_data["İşlem Zamanı"], y=st.session_state.filtered_data["İşlem Fiyatı"], mode='lines', name='Fiyat',yaxis='y1',line_shape = "spline"))
    fig.add_trace(go.Bar(x=st.session_state.filtered_data["İşlem Zamanı"], y=st.session_state.filtered_data["Hacim"], name='Hacim',yaxis='y2',marker_color='rgba(255,0,0,0.3)',width=25000))

    fig.update_layout(
        title="İşlem Fiyatı ve Hacim",
        xaxis_title="Zaman",
        yaxis_title="Fiyat",
        yaxis2=dict(
            title="Hacim",
            overlaying='y',
            side='right'
        ),
        legend=dict(
            orientation="h",  # Yatay (horizontal) legend
            x=0.5,  # Legendi grafiğin ortasına hizala
            y=-0.3,  # X ekseni başlığından biraz daha aşağıda
            xanchor="center",  # X eksenindeki hizalamayı ortala
        ),
        hovermode="x unified",
    )

    st.plotly_chart(fig,use_container_width=True)
except:
    st.write("Veri Yok")