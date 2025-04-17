from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import pandas as pd
import os
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import random
from datetime import datetime
from flask import jsonify
from fuzzywuzzy import process

app = Flask(__name__)
app.secret_key = "super secret key"

PLANILHA = 'chamados.xlsx'
PLANILHA_BLACKLIST = 'Blacklist.xlsx'  # Defina o caminho para sua planilha da blacklist


def inicializar_planilha():
    if not os.path.exists(PLANILHA):
        colunas = [
            'ID', 'Cidade', 'UF', 'Site', 'Cell', 'Tecnologia', 'Tipo', 'Alteração',
            'Data Aplicação Início', 'Data Aplicação Fim', 'Antes', 'Depois', 'Status',
            'OBS', 'Descrição', 'Material de Apoio', 'Responsável', 'Data de Abertura'
        ]
        df = pd.DataFrame(columns=colunas)
        df.to_excel(PLANILHA, index=False)


def inicializar_blacklist():
    if not os.path.exists(PLANILHA_BLACKLIST):
        # Adapte as colunas conforme a estrutura da sua planilha da blacklist
        colunas_blacklist = [
            'ID', 'Cidade', 'UF', 'Site', 'Cell', 'Tecnologia', 'Tipo', 'Alteração',
            'Data Aplicação Início', 'Data Aplicação Fim', 'Antes', 'Depois', 'Status',
            'OBS', 'Descrição', 'Material de Apoio', 'Responsável', 'Data de Abertura'
        ]
        df_blacklist = pd.DataFrame(columns=colunas_blacklist)
        df_blacklist.to_excel(PLANILHA_BLACKLIST, index=False)


def ler_blacklist():
    try:
        df_blacklist = pd.read_excel(PLANILHA_BLACKLIST)
    except Exception as e:
        print(f"Erro ao ler blacklist: {e}")
        df_blacklist = pd.DataFrame(columns=[
            'ID', 'Cidade', 'UF', 'Site', 'Cell', 'Tecnologia', 'Tipo', 'Alteração',
            'Data Aplicação Início', 'Data Aplicação Fim', 'Antes', 'Depois', 'Status',
            'OBS', 'Descrição', 'Material de Apoio', 'Responsável', 'Data de Abertura'
        ])  # Retorna DataFrame vazio com colunas
    return df_blacklist


def salvar_blacklist(df_blacklist):
    try:
        df_blacklist.to_excel(PLANILHA_BLACKLIST, index=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar blacklist: {e}")
        return False


def get_coords(cidade, uf):
    geolocator = Nominatim(user_agent="chamados-dashboard")
    try:
        location = geolocator.geocode(f"{cidade}, {uf}, Brasil")
        if location:
            return location.latitude, location.longitude
    except GeocoderTimedOut:
        return get_coords(cidade, uf)
    return None, None


@app.before_request
def proteger_rotas():
    rotas_livres = ['login', 'static']
    if not session.get('logado') and request.endpoint not in rotas_livres and not request.endpoint.startswith('static'):
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        if usuario == 'admin' and senha == '123':
            session['logado'] = True
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos!', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logado', None)
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('login'))


@app.route('/')
def index():
    try:
        df = pd.read_excel(PLANILHA, dtype={'Descrição': str}).fillna({'Descrição': ''})
    except Exception as e:
        df = pd.DataFrame()
        print(f"Erro ao carregar planilha: {e}")
    chamados = df[df['OBS'] != 'Alarme'].to_dict(orient='records')  # Filtra para excluir "Alarme"
    return render_template('index.html', chamados=chamados, now=datetime.now())


@app.route('/novo')
def novo_chamado():
    return render_template('novo_chamado.html', now=datetime.now())


