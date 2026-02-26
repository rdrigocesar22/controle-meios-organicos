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

    from datetime import date
    import plotly.express as px

    df = carregar_equip()

    if not df.empty:

        df["Ativo"] = df["Ativo"].astype(str).str.strip().str.upper()
        ativos = df[df["Ativo"] == "SIM"]
        ativos["Status"] = ativos["Status"].astype(str).str.strip().str.upper()
        
        # =============================
        # MÉTRICAS
        # =============================
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Operando",
                    len(ativos[ativos["Status"] == "OPERANDO"]))

        col2.metric("Com Restrição",
                    len(ativos[ativos["Status"] == "OPERANDO COM RESTRIÇÕES"]))

        col3.metric("Inoperante",
                    len(ativos[ativos["Status"] == "INOPERANTE"]))

        col4.metric("Provável Baixa",
                    len(ativos[ativos["Status"] == "PROVÁVEL BAIXA/LVAD"]))

        # =============================
        # GRÁFICO PIZZA - STATUS
        # =============================
        st.subheader("📌 Distribuição por Status")

        status_counts = ativos["Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Quantidade"]

        fig_pizza = px.pie(
            status_counts,
            names="Status",
            values="Quantidade",
            hole=0.4,
            color="Status",
            color_discrete_map={
                "Operando": "#00E676",                  # Verde bem vivo
                "Operando com restrições": "#FFD600",   # Amarelo vibrante
                "Inoperante": "#FF1744"                 # Vermelho intenso
            }
        )

        st.plotly_chart(fig_pizza, use_container_width=True)

        st.divider()

        # =============================
        # TABELA
        # =============================
        st.subheader("📋 Equipamentos Ativos")

        # Remove a coluna ID se existir
        tabela_exibicao = ativos.drop(columns=["ID"], errors="ignore")

        st.dataframe(tabela_exibicao, use_container_width=True)

        st.divider()
        
        # =============================
        # SLIDER DE PERÍODO
        # =============================
        st.subheader("📅 Manutenções e Avarias no Período")

        data_inicio_padrao = date(2026, 1, 1)
        data_fim_padrao = date.today()

        periodo = st.slider(
            "Selecione o período:",
            min_value=data_inicio_padrao,
            max_value=data_fim_padrao,
            value=(data_inicio_padrao, data_fim_padrao)
        )

        data_inicio, data_fim = periodo

        # =============================
        # CARREGAR REGISTROS
        # =============================
        df_manut = carregar_manut()
        df_avarias = carregar_avarias()

        # Padroniza nome da coluna de data
        if not df_manut.empty:
            df_manut["Data"] = pd.to_datetime(df_manut["Data_Manutencao"], dayfirst=True)
            df_manut["Tipo_Registro"] = "Manutenção"

        if not df_avarias.empty:
            df_avarias["Data"] = pd.to_datetime(df_avarias["Data_Identificacao"], dayfirst=True)
            df_avarias["Tipo_Registro"] = "Avaria"

        df_reg = pd.concat([df_manut, df_avarias], ignore_index=True)

        if not df_reg.empty:

            df_filtrado = df_reg[
                (df_reg["Data"] >= pd.to_datetime(data_inicio)) &
                (df_reg["Data"] <= pd.to_datetime(data_fim))
            ]

            tipo_counts = df_filtrado["Tipo_Registro"].value_counts().reset_index()
            tipo_counts.columns = ["Tipo", "Quantidade"]

            fig_bar = px.bar(
                tipo_counts,
                x="Tipo",
                y="Quantidade",
                color="Tipo"
            )

            st.plotly_chart(fig_bar, use_container_width=True)

        else:
            st.info("Nenhum registro de manutenção ou avaria encontrado.")

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
    df["Ativo"] = df["Ativo"].astype(str).str.strip().str.upper()
    ativos = df[df["Ativo"] == "SIM"]

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

            data_inc_str = data_incidente.strftime("%d/%m/%Y") if data_incidente else ""
            
            aba_avarias.append_row([
                "",
                numero,
                data_ident.strftime("%d/%m/%Y"),
                data_inc_str,
                "AVARIA",
                gravidade,
                novo_status,
                descricao.upper(),
                "Não"
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
    df["Ativo"] = df["Ativo"].astype(str).str.strip().str.upper()
    ativos = df[df["Ativo"] == "SIM"]
    
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
                "MANUTENÇÃO",
                data_manut.strftime("%d/%m/%Y"),
                processo.upper(),
                numero_processo.upper(),
                tipo_manut.upper(),
                empresa.upper(),
                contato.upper(),
                novo_status,
                ""
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






