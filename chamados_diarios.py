import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import os
from plyer import notification

# Autenticação com Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('projeto-450018-5c89ae4dda27.json', scope)
client = gspread.authorize(creds)

# Configurações da planilha
PLANILHA_URL = 'https://docs.google.com/spreadsheets/d/1FFm7S1A3Yr2xrJjY5spuMw6RTnL4gQVkHhu6uFIZnjs/edit?gid=0'
ABA_NOME = 'Página1'
COLUNAS = {
    'Time': 'Time',
    'Estado': 'Estado',
    'Cidade': 'Cidade',
    'Cell Name': 'Cell Name',
    'Downlink Resource Block Utilizing Rate (%)': 'Downlink Resource Block Utilizing Rate (%)',
    'Uplink Resource Block Utilizing Rate (%)': 'Uplink Resource Block Utilizing Rate (%)',
    'Average User Number(number)': 'Average User Number(number)',
    'Vezes que bateu 90 Down': 'Vezes que bateu 90 Down',
    'Vezes que bateu 90 UP': 'Vezes que bateu 90 UP',
}
PLANILHA_LOCAL = 'chamados.xlsx'

# Função para processar a planilha
def processar_planilha(url, nome_aba, colunas):
    sheet = client.open_by_url(url).worksheet(nome_aba)
    data = sheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])

    # Filtrar apenas as colunas desejadas
    df = df[list(colunas.values())].copy()

    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
    data_mais_recente = df['Time'].max().normalize()
    df_hoje = df[df['Time'].dt.normalize() == data_mais_recente].copy()

    # Substituir vírgula por ponto antes de converter
    df_hoje['Downlink Resource Block Utilizing Rate (%)'] = df_hoje['Downlink Resource Block Utilizing Rate (%)'].str.replace(',', '.').astype(float)
    df_hoje['Uplink Resource Block Utilizing Rate (%)'] = df_hoje['Uplink Resource Block Utilizing Rate (%)'].str.replace(',', '.').astype(float)

    df_filtrado = df_hoje[
        (df_hoje['Downlink Resource Block Utilizing Rate (%)'] > 95)
        | (df_hoje['Uplink Resource Block Utilizing Rate (%)'] > 95)
    ].copy()

    return df_filtrado

# Processar a planilha
df_filtrado = processar_planilha(PLANILHA_URL, ABA_NOME, COLUNAS)

# Carregar a planilha local (se existir)
if os.path.exists(PLANILHA_LOCAL):
    df_local = pd.read_excel(PLANILHA_LOCAL)
else:
    df_local = pd.DataFrame(
        columns=[
            'Título', 'Descrição', 'Responsável', 'Status', 'Observações', 'ID', 'Solução',
            'Cidade', 'UF', 'Site', 'Cell', 'Tecnologia', 'Tipo', 'Alteração',
            'Data Aplicação Início', 'Data Aplicação Fim', 'Antes', 'Depois', 'OBS',
            'Material de Apoio', 'Data de Abertura', 'Alteracao', 'Data Aplicacao Inicio',
            'Data Aplicacao Fim'
        ]
    )

# Iterar sobre os resultados e criar os chamados
for _, row in df_filtrado.iterrows():
    cidade = row['Cidade']
    estado = row['Estado']
    cell = row['Cell Name']
    tecnologia = 'LTE' if cell.strip().upper().startswith('B40') else 'NR'
    cell_exibicao = f"{tecnologia} {cell}"
    responsavel = "Erickson".strip()  # Garante que o responsável é sempre Erickson e remove espaços extras

    descricao = (
        f"Downlink Resource Block Utilizing Rate (%): {row['Downlink Resource Block Utilizing Rate (%)'] if pd.notna(row['Downlink Resource Block Utilizing Rate (%)']) else 'N/A'}\n"
        f"Uplink Resource Block Utilizing Rate (%): {row['Uplink Resource Block Utilizing Rate (%)'] if pd.notna(row['Uplink Resource Block Utilizing Rate (%)']) else 'N/A'}\n"
        f"Average User Number: {row['Average User Number(number)'] if pd.notna(row['Average User Number(number)']) else 'N/A'}\n"
        f"Vezes que bateu 90 Down: {row['Vezes que bateu 90 Down'] if pd.notna(row['Vezes que bateu 90 Down']) else 'N/A'}\n"
        f"Vezes que bateu 90 UP: {row['Vezes que bateu 90 UP'] if pd.notna(row['Vezes que bateu 90 UP']) else 'N/A'}\n"
    )

    data_abertura = datetime.now()  # Captura a data e hora atual
    novo_chamado = {
        'Título': '',  # Adicione campos vazios ou valores apropriados
        'Descrição': descricao,
        'Responsável': responsavel,
        'Status': 'Aberto',
        'Observações': 'Alarme',
        'ID': None,  # O ID será gerado automaticamente
        'Solução': '',
        'Cidade': cidade,
        'UF': estado,
        'Site': cell_exibicao,
        'Cell': cell_exibicao,
        'Tecnologia': tecnologia,
        'Tipo': 'Alarme',
        'Alteração': '',
        'Data Aplicação Início': data_abertura.strftime('%Y-%m-%d %H:%M:%S'),
        'Data Aplicação Fim': '',
        'Antes': '',
        'Depois': '',
        'OBS': 'Alarme',
        'Material de Apoio': '',
        'Data de Abertura': data_abertura.strftime('%Y-%m-%d %H:%M:%S'),
        'Alteracao': '',
        'Data Aplicacao Inicio': data_abertura.strftime('%Y-%m-%d %H:%M:%S'),
        'Data Aplicacao Fim': ''
    }

    novo_id = 1 if df_local.empty else df_local['ID'].max() + 1
    novo_chamado['ID'] = novo_id
    df_local = pd.concat([df_local, pd.DataFrame([novo_chamado])], ignore_index=True)

# Salva os dados atualizados
df_local.to_excel(PLANILHA_LOCAL, index=False)

# Envia notificação com ícone e formatação melhorada
mensagem_notificacao = f"""
📢 {len(df_filtrado)} novo(s) chamado(s) registrado(s)!

🔧 Sistema: Techflow Bot
📅 Data: {datetime.now().strftime('%d/%m/%Y')}
🕒 Hora: {datetime.now().strftime('%H:%M:%S')}
"""

try:
    notification.notify(
        title='🚨 Techflow Bot - Alerta de Chamado',
        message=mensagem_notificacao.strip(),
        app_icon=r'C:\Users\erickson.silva_grupo\Desktop\Sistema de chamado\logo.ico',
        timeout=10,
    )
except Exception as e:
    print(f"Erro ao enviar notificação: {e}")

print("✅ Notificação de chamados gerados com sucesso.")