@app.route('/criar', methods=['POST'])
def criar_chamado():
    dados = {
        'Cidade': request.form.get('cidade'),
        'UF': request.form.get('uf'),
        'Site': request.form.get('site'),
        'Cell': request.form.get('cell'),
        'Tecnologia': request.form.get('tecnologia'),
        'Tipo': request.form.get('tipo'),
        'Alteração': request.form.get('alteracao'),
        'Data Aplicação Início': request.form.get('aplicacao_inicio'),
        'Data Aplicação Fim': request.form.get('aplicacao_fim'),
        'Antes': request.form.get('antes'),
        'Depois': request.form.get('depois'),
        'Status': request.form.get('status'),
        'OBS': request.form.get('obs'),
        'Descrição': request.form.get('descricao'),
        'Material de Apoio': request.form.get('material'),
        'Responsável': request.form.get('responsavel'),
        'Data de Abertura': pd.to_datetime(request.form.get('aplicacao_inicio'), errors='coerce').strftime('%Y-%m-%d %H:%M:%S')
        if request.form.get('aplicacao_inicio') else datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    }

    try:
        df = pd.read_excel(PLANILHA)
    except Exception as e:
        df = pd.DataFrame(columns=['ID'] + list(dados.keys()))
        print(f"Erro ao ler planilha: {e}")

    novo_id = 1 if df.empty else df['ID'].max() + 1
    dados['ID'] = novo_id
    df = pd.concat([df, pd.DataFrame([dados])], ignore_index=True)
    df.to_excel(PLANILHA, index=False)
    flash('Chamado criado com sucesso!', 'success')
    return redirect(url_for('index'))


@app.route('/concluir/<int:id>')
def concluir_chamado(id):
    df = pd.read_excel(PLANILHA)
    chamado = df[df['ID'] == id].to_dict(orient='records')[0]
    return render_template('concluir_chamado.html', chamado=chamado, now=datetime.now())


@app.route('/salvar_conclusao', methods=['POST'])
def salvar_conclusao():
    id = int(request.form.get('id'))
    solucao = request.form.get('solucao')

    df = pd.read_excel(PLANILHA)
    df.loc[df['ID'] == id, 'Status'] = 'Concluído'
    df.loc[df['ID'] == id, 'Solução'] = solucao
    df.to_excel(PLANILHA, index=False)
    flash('Chamado concluído com sucesso!', 'success')
    return redirect(url_for('index'))


@app.route('/editar/<int:id>')
def editar_chamado(id):
    df = pd.read_excel(PLANILHA)
    chamado = df[df['ID'] == id].to_dict(orient='records')[0]
    return render_template('editar_chamado.html', chamado=chamado, now=datetime.now())


@app.route('/atualizar', methods=['POST'])
def atualizar_chamado():
    id = int(request.form.get('id'))
    dados = {
        'Cidade': request.form.get('cidade'),
        'UF': request.form.get('uf'),
        'Site': request.form.get('site'),
        'Cell': request.form.get('cell'),
        'Tecnologia': request.form.get('tecnologia'),
        'Tipo': request.form.get('tipo'),
        'Alteração': request.form.get('alteracao'),
        'Data Aplicação Início': request.form.get('aplicacao_inicio'),
        'Data Aplicação Fim': request.form.get('aplicacao_fim'),
        'Antes': request.form.get('antes'),
        'Depois': request.form.get('depois'),
        'Status': request.form.get('status'),
        'OBS': request.form.get('obs'),
        'Descrição': request.form.get('descricao'),
        'Material de Apoio': request.form.get('material'),
        'Responsável': request.form.get('responsavel'),
        'Data de Abertura': pd.to_datetime(request.form.get('aplicacao_inicio'), errors='coerce').strftime('%Y-%m-%d %H:%M:%S')
        if request.form.get('aplicacao_inicio') else datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    }

    df = pd.read_excel(PLANILHA)
    df.loc[df['ID'] == id, list(dados.keys())] = list(dados.values())
    df.to_excel(PLANILHA, index=False)
    flash('Chamado atualizado com sucesso!', 'success')
    return redirect(url_for('index'))


@app.route('/excluir/<int:id>')
def excluir_chamado(id):
    df = pd.read_excel(PLANILHA)
    df = df[df['ID'] != id]

    # Reatribui os IDs em ordem sequencial
    df = df.sort_values(by='Data de Abertura')
    df['ID'] = range(1, len(df) + 1)

    df.to_excel(PLANILHA, index=False)
    flash('Chamado excluído e IDs resequenciados com sucesso!', 'success')
    return redirect(url_for('alertas_diarios'))

    # Reatribui os IDs em ordem sequencial
    df = df.sort_values(by='Data de Abertura')
    df['ID'] = range(1, len(df) + 1)

    df.to_excel(PLANILHA, index=False)
    return jsonify({'success': True, 'message': 'Chamado excluído e IDs resequenciados com sucesso!'})


