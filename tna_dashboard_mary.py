"""
Dashboard Finanzas Argentina v3
Correr: python -m streamlit run tna_dashboard_v3.py
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import json, os
from datetime import datetime
import streamlit.components.v1 as components

# ─── SUPABASE CONFIG ──────────────────────────────────────────────────────────
SUPABASE_URL = "https://dcidmhgpnffridlywlpv.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_4AQimobjhf3-aRapF8a4PQ_9xArJvRY")
USER_ID      = "usuario_dashboard"

def sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

def sb_get(key):
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/dashboard_data?user_id=eq.{USER_ID}&data_key=eq.{key}&select=data_value",
            headers=sb_headers(), timeout=10
        )
        if r.status_code == 200 and r.json():
            return r.json()[0]["data_value"]
        return None
    except: return None

def sb_set(key, value):
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/dashboard_data",
            headers=sb_headers(), timeout=10,
            json={"user_id": USER_ID, "data_key": key, "data_value": value}
        )
    except: pass

st.set_page_config(page_title="Finanzas Argentina", page_icon="AR", layout="wide")

BILLETERAS = [
    {"nombre": "Naranja X",    "tna": 25.0},
    {"nombre": "Mercado Pago", "tna": 24.0},
    {"nombre": "Uala",         "tna": 23.0},
    {"nombre": "Personal Pay", "tna": 22.6},
    {"nombre": "Lemon",        "tna": 21.8},
    {"nombre": "Brubank",      "tna": 20.0},
]
BANCOS_PF = [
    {"nombre": "ICBC",            "tna": 28.0},
    {"nombre": "Macro",           "tna": 27.5},
    {"nombre": "Galicia",         "tna": 27.0},
    {"nombre": "Santander",       "tna": 26.0},
    {"nombre": "BBVA",            "tna": 26.0},
    {"nombre": "Banco Nacion",    "tna": 25.0},
    {"nombre": "Banco Provincia", "tna": 25.0},
    {"nombre": "Supervielle",     "tna": 19.5},
]
NOMBRES_DOLAR  = {"oficial":"Oficial","blue":"Blue","bolsa":"MEP","contadoconliqui":"CCL","tarjeta":"Tarjeta","cripto":"Cripto","mayorista":"Mayorista"}
GASTOS_FIJOS   = ["Alquiler","Expensas","Luz","Gas","Agua","Internet","ABL"]
GASTOS_FILE    = "gastos_mensuales_usuario.json"
FINANZAS_FILE  = "finanzas_personales_usuario.json"
INVERSIONES_FILE = "inversiones_usuario.json"
DEUDAS_FILE    = "deudas_usuario.json"
MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
SUELDO_1 = 0
SUELDO_2 = 0
CATEGORIAS_GASTO = ["Mercado / supermercado","Transporte","Gym / Salud","Entretenimiento","Servicios digitales","Ahorro","Otros"]

# ─── PERSISTENCIA SUPABASE ────────────────────────────────────────────────────
def cargar_json(f):
    key = f.replace(".json","")
    data = sb_get(key)
    return data if data else {}

def guardar_json(f, data):
    key = f.replace(".json","")
    sb_set(key, data)

cargar_gastos    = lambda: cargar_json(GASTOS_FILE)
guardar_gastos   = lambda d: guardar_json(GASTOS_FILE, d)
cargar_finanzas  = lambda: cargar_json(FINANZAS_FILE)
guardar_finanzas = lambda d: guardar_json(FINANZAS_FILE, d)

# ─── APIs ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_dolares():
    try:
        r = requests.get("https://dolarapi.com/v1/dolares", timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        return r.json() if r.status_code==200 else None
    except: return None

@st.cache_data(ttl=300)
def fetch_instrumento_ar(simbolo):
    """Intenta obtener cotizacion via API de Cohen/BYMA que es publica."""
    urls = [
        f"https://api.cohen.com.ar/v2/Prices?ticker={simbolo}",
        f"https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/bnown/securities?symbol={simbolo}",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    item   = data[0]
                    precio = float(item.get("last", item.get("price", item.get("c", 0))))
                    cambio = float(item.get("variationLastPrice", item.get("change", item.get("dp", 0))))
                    if precio > 0:
                        return {"precio": precio, "cambio": cambio, "moneda": "ARS"}
                elif isinstance(data, dict):
                    precio = float(data.get("last", data.get("price", data.get("c", 0))))
                    cambio = float(data.get("variationLastPrice", data.get("change", data.get("dp", 0))))
                    if precio > 0:
                        return {"precio": precio, "cambio": cambio, "moneda": "ARS"}
        except: continue
    return None

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Configuracion")
    capital_pesos = st.number_input("Capital en pesos ($)", value=1_000_000, step=100_000)
    capital_comp  = st.number_input("Pesos para comprar dolar ($)", value=100_000, step=10_000)
    dias          = st.selectbox("Plazo TNA", [30,60,90,180,365], index=0)
    st.divider()
    for i, b in enumerate(BILLETERAS):
        BILLETERAS[i]["tna"] = st.number_input(b["nombre"], value=float(b["tna"]), step=0.1, key=f"bill_{i}")
    st.divider()
    for i, b in enumerate(BANCOS_PF):
        BANCOS_PF[i]["tna"] = st.number_input(b["nombre"], value=float(b["tna"]), step=0.1, key=f"banco_{i}")
    st.caption(f"Actualizado: {datetime.now().strftime('%d/%m %H:%M')}")

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.title("Mis Finanzas Personales")
dolares_data = fetch_dolares()
if dolares_data:
    mostrar = [d for d in dolares_data if d.get("casa","").lower() in ["oficial","blue","bolsa","contadoconliqui","tarjeta"]]
    cols = st.columns(len(mostrar))
    for i, d in enumerate(mostrar):
        nombre = NOMBRES_DOLAR.get(d["casa"].lower(), d["casa"])
        cols[i].metric(nombre, f"${d.get('venta','N/A')}", f"Compra: ${d.get('compra','N/A')}")
else:
    st.warning("No se pudo cargar el dolar.")
st.divider()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "TNA Tasas", "Dolar", "Gastos mensuales",
    "Finanzas personales", "Deudas y cuotas",
    "Cartera de inversiones", "Mercados"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TNA
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    todas = sorted(BILLETERAS+BANCOS_PF, key=lambda x: x["tna"], reverse=True)
    mejor = todas[0]
    c1,c2,c3 = st.columns(3)
    c1.metric("Mejor tasa", f"{mejor['tna']:.1f}%", mejor["nombre"])
    c2.metric(f"Ganancia {dias}d", f"${capital_pesos*mejor['tna']/100/365*dias:,.0f}", mejor["nombre"])
    c3.metric("Ganancia anual", f"${capital_pesos*mejor['tna']/100:,.0f}")
    st.divider()
    cb, cba = st.columns(2)
    with cb:
        st.subheader("Billeteras")
        rows = []
        for i,b in enumerate(sorted(BILLETERAS,key=lambda x:x["tna"],reverse=True)):
            g = capital_pesos*b["tna"]/100/365*dias
            rows.append({"#":i+1,"Billetera":b["nombre"],"TNA":f"{b['tna']:.1f}%",f"Ganancia {dias}d":f"${g:,.0f}","Total":f"${capital_pesos+g:,.0f}"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with cba:
        st.subheader("Bancos PF")
        rows = []
        for i,b in enumerate(sorted(BANCOS_PF,key=lambda x:x["tna"],reverse=True)):
            g = capital_pesos*b["tna"]/100/365*dias
            rows.append({"#":i+1,"Banco":b["nombre"],"TNA":f"{b['tna']:.1f}%",f"Ganancia {dias}d":f"${g:,.0f}","Total":f"${capital_pesos+g:,.0f}"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.divider()
    nombres = [b["nombre"] for b in todas]; tnas = [b["tna"] for b in todas]
    colores = ["#1D9E75" if i==0 else "#378ADD" if t>=24 else "#BA7517" if t>=21 else "#E24B4A" for i,t in enumerate(tnas)]
    fig = go.Figure(go.Bar(x=nombres,y=tnas,marker_color=colores,text=[f"{t:.1f}%" for t in tnas],textposition="outside"))
    fig.update_layout(height=320,template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=10,b=0),yaxis_title="TNA %",showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DOLAR UNIFICADO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.caption("Fuente: dolarapi.com | Actualiza cada 5 minutos")
    if dolares_data:
        rows = []
        for d in sorted(dolares_data, key=lambda x: float(x.get("venta") or 0)):
            if d.get("venta"):
                venta = float(d["venta"]); compra = float(d.get("compra") or 0)
                usd = capital_comp/venta if venta>0 else 0
                nombre = NOMBRES_DOLAR.get(d["casa"].lower(), d["casa"].capitalize())
                rows.append({"Tipo":nombre,"Compra":f"${compra:,.2f}","Venta":f"${venta:,.2f}","Spread":f"${venta-compra:,.2f}",f"USD con ${capital_comp:,}":f"USD {usd:.2f}","Actualizado":d.get("fechaActualizacion","")[:10]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("Dolar en billeteras")
        oficial = next((d for d in dolares_data if d.get("casa","").lower()=="oficial"), None)
        mep     = next((d for d in dolares_data if d.get("casa","").lower()=="bolsa"), None)
        cripto  = next((d for d in dolares_data if d.get("casa","").lower()=="cripto"), None)
        bill_dolar = []
        if oficial: bill_dolar.append({"Billetera":"Brubank","Tipo":"Oficial","compra":float(oficial.get("compra",0)),"venta":float(oficial.get("venta",0)),"Limite":"USD 200/mes"})
        if mep:     bill_dolar.append({"Billetera":"Mercado Pago","Tipo":"MEP","compra":float(mep.get("compra",0)),"venta":float(mep.get("venta",0)),"Limite":"USD 200/mes"})
        if cripto:  bill_dolar.append({"Billetera":"Lemon","Tipo":"USDT","compra":float(cripto.get("compra",0)),"venta":float(cripto.get("venta",0)),"Limite":"Sin limite"})
        if bill_dolar:
            bill_ord = sorted(bill_dolar, key=lambda x: x["venta"])
            venta_min = bill_ord[0]["venta"]
            rows_b = []
            for i,b in enumerate(bill_ord):
                usd=capital_comp/b["venta"] if b["venta"]>0 else 0; diff=b["venta"]-venta_min
                rows_b.append({"#":i+1,"Billetera":b["Billetera"],"Tipo":b["Tipo"],"Compra":f"${b['compra']:,.2f}","Venta":f"${b['venta']:,.2f}","Limite":b["Limite"],"vs mas barato":"OK mas barato" if diff==0 else f"+${diff:,.2f}",f"USD con ${capital_comp:,}":f"USD {usd:.2f}"})
            st.dataframe(pd.DataFrame(rows_b), use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("Simulador")
        principales = [d for d in dolares_data if d.get("casa","").lower() in ["oficial","blue","bolsa","tarjeta"] and d.get("venta")]
        cols = st.columns(len(principales))
        for i,d in enumerate(principales):
            with cols[i]:
                venta=float(d["venta"]); usd=capital_comp/venta; nombre=NOMBRES_DOLAR.get(d["casa"].lower(),d["casa"])
                st.metric(nombre,f"USD {usd:.2f}",f"@ ${venta:,.2f}")
    else:
        st.error("No se pudo conectar a dolarapi.com")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GASTOS MENSUALES
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    gastos_data   = cargar_gastos()
    finanzas_data = cargar_finanzas()
    col_form, col_hist = st.columns([1,1])
    with col_form:
        st.subheader("Cargar gastos del mes")
        anio_sel = st.selectbox("Ano", [2024,2025,2026], index=2)
        mes_sel  = st.selectbox("Mes", MESES, index=datetime.now().month-1)
        clave    = f"{anio_sel}-{mes_sel}"
        ge       = gastos_data.get(clave, {})
        st.markdown("**Gastos fijos**")
        gi = {}
        cols_g = st.columns(2)
        for i,g in enumerate(GASTOS_FIJOS):
            with cols_g[i%2]:
                gi[g] = st.number_input(g, value=float(ge.get(g,0.0)), step=100.0, key=f"gf_{g}_{clave}", min_value=0.0)
        st.markdown("**Gastos extras**")
        extras_ex = ge.get("extras",[])
        num_extras = st.number_input("Items extra", min_value=0, max_value=10, value=len(extras_ex), step=1)
        extras = []
        for i in range(int(num_extras)):
            cn, cv = st.columns([2,1])
            with cn: nn = st.text_input(f"Descripcion #{i+1}", value=extras_ex[i]["nombre"] if i<len(extras_ex) else "", key=f"en_{i}_{clave}")
            with cv: vv = st.number_input(f"Monto #{i+1}", value=float(extras_ex[i]["valor"]) if i<len(extras_ex) else 0.0, step=100.0, key=f"ev_{i}_{clave}", min_value=0.0)
            if nn: extras.append({"nombre":nn,"valor":vv})
        st.markdown("**Ajustes**")
        ca, cb2 = st.columns(2)
        with ca: adelanto_mary = st.number_input("Adelanto de Mary", value=float(ge.get("adelanto_mary",0)), step=100.0, min_value=0.0)
        with cb2: deuda_ant = st.number_input("Deuda anterior de Mary", value=float(ge.get("deuda_ant",0)), step=100.0)
        if st.button("Guardar mes", use_container_width=True):
            gastos_data[clave] = {**gi,"extras":extras,"adelanto_mary":adelanto_mary,"deuda_ant":deuda_ant}
            guardar_gastos(gastos_data)
            st.success(f"Gastos de {mes_sel} {anio_sel} guardados!")
            st.rerun()

    with col_hist:
        st.subheader(f"Resumen {mes_sel} {anio_sel}")
        fp_mes   = finanzas_data.get(clave, {})
        sal_mes  = fp_mes.get("sueldo1",SUELDO_1) + fp_mes.get("sueldo2",SUELDO_2) + sum(e["valor"] for e in fp_mes.get("extras_ing",[]))
        if clave in gastos_data:
            g = gastos_data[clave]
            total_fijos  = sum(g.get(gf,0) for gf in GASTOS_FIJOS)
            total_extras = sum(e["valor"] for e in g.get("extras",[]))
            total = total_fijos+total_extras; mitad = total/2
            adelanto = g.get("adelanto_mary",0); deuda_ant_v = g.get("deuda_ant",0)
            mary_final = mitad - adelanto + deuda_ant_v
            mary_rec   = mary_final if g.get("mary_pago",False) else 0
            saldo_disp = sal_mes - mitad + mary_rec
            c1,c2,c3 = st.columns(3)
            c1.metric("Tu salario", f"${sal_mes:,.0f}")
            c2.metric("Tu parte gastos", f"${mitad:,.2f}")
            c3.metric("Saldo disponible", f"${saldo_disp:,.0f}", "incluye Mary" if mary_rec>0 else "sin Mary aun")
            st.divider()
            rows_det = []
            for gf in GASTOS_FIJOS:
                v=g.get(gf,0)
                if v>0: rows_det.append({"Concepto":gf,"Monto":f"${v:,.2f}","Tipo":"Fijo"})
            for e in g.get("extras",[]): rows_det.append({"Concepto":e["nombre"],"Monto":f"${e['valor']:,.2f}","Tipo":"Extra"})
            if rows_det: st.dataframe(pd.DataFrame(rows_det), use_container_width=True, hide_index=True)
            st.divider()
            st.markdown("**Liquidacion con Mary**")
            cl1,cl2,cl3 = st.columns(3)
            cl1.metric("Le corresponde", f"${mitad:,.2f}")
            cl2.metric("Adelanto", f"${adelanto:,.2f}")
            cl3.metric("Deuda ant.", f"${deuda_ant_v:,.2f}")
            pagado = ge.get("mary_pago",False)
            if mary_final > 0:
                if pagado:
                    st.success(f"Mary pago ${mary_final:,.2f} — saldado")
                    if st.button("Marcar pendiente", key=f"unpay_{clave}"):
                        gastos_data[clave]["mary_pago"]=False; guardar_gastos(gastos_data); st.rerun()
                else:
                    st.warning(f"Mary debe pagarte: ${mary_final:,.2f}")
                    if st.button("Mary pago", key=f"pay_{clave}", type="primary", use_container_width=True):
                        gastos_data[clave]["mary_pago"]=True; guardar_gastos(gastos_data); st.rerun()
            elif mary_final < 0: st.warning(f"Vos le debes a Mary: ${abs(mary_final):,.2f}")
            else: st.info("Estan al dia")
        else:
            st.metric("Tu salario", f"${sal_mes:,.0f}")
            st.info(f"No hay gastos cargados para {mes_sel} {anio_sel}.")
    st.divider()
    st.subheader("Historial")
    if gastos_data:
        hist_rows=[]
        for k,g in sorted(gastos_data.items()):
            total=sum(g.get(gf,0) for gf in GASTOS_FIJOS)+sum(e["valor"] for e in g.get("extras",[])); mitad=total/2
            mary_final=mitad-g.get("adelanto_mary",0)+g.get("deuda_ant",0)
            fp_k=finanzas_data.get(k,{}); sal_k=fp_k.get("sueldo1",SUELDO_1)+fp_k.get("sueldo2",SUELDO_2)
            mary_rec=mary_final if g.get("mary_pago",False) else 0; saldo_k=sal_k-mitad+mary_rec
            hist_rows.append({"Mes":k,"Salario":f"${sal_k:,.0f}","Total gastos":f"${total:,.0f}","Tu parte":f"${mitad:,.0f}","Saldo":f"${saldo_k:,.0f}","Mary paga":f"${mary_final:,.0f}","Estado":"Al dia" if mary_final==0 else ("Pagado" if g.get("mary_pago") else ("Mary debe" if mary_final>0 else "Vos debes"))})
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — FINANZAS PERSONALES
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    finanzas_data = cargar_finanzas(); gastos_data = cargar_gastos()
    ca, cb2 = st.columns(2)
    with ca: anio_fp = st.selectbox("Ano", [2024,2025,2026], index=2, key="fp_anio")
    with cb2: mes_fp = st.selectbox("Mes", MESES, index=datetime.now().month-1, key="fp_mes")
    clave_fp = f"{anio_fp}-{mes_fp}"; fpe = finanzas_data.get(clave_fp, {})
    st.divider()
    ci, cg = st.columns([1,1])
    with ci:
        st.subheader("Ingresos")
        sueldo1 = st.number_input("Empresa 1", value=float(fpe.get("sueldo1",SUELDO_1)), step=1000.0, key="fp_s1")
        sueldo2 = st.number_input("Empresa 2", value=float(fpe.get("sueldo2",SUELDO_2)), step=1000.0, key="fp_s2")
        extras_ing = fpe.get("extras_ing",[])
        num_ei = st.number_input("Ingresos extra", min_value=0, max_value=10, value=len(extras_ing), step=1, key="fp_nei")
        ingresos_extra = []
        for i in range(int(num_ei)):
            ce1,ce2 = st.columns([2,1])
            with ce1: n = st.text_input(f"Fuente #{i+1}", value=extras_ing[i]["nombre"] if i<len(extras_ing) else "", key=f"fp_in_{i}")
            with ce2: v = st.number_input(f"Monto #{i+1}", value=float(extras_ing[i]["valor"]) if i<len(extras_ing) else 0.0, step=100.0, key=f"fp_iv_{i}", min_value=0.0)
            if n: ingresos_extra.append({"nombre":n,"valor":v})
        gma = cargar_gastos().get(clave_fp,{})
        pago_mary = 0.0
        if gma.get("mary_pago",False):
            tc = sum(gma.get(gf,0) for gf in GASTOS_FIJOS)+sum(e["valor"] for e in gma.get("extras",[]))
            pago_mary = tc/2 - gma.get("adelanto_mary",0) + gma.get("deuda_ant",0)
        salario_base   = sueldo1+sueldo2+sum(e["valor"] for e in ingresos_extra)
        total_ingresos = salario_base+pago_mary
        st.divider()
        cm1,cm2,cm3 = st.columns(3)
        cm1.metric("Salario base", f"${salario_base:,.0f}")
        cm2.metric("Pago de Mary", f"${pago_mary:,.0f}", "acreditado" if pago_mary>0 else "pendiente")
        cm3.metric("Total ingresos", f"${total_ingresos:,.0f}")

        # Regla 50/20/20/10
        st.divider()
        st.markdown("**Plan de distribucion ideal (regla 50/20/20/10)**")
        r50 = salario_base*0.50; r20i = salario_base*0.20; r20e = salario_base*0.20; r10 = salario_base*0.10
        dof = next((d for d in (dolares_data or []) if d.get("casa","").lower()=="oficial"),None)
        dolar_of = float(dof.get("venta",1415)) if dof else 1415.0
        pr1,pr2,pr3,pr4 = st.columns(4)
        pr1.metric("50% Gastos fijos", f"${r50:,.0f}")
        pr2.metric("20% Invertir", f"${r20i:,.0f}", f"USD {r20i/dolar_of:,.0f}")
        pr3.metric("20% Emergencia", f"${r20e:,.0f}", f"USD {r20e/dolar_of:,.0f}")
        pr4.metric("10% Disfrutar", f"${r10:,.0f}")

    with cg:
        st.subheader("Gastos personales")
        dof2 = next((d for d in (dolares_data or []) if d.get("casa","").lower()=="oficial"),None)
        dolar_oficial = float(dof2.get("venta",1415)) if dof2 else 1415.0
        gastos_fp = {}
        for cat in CATEGORIAS_GASTO:
            val_prev = fpe.get(cat,0.0)
            if cat=="Envio mama (USDT)":
                cu,cp = st.columns([1,1])
                with cu: usdt_mama = st.number_input("Envio mama (USDT)", value=float(fpe.get("mama_usdt",100)), step=10.0, key="fp_mama_usdt", min_value=0.0)
                with cp: st.metric("En pesos", f"${usdt_mama*dolar_oficial:,.0f}", f"@ ${dolar_oficial:,.0f}/USD")
                gastos_fp[cat]=usdt_mama*dolar_oficial; gastos_fp["mama_usdt"]=usdt_mama
            elif cat=="Ahorro dolares":
                cu2,cp2 = st.columns([1,1])
                with cu2: usdt_ah = st.number_input("Ahorro (USD)", value=float(fpe.get("ahorro_usdt",0)), step=10.0, key="fp_ahorro_usdt", min_value=0.0)
                with cp2: st.metric("En pesos", f"${usdt_ah*dolar_oficial:,.0f}", f"@ ${dolar_oficial:,.0f}/USD")
                gastos_fp[cat]=usdt_ah*dolar_oficial; gastos_fp["ahorro_usdt"]=usdt_ah
            elif cat == "Servicios digitales":
                st.markdown("**Servicios digitales**")
                servicios_lista = fpe.get("servicios_lista", [])
                num_serv = st.number_input("Cantidad de servicios", min_value=0, max_value=15,
                                           value=len(servicios_lista), step=1, key="fp_num_serv")
                total_serv = 0.0
                servicios_nueva = []
                for si in range(int(num_serv)):
                    cs1, cs2, cs3 = st.columns([2, 1, 1])
                    with cs1:
                        sn = st.text_input(f"Servicio #{si+1}",
                                          value=servicios_lista[si]["nombre"] if si<len(servicios_lista) else "",
                                          key=f"fp_sn_{si}")
                    with cs2:
                        sm = st.number_input(f"Monto #{si+1}",
                                            value=float(servicios_lista[si]["monto"]) if si<len(servicios_lista) else 0.0,
                                            step=0.1, key=f"fp_sm_{si}", min_value=0.0)
                    with cs3:
                        smon = st.selectbox(f"Moneda #{si+1}",
                                           ["ARS","USD"],
                                           index=0 if (si<len(servicios_lista) and servicios_lista[si]["moneda"]=="ARS") else 1,
                                           key=f"fp_smon_{si}")
                    if sn:
                        monto_ars = sm * dolar_oficial if smon == "USD" else sm
                        total_serv += monto_ars
                        servicios_nueva.append({"nombre": sn, "monto": sm, "moneda": smon})
                if servicios_nueva:
                    st.caption(f"Total servicios: ${total_serv:,.0f} ARS")
                gastos_fp[cat] = total_serv
                gastos_fp["servicios_lista"] = servicios_nueva
            elif cat == "Otros":
                st.markdown("**Otros gastos**")
                otros_lista = fpe.get("otros_lista", [])
                num_otros = st.number_input("Cantidad de gastos varios", min_value=0, max_value=10,
                                             value=len(otros_lista), step=1, key="fp_num_otros")
                total_otros = 0.0
                otros_nueva = []
                for oi in range(int(num_otros)):
                    co1, co2 = st.columns([2,1])
                    with co1:
                        on = st.text_input(f"Descripcion #{oi+1}",
                                          value=otros_lista[oi]["nombre"] if oi<len(otros_lista) else "",
                                          key=f"fp_on_{oi}")
                    with co2:
                        ov = st.number_input(f"Monto #{oi+1}",
                                            value=float(otros_lista[oi]["valor"]) if oi<len(otros_lista) else 0.0,
                                            step=100.0, key=f"fp_ov_{oi}", min_value=0.0)
                    if on:
                        otros_nueva.append({"nombre":on,"valor":ov})
                        total_otros += ov
                gastos_fp[cat] = total_otros
                gastos_fp["otros_lista"] = otros_nueva
            else:
                gastos_fp[cat] = st.number_input(cat, value=float(val_prev), step=100.0, key=f"fp_g_{cat}", min_value=0.0)
        gc = gastos_data.get(clave_fp,{})
        mitad_c = 0.0
        if gc:
            tc=sum(gc.get(gf,0) for gf in GASTOS_FIJOS)+sum(e["valor"] for e in gc.get("extras",[])); mitad_c=tc/2
        total_gp   = sum(v for k,v in gastos_fp.items() if k in CATEGORIAS_GASTO)
        total_gr   = total_gp+mitad_c

    st.divider(); st.subheader(f"Resumen {mes_fp} {anio_fp}")
    saldo = total_ingresos-total_gr; pct_ah = (saldo/total_ingresos*100) if total_ingresos>0 else 0
    pct_usado = min((total_gr/total_ingresos*100),100) if total_ingresos>0 else 0
    cr1,cr2,cr3,cr4,cr5 = st.columns(5)
    cr1.metric("Salario base", f"${salario_base:,.0f}")
    cr2.metric("Pago Mary", f"${pago_mary:,.0f}")
    cr3.metric("Gastos pers.", f"${total_gp:,.0f}")
    cr4.metric("Gastos fijos", f"${mitad_c:,.0f}")
    cr5.metric("Saldo del mes", f"${saldo:,.0f}", f"{pct_ah:+.1f}%")
    st.progress(pct_usado/100)
    if pct_usado<70: st.success(f"Vas bien — te queda ${saldo:,.0f}")
    elif pct_usado<90: st.warning(f"Gastaste el {pct_usado:.1f}% — margen ajustado")
    else: st.error(f"Gastaste el {pct_usado:.1f}% — revisa los gastos")

    st.divider()
    if st.button("Guardar finanzas del mes", use_container_width=True, type="primary", key="fp_save"):
        finanzas_data[clave_fp] = {"sueldo1":sueldo1,"sueldo2":sueldo2,"extras_ing":ingresos_extra,**gastos_fp,"otros_lista":gastos_fp.get("otros_lista",[]),"servicios_lista":gastos_fp.get("servicios_lista",[])}
        guardar_finanzas(finanzas_data); st.success(f"Finanzas de {mes_fp} {anio_fp} guardadas!"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — DEUDAS Y CUOTAS
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    deudas_data = cargar_json(DEUDAS_FILE)
    DEUDAS_DEFAULT = [
        {"nombre":"Prestamo Supervielle","monto_total":783247.86,"cuotas_pagas":16,"cuotas_total":18,"tarjeta":"Supervielle","moneda":"ARS"},
        {"nombre":"Prestamo Mercado Libre","monto_total":28451.44,"cuotas_pagas":8,"cuotas_total":12,"tarjeta":"Mercado Libre","moneda":"ARS"},
        {"nombre":"XI Alto Palermo","monto_total":74899.98,"cuotas_pagas":4,"cuotas_total":6,"tarjeta":"Master","moneda":"ARS"},
        {"nombre":"Curso ingles","monto_total":1170000.0,"cuotas_pagas":1,"cuotas_total":9,"tarjeta":"Master","moneda":"ARS"},
        {"nombre":"Regalo Mary","monto_total":127290.0,"cuotas_pagas":0,"cuotas_total":1,"tarjeta":"Master","moneda":"ARS"},
        {"nombre":"Auriculares","monto_total":26771.55,"cuotas_pagas":2,"cuotas_total":3,"tarjeta":"Mercado Libre","moneda":"ARS"},
        {"nombre":"Perfumes","monto_total":35314.64,"cuotas_pagas":2,"cuotas_total":3,"tarjeta":"Mercado Libre","moneda":"ARS"},
        {"nombre":"Regalo Yurman","monto_total":23839.01,"cuotas_pagas":0,"cuotas_total":1,"tarjeta":"Mercado Libre","moneda":"ARS"},
        {"nombre":"Cartera Visa","monto_total":83000.0,"cuotas_pagas":0,"cuotas_total":1,"tarjeta":"Visa Supervielle","moneda":"ARS"},
    ]
    deudas = deudas_data.get("deudas", [])
    cuota     = lambda d: d["monto_total"]/d["cuotas_total"] if d["cuotas_total"]>0 else 0
    saldo_res = lambda d: cuota(d)*(d["cuotas_total"]-d["cuotas_pagas"])
    dof3 = next((d for d in (dolares_data or []) if d.get("casa","").lower()=="oficial"),None)
    dolar_v = float(dof3.get("venta",1415)) if dof3 else 1415.0
    activas = [d for d in deudas if d["cuotas_pagas"]<d["cuotas_total"]]
    total_ars = sum(saldo_res(d) for d in activas if d.get("moneda","ARS")=="ARS")
    total_usd = sum(saldo_res(d) for d in activas if d.get("moneda","ARS")=="USD")
    cuota_m   = sum(cuota(d) for d in activas if d.get("moneda","ARS")=="ARS")
    cd1,cd2,cd3,cd4 = st.columns(4)
    cd1.metric("Deuda total ARS", f"${total_ars:,.0f}")
    cd2.metric("Deuda total USD", f"USD {total_usd:,.2f}")
    cd3.metric("Cuota mensual ARS", f"${cuota_m:,.0f}")
    cd4.metric("Deudas activas", f"{len(activas)}")
    st.divider()
    rows_d=[]
    for d in deudas:
        restantes=d["cuotas_total"]-d["cuotas_pagas"]; c=cuota(d); s=saldo_res(d)
        moneda=d.get("moneda","ARS"); sim="USD " if moneda=="USD" else "$"
        rows_d.append({"Deuda":d["nombre"],"Tarjeta":d["tarjeta"],"Moneda":moneda,"Cuota":f"{sim}{c:,.2f}","Progreso":f"{d['cuotas_pagas']}/{d['cuotas_total']}","Saldo restante":f"{sim}{s:,.2f}","Estado":"Pagada" if restantes==0 else f"{restantes} cuota/s restante/s"})
    st.dataframe(pd.DataFrame(rows_d), use_container_width=True, hide_index=True)
    st.divider()
    st.subheader("Progreso")
    for d in deudas:
        restantes=d["cuotas_total"]-d["cuotas_pagas"]; prog=d["cuotas_pagas"]/d["cuotas_total"] if d["cuotas_total"]>0 else 1
        moneda=d.get("moneda","ARS"); sim="USD " if moneda=="USD" else "$"; c=cuota(d)
        cn,cp=st.columns([2,3])
        with cn: st.text(d["nombre"]); st.caption(f"{sim}{c:,.0f}/cuota — {restantes} restantes")
        with cp: st.progress(prog)
    st.divider()
    st.subheader("Marcar cuota pagada")
    mes_actual_str = datetime.now().strftime("%Y-%m")
    for i,d in enumerate(deudas):
        restantes=d["cuotas_total"]-d["cuotas_pagas"]
        if restantes>0:
            c=cuota(d); moneda=d.get("moneda","ARS"); sim="USD " if moneda=="USD" else "$"
            ultimo_pago = d.get("ultimo_pago_mes","")
            ya_pago_este_mes = (ultimo_pago == mes_actual_str)
            cdn,cdb=st.columns([3,1])
            with cdn:
                st.text(f"{d['nombre']} — {sim}{c:,.0f} — {restantes} cuotas restantes")
                if ya_pago_este_mes:
                    st.caption(f"Ya pagaste este mes ({mes_actual_str})")
            with cdb:
                if ya_pago_este_mes:
                    st.button("Ya pago", key=f"dp_{i}", disabled=True)
                else:
                    if st.button("Pague", key=f"dp_{i}"):
                        deudas[i]={**d,"cuotas_pagas":d["cuotas_pagas"]+1,"ultimo_pago_mes":mes_actual_str}
                        deudas_guardar=[x for x in deudas if x["cuotas_pagas"]<x["cuotas_total"]]
                        guardar_json(DEUDAS_FILE,{"deudas":deudas_guardar})
                        st.success(f"Cuota de '{d['nombre']}' marcada como pagada!")
                        st.rerun()
    deudas_nuevas = deudas[:]
    st.divider()
    st.subheader("Agregar nueva deuda")
    with st.expander("+ Nueva deuda"):
        cn1,cn2=st.columns(2)
        with cn1:
            nd_nom = st.text_input("Descripcion", key="nd_n")
            nd_monto = st.number_input("Monto total", min_value=0.0, step=100.0, key="nd_m")
            nd_cuotas = st.number_input("Total cuotas", min_value=1, max_value=60, value=1, step=1, key="nd_c")
        with cn2:
            nd_tarj = st.text_input("Tarjeta / Banco", key="nd_t")
            nd_mon  = st.selectbox("Moneda", ["ARS","USD"], key="nd_mo")
            nd_pagas = st.number_input("Cuotas ya pagas", min_value=0, value=0, step=1, key="nd_p")
        if nd_mon=="USD" and nd_monto>0:
            st.caption(f"Equivale a ${nd_monto*dolar_v:,.0f} ARS al tipo oficial")
        if st.button("Agregar deuda", type="primary", key="nd_add"):
            if nd_nom and nd_monto>0:
                deudas_nuevas.append({"nombre":nd_nom,"monto_total":nd_monto,"cuotas_total":int(nd_cuotas),"cuotas_pagas":int(nd_pagas),"tarjeta":nd_tarj,"moneda":nd_mon})
                guardar_json(DEUDAS_FILE,{"deudas":deudas_nuevas}); st.success(f"Deuda '{nd_nom}' agregada!"); st.rerun()
            else: st.error("Completa descripcion y monto")
    if st.button("Guardar estado deudas", use_container_width=True, key="d_save"):
        dg=[d for d in deudas_nuevas if d["cuotas_pagas"]<d["cuotas_total"]]
        elim=len(deudas_nuevas)-len(dg); guardar_json(DEUDAS_FILE,{"deudas":dg})
        st.success(f"Guardado!" + (f" Se eliminaron {elim} deuda/s pagadas." if elim>0 else "")); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — CARTERA DE INVERSIONES
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    inv_data = cargar_json(INVERSIONES_FILE)
    CARTERA_DEFAULT = []
    cartera = inv_data.get("cartera", [])
    total_usd_inv = sum(c["monto_usd"] for c in cartera)
    rend_anual    = sum(c["monto_usd"]*c["apy"]/100 for c in cartera)
    apy_prom      = rend_anual/total_usd_inv*100 if total_usd_inv>0 else 0
    ci1,ci2,ci3,ci4 = st.columns(4)
    ci1.metric("Total invertido", f"USD {total_usd_inv:,.0f}")
    ci2.metric("Rendimiento anual", f"USD {rend_anual:,.0f}")
    ci3.metric("APY promedio", f"{apy_prom:.2f}%")
    ci4.metric("Rendimiento mensual", f"USD {rend_anual/12:,.0f}")
    st.divider()
    ct, cg2 = st.columns([1,1])
    with ct:
        rows_i=[]
        for c in sorted(cartera,key=lambda x:x["monto_usd"],reverse=True):
            ra=c["monto_usd"]*c["apy"]/100
            rows_i.append({"Plataforma":c["plataforma"],"Activo":c["moneda"],"Tipo":c["tipo"],"USD":f"${c['monto_usd']:,.0f}","APY":f"{c['apy']:.1f}%","Rend/ano":f"USD {ra:,.0f}","Notas":c["notas"]})
        st.dataframe(pd.DataFrame(rows_i), use_container_width=True, hide_index=True)
    with cg2:
        pd2={}
        for c in cartera: pd2[c["plataforma"]]=pd2.get(c["plataforma"],0)+c["monto_usd"]
        fig2=go.Figure(go.Pie(labels=list(pd2.keys()),values=[round(v) for v in pd2.values()],hole=0.4,textinfo="label+percent",marker=dict(colors=["#1D9E75","#378ADD","#BA7517","#E24B4A","#CE93D8","#FFB74D","#64B5F6","#A5D6A7","#EF9A9A","#80CBC4","#FFCC80","#F48FB1"])))
        fig2.update_layout(height=350,template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=20,b=0),showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    st.divider()
    st.subheader("Actualizar montos")
    cartera_nueva=[]
    for i,c in enumerate(cartera):
        cp,cm,ca2=st.columns([2,1,1])
        with cp: st.text(f"{c['plataforma']} — {c['moneda']}")
        with cm: nm=st.number_input("USD",value=float(c["monto_usd"]),step=10.0,key=f"im_{i}",label_visibility="collapsed")
        with ca2: na=st.number_input("APY%",value=float(c["apy"]),step=0.1,key=f"ia_{i}",label_visibility="collapsed")
        cartera_nueva.append({**c,"monto_usd":nm,"apy":na})
    st.divider()
    st.subheader("Agregar nueva inversion")
    with st.expander("+ Nueva inversion"):
        ni1,ni2=st.columns(2)
        with ni1:
            ni_plat = st.text_input("Plataforma (ej: Bybit)", key="ni_p")
            ni_monto = st.number_input("Monto (USD)", min_value=0.0, step=1.0, key="ni_m")
            ni_apy = st.number_input("APY %", min_value=0.0, step=0.1, key="ni_a")
        with ni2:
            ni_mon  = st.text_input("Moneda (ej: USDT)", key="ni_mo")
            ni_tipo = st.selectbox("Tipo", ["Stablecoin","Cripto","USD","Acciones","FCI","CEDEAR","Pesos"], key="ni_t")
            ni_nota = st.text_input("Notas", key="ni_n")
        if st.button("Agregar inversion", type="primary", key="ni_add"):
            if ni_plat and ni_monto>0:
                cartera_nueva.append({"plataforma":ni_plat,"tipo":ni_tipo,"moneda":ni_mon,"monto_usd":ni_monto,"apy":ni_apy,"notas":ni_nota})
                guardar_json(INVERSIONES_FILE,{"cartera":cartera_nueva}); st.success(f"Inversion en {ni_plat} agregada!"); st.rerun()
            else: st.error("Completa plataforma y monto")
    if st.button("Guardar cartera", use_container_width=True, key="inv_save"):
        guardar_json(INVERSIONES_FILE,{"cartera":cartera_nueva}); st.success("Cartera guardada!"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — MERCADOS
# ══════════════════════════════════════════════════════════════════════════════
with tab7:
    INSTRUMENTOS_AR = [
        {"simbolo":"AL30","nombre":"AL30","tipo":"Bono"},
        {"simbolo":"AE38","nombre":"AE38","tipo":"Bono"},
        {"simbolo":"GD30","nombre":"GD30","tipo":"Bono"},
        {"simbolo":"AL35","nombre":"AL35","tipo":"Bono"},
        {"simbolo":"GGAL","nombre":"Galicia","tipo":"Accion"},
        {"simbolo":"YPFD","nombre":"YPF","tipo":"Accion"},
        {"simbolo":"BBAR","nombre":"BBVA AR","tipo":"Accion"},
        {"simbolo":"PAMP","nombre":"Pampa","tipo":"Accion"},
        {"simbolo":"BMA","nombre":"Macro","tipo":"Accion"},
        {"simbolo":"TXAR","nombre":"Ternium","tipo":"Accion"},
    ]
    st.subheader("Bonos y acciones argentinas")
    st.caption("Fuente: BYMA | Precios diferidos 20 min")
    cb1,cb2 = st.columns(2)
    bonos    = [i for i in INSTRUMENTOS_AR if i["tipo"]=="Bono"]
    acciones = [i for i in INSTRUMENTOS_AR if i["tipo"]=="Accion"]
    with cb1:
        st.markdown("**Bonos soberanos**")
        rows_b=[]
        for inst in bonos:
            data=fetch_instrumento_ar(inst["simbolo"])
            if data: rows_b.append({"Bono":inst["nombre"],"Precio":f"${data['precio']:,.2f}","Cambio":f"{data['cambio']:+.2f}%","Moneda":data["moneda"]})
            else: rows_b.append({"Bono":inst["nombre"],"Precio":"N/D","Cambio":"-","Moneda":"ARS"})
        st.dataframe(pd.DataFrame(rows_b), use_container_width=True, hide_index=True)
    with cb2:
        st.markdown("**Acciones lideres MERVAL**")
        rows_a=[]
        for inst in acciones:
            data=fetch_instrumento_ar(inst["simbolo"])
            if data: rows_a.append({"Accion":inst["nombre"],"Precio":f"${data['precio']:,.2f}","Cambio":f"{data['cambio']:+.2f}%","Moneda":data["moneda"]})
            else: rows_a.append({"Accion":inst["nombre"],"Precio":"N/D","Cambio":"-","Moneda":"ARS"})
        st.dataframe(pd.DataFrame(rows_a), use_container_width=True, hide_index=True)
    st.divider()
    st.subheader("Mapa de calor S&P 500")
    components.html("""
    <div style="height:520px;width:100%;">
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
    {"exchanges":[],"dataSource":"SPX500","grouping":"sector","blockSize":"market_cap_basic","blockColor":"change","locale":"es","colorTheme":"dark","hasTopBar":false,"isZoomEnabled":true,"hasSymbolTooltip":true,"isMonoSize":false,"width":"100%","height":"500"}
    </script></div>""", height=530)
    st.divider()
    cm1, cm2 = st.columns(2)
    with cm1:
        st.markdown("**Merval**")
        components.html("""
        <div style="height:320px;width:100%;">
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
        {"symbol":"BCBA:IMV","width":"100%","height":"300","locale":"es","dateRange":"12M","colorTheme":"dark","isTransparent":false,"autosize":true}
        </script></div>""", height=330)
    with cm2:
        st.markdown("**BTC/USDT**")
        components.html("""
        <div style="height:320px;width:100%;">
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
        {"symbol":"BINANCE:BTCUSDT","width":"100%","height":"300","locale":"es","dateRange":"1M","colorTheme":"dark","isTransparent":false,"autosize":true}
        </script></div>""", height=330)
    st.divider()
    st.markdown("**Noticias del mercado cripto**")
    components.html("""
    <div style="height:420px;width:100%;">
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js" async>
    {"feedMode":"market","market":"crypto","isTransparent":false,"displayMode":"regular","width":"100%","height":"400","colorTheme":"dark","locale":"es"}
    </script></div>""", height=430)
