import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# =============================
# CONFIGURAÇÃO GOOGLE
# =============================

PLANILHA_NOME = "Controle_Meios_Organicos_Deposito"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = st.secrets["gcp_service_account"]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict, scope
)

client = gspread.authorize(creds)
sheet = client.open(PLANILHA_NOME)

aba_equip = sheet.worksheet("Equipamentos")
aba_manut = sheet.worksheet("Manutencoes")
aba_avarias = sheet.worksheet("Avarias")

# =============================
# FUNÇÕES SEGURAS
# =============================

def carregar_equip():
    dados = aba_equip.get_all_records()
    if not dados:
        return pd.DataFrame()
    df = pd.DataFrame(dados)
    df.columns = df.columns.map(str)
    df.columns = df.columns.str.strip()
    return df

def carregar_manut():
    dados = aba_manut.get_all_records()
    if not dados:
        return pd.DataFrame()
    df = pd.DataFrame(dados)
    df.columns = df.columns.map(str)
    df.columns = df.columns.str.strip()
    return df

def carregar_avarias():
    dados = aba_avarias.get_all_records()
    if not dados:
        return pd.DataFrame()
    df = pd.DataFrame(dados)
    df.columns = df.columns.map(str)
    df.columns = df.columns.str.strip()
    return df

def numero_existe(numero):
    df = carregar_equip()
    if df.empty:
        return False
    return numero in df["Numero_Meio"].astype(str).values

def adicionar_equipamento(dados):
    aba_equip.append_row(dados)

def atualizar_status(numero, novo_status):

    try:
        df = carregar_equip()

        if df.empty:
            st.error("Planilha vazia.")
            return

        numero = str(numero).strip()

        # Garante que Numero_Meio é string
        df["Numero_Meio"] = df["Numero_Meio"].astype(str).str.strip()

        # Procura o equipamento
        linha = df[df["Numero_Meio"] == numero]

        if linha.empty:
            st.error(f"Equipamento {numero} não encontrado.")
            return

        # Descobre posição da linha real na planilha
        indice_df = linha.index[0]
        linha_planilha = indice_df + 2  # +2 por causa do cabeçalho

        # Descobre posição da coluna Status automaticamente
        cabecalho = aba_equip.row_values(1)
        cabecalho = [str(c).strip() for c in cabecalho]

        if "Status" not in cabecalho:
            st.error("Coluna 'Status' não encontrada na planilha.")
            return

        coluna_status = cabecalho.index("Status") + 1

        # Atualiza célula
        aba_equip.update_cell(linha_planilha, coluna_status, novo_status.upper())

        st.success(f"Status do equipamento {numero} atualizado para {novo_status.upper()}!")

    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")

# =============================
# INTERFACE
# =============================

st.set_page_config(layout="wide")
st.title("📦 CONTROLE DE MEIOS ORGÂNICOS")

menu = st.sidebar.radio(
    "Navegação",
    [
        "📊 Planilha",
        "🚜 Cadastrar Equipamentos",
        "🔧 Registrar Manutenções",
        "🔧 Registrar Avarias",
        "📜 Histórico de Manutenções",
        "📜 Histórico de Avarias"
    ]
)

# =============================
# DASHBOARD
# =============================

if menu == "📊 Planilha":

    df = carregar_equip()

    if not df.empty:

        ativos = df[df["Ativo"] == "Sim"]

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Operando",
                    len(ativos[ativos["Status"] == "OPERANDO"]))

        col2.metric("Com Restrição",
                    len(ativos[ativos["Status"] == "OPERANDO COM RESTRIÇÕES"]))

        col3.metric("Inoperante",
                    len(ativos[ativos["Status"] == "INOPERANTE"]))

        col4.metric("Provável Baixa",
                    len(ativos[ativos["Status"] == "PROVÁVEL BAIXA/LVAD"]))

        st.dataframe(ativos)

    else:
        st.info("Nenhum equipamento cadastrado.")

# =============================
# CADASTRAR EQUIPAMENTO
# =============================