@app.route('/exportar')
def exportar_excel():
    df = pd.read_excel(PLANILHA)
    export_path = 'export_chamados.xlsx'
    df.to_excel(export_path, index=False)
    return send_file(export_path, as_attachment=True)


@app.route('/alertas')
def alertas_diarios():
    try:
        df = pd.read_excel(PLANILHA)
        # Filtra chamados onde OBS é exatamente "Alarme"
        df = df[df['OBS'] == 'Alarme']
    except Exception as e:
        df = pd.DataFrame()
        print(f"Erro ao carregar alertas: {e}")

    return render_template('alertas.html', chamados=df.to_dict(orient='records'), now=datetime.now())


@app.route('/dashboard')
def dashboard():
    try:
        df = pd.read_excel(PLANILHA)
    except Exception as e:
        df = pd.DataFrame()
        print(f"Erro ao carregar planilha: {e}")

    cidade_filtro = request.args.get('cidade', '').strip()
    site_filtro = request.args.get('site', '').strip()
    responsavel_filtro = request.args.get('responsavel', '').strip()
    data_inicial_filtro = request.args.get('data_inicial', '')
    data_final_filtro = request.args.get('data_final', '')
    status_filtro = request.args.get('status', '').strip()
    tipo_filtro = request.args.get('tipo', '').strip()  # Novo filtro para Tipo

    if cidade_filtro:
        df = df[df['Cidade'].str.lower() == cidade_filtro.lower()]
    if site_filtro:
        df = df[df['Site'].str.lower() == site_filtro.lower()]
    if responsavel_filtro:
        df = df[df['Responsável'].str.lower() == responsavel_filtro.lower()]
    if data_inicial_filtro:
        data_inicial = datetime.strptime(data_inicial_filtro, '%Y-%m-%d').date()
        df = df[pd.to_datetime(df['Data de Abertura']).dt.date >= data_inicial]
    if data_final_filtro:
        data_final = datetime.strptime(data_final_filtro, '%Y-%m-%d').date()
        df = df[pd.to_datetime(df['Data de Abertura']).dt.date <= data_final]
    if status_filtro:
        df = df[df['Status'].str.lower() == status_filtro.lower()]
    if tipo_filtro:  # Aplicar filtro de Tipo
        df = df[df['Tipo'].str.lower() == tipo_filtro.lower()]

    total_chamados = len(df)
    chamados_por_status = df['Status'].value_counts().to_dict()
    chamados_por_responsavel = df['Responsável'].value_counts().to_dict()
    chamados_por_tecnologia = df['Tecnologia'].value_counts().to_dict()
    chamados_por_cidade = df['Cidade'].value_counts().to_dict()
    chamados_por_site = df['Site'].value_counts().to_dict()
    chamados_por_estado = df['UF'].value_counts().to_dict()

    cidades_geo = []
    for cidade, qtd in chamados_por_cidade.items():
        try:
            uf = df[df['Cidade'] == cidade]['UF'].mode().values[0]
            if isinstance(uf, str):
                lat, lng = get_coords(cidade, uf)
                if lat and lng:
                    df_cidade = df[df['Cidade'] == cidade]
                    status_counts = df_cidade['Status'].value_counts().to_dict()
                    responsaveis = df_cidade['Responsável'].unique().tolist()  # Pegar lista de responsáveis únicos
                    tecnologias = df_cidade['Tecnologia'].unique().tolist()
                    tipos_chamados = df_cidade['Tipo'].unique().tolist()
                    # Encontrar o status mais frequente para a cidade
                    status_mais_frequente = df_cidade['Status'].mode().values[0] if not df_cidade['Status'].empty else 'N/A'

                    cidades_geo.append({
                        'nome': cidade,
                        'qtd': qtd,
                        'lat': lat,
                        'lng': lng,
                        'status_counts': status_counts,  # Usar counts, não o modo
                        'tecnologias': tecnologias,
                        'tipos_chamados': tipos_chamados,
                        'responsaveis': responsaveis,  # Incluir a lista de responsáveis
                        'status': status_mais_frequente  # Adicionar o status mais frequente
                    })
        except Exception as e:
            print(f"Erro ao processar a cidade {cidade}: {e}")
            continue

    cidades_unicas = sorted(df['Cidade'].dropna().unique())
    sites_unicos = sorted(df['Site'].dropna().unique())
    responsaveis_unicos = sorted(df['Responsável'].dropna().unique())
    status_unicos = sorted(df['Status'].dropna().unique())
    tipos_unicos = sorted(df['Tipo'].dropna().unique())  # Tipos únicos

    df['Data de Abertura'] = pd.to_datetime(df['Data de Abertura'], errors='coerce')
    chamados_por_dia = df.groupby(df['Data de Abertura'].dt.date).size()
    chamados_por_dia = {str(k): v for k, v in chamados_por_dia.items()}
    chamados_por_semana = df.groupby(df['Data de Abertura'].dt.isocalendar().week).size()
    chamados_por_semana = {str(k): v for k, v in chamados_por_semana.items()}

    ontem = datetime.now().date() - timedelta(days=1)
    chamados_ontem = chamados_por_dia.get(str(ontem), 0)

    chamados_recentes = df.nlargest(10, 'Data de Abertura').to_dict(orient='records')

    return render_template(
        'dashboard.html',
        total=total_chamados,
        por_status=chamados_por_status,
        por_responsavel=chamados_por_responsavel,
        por_tecnologia=chamados_por_tecnologia,
        por_cidade=chamados_por_cidade,
        por_site=chamados_por_site,
        por_estado=chamados_por_estado,
        cidades_geo=cidades_geo,
        cidades_unicas=cidades_unicas,
        sites_unicos=sites_unicos,
        responsaveis_unicos=responsaveis_unicos,
        status_unicos=status_unicos,
        tipos_unicos=tipos_unicos,  # Passar tipos únicos para o template
        now=datetime.now(),
        chamados_ontem=chamados_ontem,
        chamados_por_dia=chamados_por_dia,
        chamados_por_semana=chamados_por_semana,
        chamados_recentes=chamados_recentes
        
    )
    
