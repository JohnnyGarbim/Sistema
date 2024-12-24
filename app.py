import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta


# Conexão com o banco de dados
def get_connection():
    conn = sqlite3.connect("fechamento_semanal.db")
    return conn


# Função para criar tabelas (executa uma vez)
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fechamento_semanal (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        Installer TEXT NOT NULL,
        Customer_name TEXT NOT NULL,
        Job_number TEXT NOT NULL,
        Labor_REAL NOT NULL,
        Expenses REAL NOT NULL,
        Pay_date TEXT NOT NULL,
        Job_date TEXT NOT NULL,
        Prices_after_percent REAL NOT NULL,
        Discount REAL NOT NULL,
        Extras_details TEXT,
        Back_charge REAL NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS extras (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        Installer TEXT NOT NULL,
        Extra_name TEXT NOT NULL,
        Extra_value REAL NOT NULL,
        Extra_date TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS back_charges (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        Installer TEXT NOT NULL,
        Back_charge value REAL NOT NULL,
        reason TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS summary (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        Installer TEXT NOT NULL,
        Total_labor REAL NOT NULL,
        Total_expenses REAL NOT NULL,
        Total_extras REAL NOT NULL,
        Total_back_charges REAL NOT NULL,
        Total_price REAL NOT NULL,
        Report date TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()


# Função para inserir dados no banco
def insert_data(table, data):
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ', '.join(['?'] * len(data))
    cursor.execute(f"INSERT INTO {table} VALUES (NULL, {placeholders})", tuple(data))
    conn.commit()
    conn.close()


# Função para consultar dados do banco
def query_data(query, params=()):
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# Função para salvar os dados no banco
def save_to_database(data):
    conn = get_connection()
    cursor = conn.cursor()

    # Converta colunas de datas para strings compatíveis com SQLite
    if "pay_date" in data.columns:
        data["pay_date"] = data["pay_date"].dt.strftime('%Y-%m-%d')
    if "job_date" in data.columns:
        data["job_date"] = data["job_date"].dt.strftime('%Y-%m-%d')

    for _, row in data.iterrows():
        cursor.execute("""
        INSERT INTO fechamento_semanal (
            installer, customer_name, job_number, labor, expenses, pay_date, 
            job_date, prices_after_percent, discount, extras_details, back_charge
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["installer"], row["customer name"], row["job number"], row["labor"], row["expenses"],
            row["pay_date"], row["job_date"], row["prices_after_percent"], row["discount"],
            row.get("extras_details", ""), row["back_charge"]
        ))
    conn.commit()
    conn.close()
# Inicializa o banco de dados
create_tables()

# Função para adicionar estilo personalizado
def add_custom_style():
    st.markdown(
        """
        <style>
        .main {
            background-color: #f8f9fa;
            font-family: Arial, sans-serif;
        }
        header, .stApp {
            background-color: #ffffff;
            border-bottom: 2px solid #007bff;
        }
        .stButton button {
            background-color: #007bff;
            color: white;
            font-size: 16px;
            border-radius: 5px;
        }
        .stButton button:hover {
            background-color: #0056b3;

        }
        .center-logo {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# Classe PDF para relatórios
class CustomStyledPDF(FPDF):
    def __init__(self, orientation="L", unit="mm", format="A4"):
        super().__init__(orientation, unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_fill_color(200, 220, 255)
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "PM Home Remodeling System", ln=True, align="C", fill=True)
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, f"Week - {self.period}", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Installer: {self.team_name}", align="C")

    def set_team_and_period(self, team_name, period):
        self.team_name = team_name
        self.period = period

    def add_table(self, title, headers, rows):
        self.set_font("Arial", "B", 10)
        self.cell(0, 10, title, ln=True, align="L")
        self.ln(5)

        self.set_fill_color(180, 180, 180)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 8)
        col_widths = [25, 50, 30, 30, 40, 40, 30]
        for header, width in zip(headers, col_widths):
            self.cell(width, 8, header, border=1, align="C", fill=True)
        self.ln()

        self.set_font("Arial", "", 8)
        self.set_text_color(0, 0, 0)
        for row in rows:
            for cell, width in zip(row, col_widths):
                self.cell(width, 8, str(cell), border=1, align="C")
            self.ln()


# Função para gerar o PDF detalhado
def generate_detailed_pdf(data, summary, team_name, period, extras, back_charge):
    pdf = CustomStyledPDF()
    pdf.set_team_and_period(team_name, period)
    pdf.add_page()

    summary_headers = [
        "ID", "Name", "Address", "City", "State",
        "Phone Number", "TOTAL after %"
    ]
    summary_rows = [
        [
            row["ID"], row["Name"], row["Address"], row["City"],
            row["State"], row["Phone Number"], f"${row['TOTAL after %']:.2f}"
        ]
        for row in summary
    ]
    pdf.add_table("Summary", summary_headers, summary_rows)

    detail_headers = [
        "Installer", "Customer Name", "Job Number", "Labor",
        "When the job was done", "Prices after %", "Despesas"
    ]
    detail_rows = [
        [
            row["installer"], row["customer name"], row["job number"],
            f"${row['labor']:.2f}", row["when the job was done"],
            f"${row['prices after %']:.2f}", f"${row['despesas']:.2f}"
        ]
        for row in data
    ]
    pdf.add_table("Details", detail_headers, detail_rows)

    # Exibir Extras e Back Charge
    if extras or back_charge > 0:
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Extras e Back Charges", ln=True, align="L")
        pdf.set_font("Arial", "", 10)

        # Listar extras, se existirem
        for extra in extras:
            pdf.cell(
                0,
                10,
                f"Extra: {extra['name']} - ${extra['value']:.2f} on {extra['date']}",
                ln=True,
                align="L",
            )

        # Exibir Back Charge, se aplicado
        if back_charge > 0:
            pdf.cell(
                0,
                10,
                f"Back Charge aplicado: -${back_charge:.2f}",
                ln=True,
                align="L",
            )

    return pdf.output(dest="S").encode("latin1")


# Função para a página inicial
def homepage():
    st.title("Bem-vindo ao Sistema de Fechamento Semanal")

    # Logotipo centralizado com `st.image`
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.image("logo.png", width=150)  # Substitua o caminho, se necessário
    st.markdown("</div>", unsafe_allow_html=True)

    # Texto centralizado
    st.markdown(
        """
        <div style="text-align: center;">
            <h2>Sistema de Gestão e Relatórios</h2>
            <p style="font-size: 18px; color: #6c757d;">
                Escolha uma das funcionalidades abaixo para começar.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Botões lado a lado usando colunas
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Fechamento Semanal"):
            st.session_state.page = "fechamento_semanal"

    with col2:
        if st.button("Relatório Semanal Geral"):
            st.session_state.page = "relatorio_semanal_geral"

    with col3:
        if st.button("Labor Bill"):
            st.session_state.page = "Labor Bill"

# Função para o Fechamento Semanal
def fechamento_semanal():


    st.title("Fechamento Semanal")
    st.markdown("### Gerador de relatórios de pagamento semanal")

    # Adicionando uma chave única ao file_uploader
    uploaded_file = st.file_uploader("Upload your Excel file", type=["xls", "xlsx", "xlsm"],
                                     key="fechamento_semanal_file")

    if uploaded_file:
        df = pd.read_excel(uploaded_file, header=1)

        st.title("Weekly Payment Report Generator")

        team_discounts = {
            "PM2": 0.30,
            "PM3": 0.20,
            "PM4": 0.20,
            "PM5": 0.20,
            "PM6": 0.30,
            "PM7": 0.20,
            "PM8": 0.20,
        }

        if uploaded_file:
            df.columns = [col.strip().lower() for col in df.columns]

            if "unnamed: 8" in df.columns:
                df.rename(columns={"unnamed: 8": "customer name"}, inplace=True)
            if "job #" in df.columns:
                df.rename(columns={"job #": "job number"}, inplace=True)
            if "date" in df.columns:
                df.rename(columns={"date": "when the job was done"}, inplace=True)

            df = df.dropna(subset=["customer name"])

            st.write("### Uploaded Data Preview:")
            st.dataframe(df)

            required_columns = ["installer", "pay date", "labor", "customer name", "job number",
                                "when the job was done"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.error(f"Missing required columns: {', '.join(missing_columns)}")
                return

            next_friday = (datetime.today() + timedelta((4 - datetime.today().weekday()) % 7)).strftime('%Y-%m-%d')
            df["pay date"] = pd.to_datetime(df["pay date"], errors="coerce")
            filtered_data = df[df["pay date"] == next_friday]

            if filtered_data.empty:
                st.warning(f"No payments found for the next Friday ({next_friday}).")
                return

            st.write(f"### Edit Payments and Expenses for Each Installer (Payments for {next_friday}):")

            filtered_data["installer"] = filtered_data["installer"].astype(str).str.extract(r'(\d+)', expand=False)
            filtered_data["installer"] = filtered_data["installer"].fillna("0")
            filtered_data["installer"] = "PM" + filtered_data["installer"]

            installers = sorted(filtered_data["installer"].unique(), key=lambda x: int(x[2:]))
            tabs = st.tabs(installers)

            edited_data = []
            extras_data = {}
            back_charges = {}

            for tab, installer in zip(tabs, installers):
                with tab:
                    installer_data = filtered_data[filtered_data["installer"] == installer].copy()
                    st.write(f"#### Data for {installer}")

                    if "prices after %" not in installer_data.columns:
                        installer_data["prices after %"] = 0.0

                    for idx, row in installer_data.iterrows():
                        labor = max(row["labor"], 0.0)
                        despesas = max(row.get("despesas", 0.0), 0.0)

                        labor = st.number_input(
                            f"Labor for {row['customer name']}",
                            min_value=0.0,
                            value=labor,
                            step=0.01,
                            key=f"{installer}_{idx}_labor"
                        )
                        despesas = st.number_input(
                            f"Expenses for {row['customer name']}",
                            min_value=0.0,
                            value=despesas,
                            step=0.01,
                            key=f"{installer}_{idx}_despesas"
                        )

                        installer_data.at[idx, "labor"] = labor
                        installer_data.at[idx, "despesas"] = despesas

                        discount = team_discounts.get(installer, 0.0)
                        prices_after_discount = (labor - despesas) * (1 - discount)
                        prices_after_percent = prices_after_discount + despesas

                        installer_data.at[idx, "prices after %"] = prices_after_percent

                    st.dataframe(installer_data)

                    extras = []
                    num_extras = st.number_input(
                        f"How many extra services for {installer}?",
                        min_value=0,
                        value=0,
                        step=1,
                        key=f"{installer}_num_extras",
                    )

                    for i in range(num_extras):
                        st.write(f"**Extra Service #{i + 1}**")
                        extra_name = st.text_input(f"Extra Service Name #{i + 1} ({installer})",
                                                   key=f"{installer}_{i}_name")
                        extra_value = st.number_input(
                            f"Extra Service Value #{i + 1} ({installer})",
                            min_value=0.0,
                            step=0.01,
                            key=f"{installer}_{i}_value",
                        )
                        extra_date = st.date_input(
                            f"Date of Extra Service #{i + 1} ({installer})", key=f"{installer}_{i}_date"
                        )
                        extras.append(
                            {
                                "name": extra_name,
                                "value": extra_value,
                                "date": extra_date,
                            }
                        )
                    extras_data[installer] = extras

                    # Adicionar Back Charge
                    back_charge = st.number_input(
                        f"Back Charge para {installer} (subtração do total semanal):",
                        min_value=0.0,
                        step=0.01,
                        key=f"{installer}_back_charge",
                    )
                    back_charges[installer] = back_charge

                    edited_data.append(installer_data)

            # Gerar relatórios para cada instalador
            for installer_data in edited_data:
                installer = installer_data["installer"].iloc[0]
                total_prices_after_percent = installer_data["prices after %"].sum()

                discount = team_discounts.get(installer, 0.0)
                extras = extras_data.get(installer, [])
                extra_total = sum(extra["value"] for extra in extras)
                back_charge = back_charges.get(installer, 0.0)
                final_total = total_prices_after_percent + extra_total - back_charge

                summary = [{
                    "ID": installer,
                    "Name": f"Installer {installer}",
                    "Address": "Sample Address",
                    "City": "Sample City",
                    "State": "ST",
                    "Phone Number": "(000) 000-0000",
                    "TOTAL after %": final_total
                }]
                pdf_content = generate_detailed_pdf(
                    installer_data.to_dict(orient="records"),
                    summary,
                    f"Installer {installer}",
                    next_friday,
                    extras,
                    back_charge
                )

                # Adicionar botão para baixar o relatório
                st.download_button(
                    label=f"Download Report for {installer}",
                    data=pdf_content,
                    file_name=f"{installer}_Report_{next_friday}.pdf",
                    mime="application/pdf"
                )

    if uploaded_file:
        df = pd.read_excel(uploaded_file, header=1)
        df.columns = [col.strip().lower() for col in df.columns]

        # Renomear colunas conforme necessário
        df.rename(columns={
            "unnamed: 8": "customer name",
            "job #": "job number",
            "date": "job_date",
            "Pay Date": "pay_date",
            "pay date": "pay_date",
            "Data de Pagamento": "pay_date"
        }, inplace=True)

        # Verificar se a coluna 'pay_date' está presente
        if "pay_date" not in df.columns:
            st.error("A coluna 'Pay Date' não foi encontrada no arquivo Excel. Verifique os dados.")
            st.stop()

        # Convertendo 'pay_date' para datetime
        df["pay_date"] = pd.to_datetime(df["pay_date"], errors="coerce")
        if df["pay_date"].isna().all():
            st.error("Nenhuma data válida foi encontrada na coluna 'Pay Date'. Verifique os dados.")
            st.stop()

        # Filtrar dados editáveis
        df = df.dropna(subset=["customer name"])
        df["pay_date"] = pd.to_datetime(df["pay_date"], errors="coerce")

        # Determinar a última semana no campo "Pay Date"
        last_week_date = df["pay_date"].max()
        filtered_df = df[df["pay_date"] == last_week_date]

        # Adicionar edição dos valores
        edited_data = []
        for idx, row in filtered_df.iterrows():
            col1, col2 = st.columns(2)
            with col1:
                labor = st.number_input(f"Labor para {row['customer name']}", value=row["labor"], key=f"labor_{idx}")
            with col2:
                expenses = st.number_input(f"Despesas para {row['customer name']}", value=row.get("expenses", 0.0),
                                            key=f"expenses_{idx}")

            row["labor"] = labor
            row["expenses"] = expenses
            row["prices_after_percent"] = labor - expenses  # Exemplo de cálculo
            edited_data.append(row)

        # Converta os dados editados para um DataFrame
        edited_df = pd.DataFrame(edited_data)

        # Verifica se a coluna 'discount' está presente; se não, adiciona com valor padrão 0.0
        if "discount" not in edited_df.columns:
            edited_df["discount"] = 0.0

        if "back_charge" not in edited_df.columns:
            edited_df["back_charge"] = 0.0

        st.write("### Dados Editados da Última Semana:")
        st.dataframe(edited_df)

        # Salvar dados no banco de dados
        if st.button("Salvar no Banco de Dados"):
            save_to_database(edited_df)
            st.success(f"Dados da última semana ({last_week_date.strftime('%Y-%m-%d')}) salvos no banco de dados com sucesso!")

    if st.button("Voltar para a Página Inicial"):
        st.session_state.page = "homepage"


# Função para o Relatório Semanal Geral
def relatorio_semanal_geral():
    st.title("Relatório Semanal Geral")
    st.markdown("### Gerador de relatórios gerais da semana")

    # Adicione aqui o código para o relatório geral
    uploaded_file = st.file_uploader("Upload your Excel file", type=["xls", "xlsx", "xlsm"],
                                     key="relatorio_semanal_file")
    if uploaded_file:
        df = pd.read_excel(uploaded_file, header=1)
        st.write("### Uploaded Data Preview:")
        st.dataframe(df)
        st.markdown("### Aqui estará o processamento específico do Relatório Geral...")

    if st.button("### Voltar para a Página Inicial"):
        st.session_state.page = "homepage"


# Função para o Labor Bill
def LaborBill():
    st.title("Labor Bill")
    st.markdown("ATLANTA Labor Bill")

    if st.button("Voltar para a Página Inicial"):
        st.session_state.page = "homepage"


# Configuração inicial para controle de navegação
if "page" not in st.session_state:
    st.session_state.page = "homepage"

# Adicionar estilos
add_custom_style()

# Controlador de navegação
if st.session_state.page == "homepage":
    homepage()
elif st.session_state.page == "fechamento_semanal":
    fechamento_semanal()
elif st.session_state.page == "relatorio_semanal_geral":
    relatorio_semanal_geral()
elif st.session_state.page == "Labor Bill":
    LaborBill()