elif menu == "🚜 Cadastrar Equipamentos":

    st.subheader("Novo Equipamento")

    numero = st.text_input("Número (01 a 99)")
    marca = st.text_input("Marca")
    modelo = st.text_input("Modelo")
    ano = st.text_input("Ano (4 dígitos)")
    classificacao = st.selectbox(
        "Classificação",
        ["Retrátil", "Selecionadora", "Patolada"]
    )
    numpart = st.text_input("NUMPART (Opcional)")
    horimetro = st.text_input("Horímetro (Opcional)")
    chassi = st.text_input("Chassi (Obrigatório)")
    obs = st.text_area("Observações (Opcional)")

    if st.button("Salvar Equipamento"):

        numero = numero.zfill(2)

        if not numero.isdigit() or not (1 <= int(numero) <= 99):
            st.error("Número deve ser entre 01 e 99.")
        elif numero_existe(numero):
            st.error("Número já cadastrado.")
        elif not ano.isdigit() or len(ano) != 4:
            st.error("Ano deve conter 4 dígitos.")
        elif not marca or not modelo or not chassi:
            st.error("Preencha todos os campos obrigatórios.")
        else:

            nova_linha = [
                "",
                numero,
                "EMPILHADEIRA",
                marca.upper(),
                modelo.upper(),
                ano,
                classificacao.upper(),
                numpart.upper(),
                horimetro.upper(),
                chassi.upper(),
                "OPERANDO",
                datetime.now().strftime("%d/%m/%Y"),
                obs.upper(),
                "Sim"
            ]

            adicionar_equipamento(nova_linha)
            st.success("Equipamento cadastrado com sucesso!")

# =============================
# REGISTRAR AVARIA
# =============================

elif menu == "🔧 Registrar Avarias":

    df = carregar_equip()
    ativos = df[df["Ativo"] == "Sim"]

    if not ativos.empty:

        numero = st.selectbox("Equipamento", ativos["Numero_Meio"])
        data_ident = st.date_input("Data da Identificação")
        data_incidente = st.date_input("Data do Incidente (Opcional)")
        descricao = st.text_area("Descrição")

        gravidade = st.selectbox(
            "Gravidade",
            [
                "BAIXA (continua operando)",
                "MÉDIA (operando com restrição)",
                "ALTA (inoperante ou provável baixa)"
            ]
        )

        novo_status = st.selectbox(
            "Alterar Status para:",
            [
                "OPERANDO COM RESTRIÇÕES",
                "INOPERANTE",
                "PROVÁVEL BAIXA/LVAD"
            ]
        )

        if st.button("Registrar Avaria"):

            aba_avarias.append_row([
                "",
                numero,
                data_ident.strftime("%d/%m/%Y"),
                data_incidente.strftime("%d/%m/%Y"),
                descricao.upper(),
                gravidade,
                novo_status
            ])

            atualizar_status(numero, novo_status)

            st.success("Avaria registrada e status atualizado.")

    else:
        st.info("Nenhum equipamento ativo.")

# =============================
# REGISTRAR MANUTENÇÃO
# =============================

elif menu == "🔧 Registrar Manutenções":

    df = carregar_equip()
    ativos = df[df["Ativo"] == "Sim"]

    if not ativos.empty:

        numero = st.selectbox("Equipamento", ativos["Numero_Meio"])
        data_manut = st.date_input("Data da Manutenção")

        processo = st.selectbox(
            "Processo",
            [
                "Pregão",
                "Dispensa Eletrônica",
                "Suprimento de Fundos",
                "Garantia",
                "Contrato de Manutenção",
                "Outro"
            ]
        )

        numero_processo = st.text_input(
            "Número da contratação (ex: NOTA DE EMPENHO Nº 01/2026)"
        )

        tipo_manut = st.selectbox(
            "Tipo",
            ["Manutenção Completa", "Manutenção Parcial"]
        )

        empresa = st.text_input("Empresa")
        contato = st.text_input("Pessoa / Contato")

        novo_status = st.selectbox(
            "Alterar Status para:",
            ["OPERANDO", "OPERANDO COM RESTRIÇÕES"]
        )

        if st.button("Registrar Manutenção"):

            aba_manut.append_row([
                "",
                numero,
                data_manut.strftime("%d/%m/%Y"),
                processo.upper() + " Nº " + numero_processo.upper(),
                tipo_manut.upper(),
                empresa.upper(),
                contato.upper(),
                novo_status
            ])

            atualizar_status(numero, novo_status)

            st.success("Manutenção registrada e status atualizado.")

    else:
        st.info("Nenhum equipamento ativo.")

# =============================
# HISTÓRICO MANUTENÇÕES
# =============================

elif menu == "📜 Histórico de Manutenções":

    df = carregar_manut()

    if not df.empty:

        filtro = st.selectbox(
            "Filtrar por Equipamento",
            ["Todos"] + list(df["Numero_Meio"].unique())
        )

        if filtro != "Todos":
            df = df[df["Numero_Meio"] == filtro]

        st.dataframe(df)

    else:
        st.info("Nenhuma manutenção registrada.")

# =============================
# HISTÓRICO AVARIAS
# =============================

elif menu == "📜 Histórico de Avarias":

    df = carregar_avarias()

    if not df.empty:

        filtro = st.selectbox(
            "Filtrar por Equipamento",
            ["Todos"] + list(df["Numero_Meio"].unique())
        )

        if filtro != "Todos":
            df = df[df["Numero_Meio"] == filtro]

        st.dataframe(df)

    else:

        st.info("Nenhuma avaria registrada.")