from flask import jsonify
from fuzzywuzzy import process

@app.route('/chatbot')
def chatbot():
    pergunta = request.args.get('pergunta', '').strip().lower()

    try:
        df = pd.read_excel(PLANILHA)
    except FileNotFoundError:
        return jsonify({'resposta': '⚠️ Arquivo não encontrado. Verifique se a planilha está acessível.'})
    except Exception as e:
        return jsonify({'resposta': f'⚠️ Erro ao acessar os dados dos chamados: {str(e)}'})

    if not pergunta:
        return jsonify({'resposta': '🤖 Olá! Digite o nome de uma cidade ou responsável para começar. Caso queira ajuda, posso sugerir algumas opções!'})

    # Saudações
    saudacoes = ['oi', 'olá', 'salve', 'e aí', 'bom dia', 'boa tarde', 'boa noite']
    respostas_saudacoes = [
        '🤖 Olá! Como posso ajudar hoje?',
        '🤖 E aí, qual a boa?',
        '🤖 Saudações! Em que posso ser útil?'
    ]
    if any(s in pergunta for s in saudacoes):
        return jsonify({'resposta': random.choice(respostas_saudacoes)})

    # Sugestão se mencionar "aberto"
    if 'aberto' in pergunta and len(pergunta.split()) == 1:
        return jsonify({'resposta': '🔍 Você pode me informar a cidade ou o responsável para que eu buscar os chamados abertos?'})

    # Preparar dados
    df['Cidade'] = df['Cidade'].fillna('').str.strip().str.lower()
    df['Status'] = df['Status'].fillna('').str.strip().str.lower()
    df['Site'] = df['Site'].fillna('').str.strip()
    df['Responsável'] = df['Responsável'].fillna('').str.strip().str.lower()
    df['OBS'] = df['OBS'].fillna('').str.strip().str.lower()
    df['Data Aplicação Início'] = pd.to_datetime(df['Data Aplicação Início'], errors='coerce')

    cidades_unicas = df['Cidade'].unique()
    responsaveis_unicos = df['Responsável'].unique()

    # Fuzzy matching
    cidade_encontrada, cidade_score = process.extractOne(pergunta, cidades_unicas) if cidades_unicas.any() else (None, 0)
    responsavel_encontrado, responsavel_score = process.extractOne(pergunta, responsaveis_unicos) if responsaveis_unicos.any() else (None, 0)

    if cidade_score >= 80:
        df_cidade = df[df['Cidade'] == cidade_encontrada]
        total = len(df_cidade)
        abertos = df_cidade[df_cidade['Status'] == 'aberto']
        andamento = df_cidade[df_cidade['Status'] == 'em andamento']
        concluidos = df_cidade[df_cidade['Status'] == 'concluído']

        sites_abertos = abertos['Site'].dropna().unique().tolist()
        sites_andamento = andamento['Site'].dropna().unique().tolist()
        sites_com_chamados = set(sites_abertos + sites_andamento)
        sites_texto = "\n📍 " + "\n📍 ".join(sites_com_chamados) if sites_com_chamados else "Nenhum site com chamados abertos ou em andamento."

        ultima_data = df_cidade['Data Aplicação Início'].max()
        ultima_str = ultima_data.strftime('%d/%m/%Y') if pd.notnull(ultima_data) else "não disponível"

        resposta = (
            f"📊 <b>{cidade_encontrada.title()}</b> possui <b>{total}</b> chamados:\n\n"
            f"🟡 Abertos: <b>{len(abertos)}</b>\n"
            f"🔄 Em andamento: <b>{len(andamento)}</b>\n"
            f"✅ Concluídos: <b>{len(concluidos)}</b>\n\n"
            f"📅 Última atualização: <b>{ultima_str}</b>\n\n"
            f"📌 <u>Sites com chamados abertos ou em andamento:</u>\n{sites_texto}"
        )

        # Alertas
        alertas_cidade = df_cidade[df_cidade['OBS'] == 'Alarme']
        total_alertas = len(alertas_cidade)
        sites_alertas = alertas_cidade['Site'].dropna().unique().tolist()
        sites_alertas_texto = "\n🚨 " + "\n🚨 ".join(sites_alertas) if sites_alertas else "Nenhum site com alertas."

        if total_alertas > 0:
            resposta += (
                f"\n\n⚠️ <b>Alertas em {cidade_encontrada.title()}</b>: {total_alertas} chamados de alerta.\n"
                f"📌 <u>Sites com alertas:</u>\n{sites_alertas_texto}"
            )

    elif responsavel_score >= 80:
        df_resp = df[df['Responsável'] == responsavel_encontrado]
        total = len(df_resp)
        abertos = len(df_resp[df_resp['Status'] == 'aberto'])
        andamento = len(df_resp[df_resp['Status'] == 'em andamento'])
        concluidos = len(df_resp[df_resp['Status'] == 'concluído'])

        ultima_data = df_resp['Data Aplicação Início'].max()
        ultima_str = ultima_data.strftime('%d/%m/%Y') if pd.notnull(ultima_data) else "não disponível"

        resposta = (
            f"🧑‍🔧 <b>{responsavel_encontrado.title()}</b> é responsável por <b>{total}</b> chamados:\n\n"
            f"🟡 Abertos: <b>{abertos}</b>\n"
            f"🔄 Em andamento: <b>{andamento}</b>\n"
            f"✅ Concluídos: <b>{concluidos}</b>\n\n"
            f"📅 Última atualização: <b>{ultima_str}</b>"
        )

    else:
        exemplo_cidade = random.choice([c for c in df['Cidade'].unique() if c])
        exemplo_resp = random.choice([r for r in df['Responsável'].unique() if r])
        resposta = (
            "❓ Não entendi sua pergunta.\n"
            "Tente algo como:\n"
            f"🔹 Chamados abertos em <b>{exemplo_cidade.title()}</b>\n"
            f"🔹 Status dos chamados do responsável <b>{exemplo_resp.title()}</b>"
        )

    return jsonify({'resposta': resposta})


 


