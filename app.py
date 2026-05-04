import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import urllib.parse

# ==================== LOGIN ====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

USUARIOS = {
    "admin": "1234",
    "vendedor": "loja2025"
}

if not st.session_state.logged_in:
    st.title("🔐 Login - Loja de Informática")
    st.markdown("### Digite seu usuário e senha")
    col1, col2 = st.columns(2)
    with col1: usuario = st.text_input("Usuário")
    with col2: senha = st.text_input("Senha", type="password")
    
    if st.button("🚪 Entrar", type="primary"):
        if usuario in USUARIOS and USUARIOS[usuario] == senha:
            st.session_state.logged_in = True
            st.session_state.username = usuario
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorreto")
    st.caption("admin / 1234\nvendedor / loja2025")
    st.stop()

# ==================== CONFIGURAÇÃO ====================
st.set_page_config(page_title="Loja de Informática", layout="wide")
st.title("💻 Loja de Informática - Sistema de Gestão")
st.markdown(f"**Bem-vindo, {st.session_state.username}!**")

if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.rerun()

# ==================== BANCO DE DADOS ====================
conn = sqlite3.connect('loja.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS clientes 
             (id INTEGER PRIMARY KEY, nome TEXT, telefone TEXT, cpf TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS produtos 
             (id INTEGER PRIMARY KEY, nome TEXT, preco REAL, estoque INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS os 
             (id INTEGER PRIMARY KEY, data TEXT, cliente_id INTEGER, total REAL, status TEXT, tipo TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS os_itens 
             (id INTEGER PRIMARY KEY, os_id INTEGER, descricao TEXT, quantidade REAL, preco REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS despesas 
             (id INTEGER PRIMARY KEY, data TEXT, descricao TEXT, valor REAL)''')
conn.commit()

# ==================== MENU ====================
menu = st.sidebar.selectbox(
    "Escolha o que fazer:",
    ["👤 Cadastrar Cliente",
     "📦 Cadastrar Produto",
     "📋 Nova Ordem de Serviço",
     "📋 Listar Ordens de Serviço",
     "👥 Gerenciar Clientes",
     "📦 Gerenciar Produtos",
     "💰 Relatório de Gastos e Lucro",
     "📄 Imprimir OS / NF-e"]
)

# ==================== CADASTRAR CLIENTE ====================
if menu == "👤 Cadastrar Cliente":
    st.subheader("Cadastrar Novo Cliente")
    with st.form("form_cliente"):
        nome = st.text_input("Nome completo")
        telefone = st.text_input("Telefone (com DDD)")
        cpf = st.text_input("CPF")
        if st.form_submit_button("💾 Salvar Cliente"):
            if nome:
                c.execute("INSERT INTO clientes (nome, telefone, cpf) VALUES (?,?,?)", (nome, telefone, cpf))
                conn.commit()
                st.success("✅ Cliente cadastrado!")
                st.rerun()

# ==================== CADASTRAR PRODUTO ====================
elif menu == "📦 Cadastrar Produto":
    st.subheader("Cadastrar Novo Produto")
    with st.form("form_produto"):
        nome = st.text_input("Nome do produto (ex: Notebook Dell i5)")
        preco = st.number_input("Preço de venda R$", min_value=0.0, step=0.1)
        estoque = st.number_input("Quantidade em estoque", min_value=0, step=1)
        if st.form_submit_button("💾 Salvar Produto"):
            if nome:
                c.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (?,?,?)", (nome, preco, estoque))
                conn.commit()
                st.success("✅ Produto cadastrado!")
                st.rerun()

# ==================== NOVA ORDEM DE SERVIÇO ====================
elif menu == "📋 Nova Ordem de Serviço":
    st.subheader("Nova Ordem de Serviço")
    c.execute("SELECT id, nome FROM clientes")
    clientes = [f"{id} - {nome}" for id, nome in c.fetchall()]
    cliente_sel = st.selectbox("Cliente", clientes) if clientes else None
    
    tipo_os = st.selectbox("Tipo de Ordem", ["Conserto / Assistência", "Venda", "Orçamento"])
    
    if "itens_os" not in st.session_state:
        st.session_state.itens_os = []
    
    st.write("### Adicionar itens (produto ou serviço)")
    col1, col2, col3 = st.columns(3)
    with col1: desc = st.text_input("Descrição")
    with col2: qtd = st.number_input("Quantidade", min_value=0.1, step=0.1)
    with col3: preco = st.number_input("Preço unitário R$", min_value=0.0, step=0.1)
    
    if st.button("➕ Adicionar item"):
        if desc and qtd and preco:
            st.session_state.itens_os.append([desc, qtd, preco, qtd*preco])
            st.rerun()
    
    if st.session_state.itens_os:
        df_itens = pd.DataFrame(st.session_state.itens_os, columns=["Descrição", "Qtd", "Preço", "Subtotal"])
        st.dataframe(df_itens, use_container_width=True)
        st.success(f"**Total: R$ {df_itens['Subtotal'].sum():.2f}**")
    
    if st.button("💾 Salvar Ordem de Serviço", type="primary"):
        if cliente_sel and st.session_state.itens_os:
            cliente_id = cliente_sel.split(" - ")[0]
            total = sum(item[3] for item in st.session_state.itens_os)
            
            c.execute("INSERT INTO os (data, cliente_id, total, status, tipo) VALUES (?,?,?,?,?)",
                      (datetime.now().strftime("%d/%m/%Y"), cliente_id, total, "Aberta", tipo_os))
            os_id = c.lastrowid
            
            for item in st.session_state.itens_os:
                c.execute("INSERT INTO os_itens (os_id, descricao, quantidade, preco) VALUES (?,?,?,?)",
                          (os_id, item[0], item[1], item[2]))
            conn.commit()
            st.success(f"✅ OS #{os_id} salva!")
            st.session_state.itens_os = []
            st.rerun()

# ==================== LISTAR OS ====================
elif menu == "📋 Listar Ordens de Serviço":
    st.subheader("Ordens de Serviço")
    df = pd.read_sql_query("""
        SELECT os.id, os.data, os.tipo, clientes.nome as cliente, os.total, os.status 
        FROM os JOIN clientes ON os.cliente_id = clientes.id 
        ORDER BY os.id DESC
    """, conn)
    st.dataframe(df, use_container_width=True)

# ==================== GERENCIAR CLIENTES / PRODUTOS ====================
elif menu == "👥 Gerenciar Clientes":
    st.subheader("Gerenciar Clientes")
    df = pd.read_sql_query("SELECT * FROM clientes", conn)
    st.dataframe(df, use_container_width=True)

elif menu == "📦 Gerenciar Produtos":
    st.subheader("Gerenciar Produtos")
    df = pd.read_sql_query("SELECT * FROM produtos", conn)
    st.dataframe(df, use_container_width=True)

# ==================== RELATÓRIO ====================
elif menu == "💰 Relatório de Gastos e Lucro":
    st.subheader("Relatório Financeiro")
    total_os = pd.read_sql_query("SELECT SUM(total) as total FROM os", conn).iloc[0]['total'] or 0
    total_despesas = pd.read_sql_query("SELECT SUM(valor) as total FROM despesas", conn).iloc[0]['total'] or 0
    lucro = total_os - total_despesas
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Recebido", f"R$ {total_os:.2f}")
    col2.metric("Total Despesas", f"R$ {total_despesas:.2f}")
    col3.metric("💰 LUCRO", f"R$ {lucro:.2f}")

# ==================== IMPRIMIR OS / NF-e ====================
elif menu == "📄 Imprimir OS / NF-e":
    st.subheader("Imprimir Ordem de Serviço / NF-e")
    df_os = pd.read_sql_query("SELECT id FROM os ORDER BY id DESC", conn)
    if not df_os.empty:
        os_id = st.selectbox("Escolha a OS", df_os['id'])
        
        if st.button("🖨️ Gerar PDF para Impressão"):
            os_data = pd.read_sql_query(f"SELECT * FROM os WHERE id={os_id}", conn).iloc[0]
            itens = pd.read_sql_query(f"SELECT * FROM os_itens WHERE os_id={os_id}", conn)
            cliente = pd.read_sql_query(f"SELECT nome, telefone FROM clientes WHERE id={os_data['cliente_id']}", conn).iloc[0]
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 15, "ORDEM DE SERVIÇO / NF-e", align="C", ln=1)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"OS: {os_id}   |   Data: {os_data['data']}", ln=1)
            pdf.cell(0, 10, f"Tipo: {os_data['tipo']}", ln=1)
            pdf.cell(0, 10, f"Cliente: {cliente['nome']}", ln=1)
            pdf.cell(0, 10, f"Telefone: {cliente['telefone']}", ln=1)
            pdf.ln(10)
            
            pdf.set_font("Arial", "B", 12)
            pdf.cell(90, 10, "Descrição", 1)
            pdf.cell(25, 10, "Qtd", 1, align="C")
            pdf.cell(35, 10, "Preço", 1, align="C")
            pdf.cell(35, 10, "Subtotal", 1, align="C", ln=1)
            
            pdf.set_font("Arial", "", 11)
            for _, item in itens.iterrows():
                pdf.cell(90, 10, item['descricao'][:40], 1)
                pdf.cell(25, 10, str(item['quantidade']), 1, align="C")
                pdf.cell(35, 10, f"R$ {item['preco']:.2f}", 1, align="C")
                pdf.cell(35, 10, f"R$ {item['quantidade']*item['preco']:.2f}", 1, align="C", ln=1)
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 12, f"TOTAL: R$ {os_data['total']:.2f}", align="R", ln=1)
            
            pdf_bytes = pdf.output(dest="S")
            if isinstance(pdf_bytes, str):
                pdf_bytes = pdf_bytes.encode("latin1")
            
            st.download_button(
                label="⬇️ Baixar PDF para Imprimir",
                data=pdf_bytes,
                file_name=f"OS_{os_id}.pdf",
                mime="application/pdf"
            )
    else:
        st.warning("Nenhuma OS cadastrada ainda.")

st.sidebar.caption("Sistema de Gestão para Loja de Informática ❤️")