@app.route('/blacklist')
def blacklist():
    df_blacklist = ler_blacklist()
    itens_blacklist = df_blacklist.to_dict(orient='records')
    return render_template('blacklist.html', itens_blacklist=itens_blacklist, now=datetime.now())


@app.route('/blacklist/novo')
def novo_item_blacklist():
    return render_template('novo_item_blacklist.html', now=datetime.now())


@app.route('/blacklist/criar', methods=['POST'])
def criar_item_blacklist():
    df_blacklist = ler_blacklist()
    dados = {
        'Cidade': request.form.get('cidade'),
        'UF': request.form.get('uf'),
        'Site': request.form.get('site'),
        'Cell': request.form.get('cell'),
        'Tecnologia': request.form.get('tecnologia'),
        'Tipo': request.form.get('tipo'),
        'Alteração': request.form.get('alteracao'),
        'Data Aplicação Início': request.form.get('aplicacao_inicio'),
        'Data Aplicação Fim': request.form.get('aplicacao_fim'),
        'Antes': request.form.get('antes'),
        'Depois': request.form.get('depois'),
        'Status': request.form.get('status'),
        'OBS': request.form.get('obs'),
        'Descrição': request.form.get('descricao'),
        'Material de Apoio': request.form.get('material'),
        'Responsável': request.form.get('responsavel'),
        'Data de Abertura': pd.to_datetime(request.form.get('aplicacao_inicio'), errors='coerce').strftime('%Y-%m-%d %H:%M:%S')
        if request.form.get('aplicacao_inicio') else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    novo_id = 1 if df_blacklist.empty else df_blacklist['ID'].max() + 1
    dados['ID'] = novo_id
    df_blacklist = pd.concat([df_blacklist, pd.DataFrame([dados])], ignore_index=True)
    if salvar_blacklist(df_blacklist):
        flash('Item adicionado à Blacklist com sucesso!', 'success')
    else:
        flash('Erro ao adicionar item à Blacklist.', 'danger')
    return redirect(url_for('blacklist'))


@app.route('/blacklist/editar/<int:id>')
def editar_item_blacklist(id):
    df_blacklist = ler_blacklist()
    item = df_blacklist[df_blacklist['ID'] == id].to_dict(orient='records')[0]
    return render_template('editar_item_blacklist.html', item=item, now=datetime.now())


@app.route('/blacklist/atualizar', methods=['POST'])
def atualizar_item_blacklist():
    id = int(request.form.get('id'))
    df_blacklist = ler_blacklist()
    if df_blacklist[df_blacklist['ID'] == id].empty:
        flash('Item não encontrado na Blacklist.', 'danger')
        return redirect(url_for('blacklist'))
    dados = {
        'Cidade': request.form.get('cidade'),
        'UF': request.form.get('uf'),
        'Site': request.form.get('site'),
        'Cell': request.form.get('cell'),
        'Tecnologia': request.form.get('tecnologia'),
        'Tipo': request.form.get('tipo'),
        'Alteração': request.form.get('alteracao'),
        'Data Aplicação Início': request.form.get('aplicacao_inicio'),
        'Data Aplicação Fim': request.form.get('aplicacao_fim'),
        'Antes': request.form.get('antes'),
        'Depois': request.form.get('depois'),
        'Status': request.form.get('status'),
        'OBS': request.form.get('obs'),
        'Descrição': request.form.get('descricao'),
        'Material de Apoio': request.form.get('material'),
        'Responsável': request.form.get('responsavel'),
        'Data de Abertura': pd.to_datetime(request.form.get('aplicacao_inicio'), errors='coerce').strftime('%Y-%m-%d %H:%M:%S')
        if request.form.get('aplicacao_inicio') else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    df_blacklist.loc[df_blacklist['ID'] == id, list(dados.keys())] = list(dados.values())
    if salvar_blacklist(df_blacklist):
        flash('Item atualizado na Blacklist com sucesso!', 'success')
    else:
        flash('Erro ao atualizar item na Blacklist.', 'danger')
    return redirect(url_for('blacklist'))


@app.route('/blacklist/excluir/<int:id>')
def excluir_item_blacklist(id):
    df_blacklist = ler_blacklist()
    if df_blacklist[df_blacklist['ID'] == id].empty:
        flash('Item não encontrado na Blacklist.', 'danger')
        return redirect(url_for('blacklist'))
    df_blacklist = df_blacklist[df_blacklist['ID'] != id]
    if salvar_blacklist(df_blacklist):
        flash('Item excluído da Blacklist com sucesso!', 'success')
    else:
        flash('Erro ao excluir item da Blacklist.', 'danger')
    return redirect(url_for('blacklist'))


if __name__ == '__main__':
    inicializar_planilha()
    inicializar_blacklist()  # Inicializar a planilha da blacklist também
    app.run(debug=True)