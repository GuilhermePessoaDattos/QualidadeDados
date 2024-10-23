import pandas as pd
import re
import streamlit as st

# Definir colunas sigilosas de acordo com a LGPD
COLUNAS_SIGILOSAS_PADRAO = ['cpf', 'email', 'telefone', 'endereco']

# Função para carregar o arquivo (CSV ou Excel)
def carregar_arquivo(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    elif file.name.endswith('.xlsx'):
        return pd.read_excel(file)
    else:
        raise ValueError("Formato de arquivo não suportado: deve ser CSV ou Excel (.xlsx)")

# Função para avaliar completude dos dados com o novo cálculo
def avaliar_completude(df, colunas_obrigatorias, colunas_importantes):
    total_colunas = len(colunas_obrigatorias) + len(colunas_importantes)
    if total_colunas == 0:
        return 25, "Nenhuma coluna foi selecionada para análise de completude. Score máximo atribuído: 25/25.\n"
    
    # Peso para cada coluna
    peso_por_coluna = 25 / total_colunas
    completude_score = 25
    explicacao = ""
    
    # Avaliar colunas obrigatórias
    for col in colunas_obrigatorias:
        if col not in df.columns:
            completude_score -= peso_por_coluna
            explicacao += f"A coluna obrigatória '{col}' está ausente.\n"
        else:
            # Verificar se há valores nulos ou em branco
            valores_validos = df[col].notna().mean()
            if valores_validos < 1.0:
                completude_score -= peso_por_coluna
                explicacao += f"A coluna obrigatória '{col}' tem valores nulos ou em branco.\n"

    # Avaliar colunas importantes com percentuais mínimos de completude
    for col, min_percent_preenchimento in colunas_importantes.items():
        if col not in df.columns:
            completude_score -= peso_por_coluna
            explicacao += f"A coluna importante '{col}' está ausente.\n"
        else:
            percent_filled = df[col].notna().mean()
            if percent_filled < min_percent_preenchimento:
                # Penalização proporcional à diferença entre o preenchimento atual e o mínimo
                penalizacao_proporcional = (min_percent_preenchimento - percent_filled) * peso_por_coluna
                completude_score -= penalizacao_proporcional
                explicacao += f"A coluna importante '{col}' tem {percent_filled*100:.2f}% de preenchimento, abaixo do mínimo de {min_percent_preenchimento*100}%.\n"
    
    explicacao += f"Score final de completude: {completude_score}/25 (Peso: 25%).\n"
    return max(0, completude_score), explicacao

# Função para avaliar consistência de formato com verificação completa de cada coluna
def avaliar_consistencia(df, formatos_colunas):
    total_colunas = len(formatos_colunas)
    if total_colunas == 0:
        return 25, "Nenhuma coluna foi selecionada para análise de consistência. Score máximo atribuído: 25/25.\n"
    
    # Peso para cada coluna
    peso_por_coluna = 25 / total_colunas
    consistencia_score = 25
    explicacao = ""

    for col, formato in formatos_colunas.items():
        if col in df.columns:
            if formato == 'data':
                # Verificar se todos os valores seguem os formatos de data permitidos
                inconsistentes = df[col].dropna().apply(lambda x: not re.match(r'^\d{2}/\d{2}/\d{4}$|^\d{4}-\d{2}-\d{2}$|^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', str(x))).sum()
                if inconsistentes > 0:
                    consistencia_score -= peso_por_coluna
                    explicacao += f"A coluna '{col}' foi analisada como 'data', mas contém {inconsistentes} valores fora do formato permitido (dd/mm/yyyy, yyyy-mm-dd, yyyy-mm-dd hh:mi:ss).\n"
                else:
                    explicacao += f"A coluna '{col}' foi analisada como 'data' e todos os valores estão no formato correto.\n"
            elif formato == 'monetario':
                # Verificar o formato de valores monetários (XX.XX)
                inconsistentes = df[col].dropna().apply(lambda x: not re.match(r'^\d+\.\d{2}$', str(x))).sum()
                if inconsistentes > 0:
                    consistencia_score -= peso_por_coluna
                    explicacao += f"A coluna '{col}' foi analisada como 'monetário', mas contém {inconsistentes} valores fora do formato esperado (XX.XX).\n"
                else:
                    explicacao += f"A coluna '{col}' foi analisada como 'monetário' e todos os valores estão no formato correto.\n"
            elif formato == 'inteiro':
                # Verificar se são todos números inteiros
                inconsistentes = df[col].dropna().apply(lambda x: not isinstance(x, int)).sum()
                if inconsistentes > 0:
                    consistencia_score -= peso_por_coluna
                    explicacao += f"A coluna '{col}' foi analisada como 'inteiro', mas contém {inconsistentes} valores que não são inteiros.\n"
                else:
                    explicacao += f"A coluna '{col}' foi analisada como 'inteiro' e todos os valores são inteiros.\n"
            elif formato == 'decimal':
                # Verificar se são todos números decimais
                inconsistentes = df[col].dropna().apply(lambda x: not isinstance(x, float)).sum()
                if inconsistentes > 0:
                    consistencia_score -= peso_por_coluna
                    explicacao += f"A coluna '{col}' foi analisada como 'decimal', mas contém {inconsistentes} valores que não são decimais.\n"
                else:
                    explicacao += f"A coluna '{col}' foi analisada como 'decimal' e todos os valores são decimais.\n"
            elif formato == 'texto':
                # Para texto, qualquer valor é considerado válido
                explicacao += f"A coluna '{col}' foi analisada como 'texto' e todos os valores são considerados válidos.\n"

    explicacao += f"Score final de consistência: {consistencia_score}/25 (Peso: 25%).\n"
    return max(0, consistencia_score), explicacao

# Função para avaliar valores permitidos em colunas específicas com novo critério
def avaliar_valores_permitidos(df, colunas_valores_permitidos):
    # Se nenhuma coluna for selecionada, o score deve ser 25/25
    if len(colunas_valores_permitidos) == 0:
        return 25, "Nenhuma coluna foi selecionada para valores permitidos. Score máximo atribuído: 25/25 (Peso: 25%).\n"
    
    total_colunas = len(colunas_valores_permitidos)
    peso_por_coluna = 25 / total_colunas
    valores_score = 25
    explicacao = ""

    # Avaliar cada coluna com valores permitidos
    for col, valores in colunas_valores_permitidos.items():
        valores_permitidos = [v.strip() for v in valores.split(",")]
        if col in df.columns:
            total_linhas = len(df[col].dropna())
            valores_invalidos = df[col].dropna().apply(lambda x: x not in valores_permitidos).sum()
            if valores_invalidos > 0:
                penalizacao_proporcional = (valores_invalidos / total_linhas) * peso_por_coluna
                valores_score -= penalizacao_proporcional
                explicacao += f"A coluna '{col}' contém {valores_invalidos} valores fora dos permitidos ({valores_permitidos}).\n"
            else:
                explicacao += f"A coluna '{col}' contém todos os valores dentro dos permitidos ({valores_permitidos}).\n"
    
    explicacao += f"Score final de valores permitidos: {valores_score}/25 (Peso: 25%).\n"
    return max(0, valores_score), explicacao

# Função para identificar dados sigilosos com score máximo de 10
def identificar_dados_sigilosos(df, colunas_sigilosas):
    sigilosos_score = 10
    explicacao = ""
    colunas_com_dados_sigilosos = []

    for col in df.columns:
        # Se a coluna tiver um nome ou padrão que remeta a dados sigilosos, decrementar o score
        if any(sig in col.lower() for sig in colunas_sigilosas):
            sigilosos_score -= 2  # Penalização de 2 pontos por coluna sensível
            colunas_com_dados_sigilosos.append(col)
    
    if colunas_com_dados_sigilosos:
        explicacao += f"As seguintes colunas contêm dados pessoais sensíveis (LGPD): {', '.join(colunas_com_dados_sigilosos)}.\n"
    
    explicacao += f"Score final de dados sigilosos: {sigilosos_score}/10 (Peso: 10%).\n"
    return max(0, sigilosos_score), explicacao

# Função para avaliar padronização (manipulação manual)
def avaliar_padronizacao(manipulacao_manual):
    if manipulacao_manual:
        return 0, "Os dados foram manipulados manualmente. Score de padronização: 0/5 (Peso: 5%).\n"
    return 5, "Os dados não foram manipulados manualmente. Score de padronização: 5/5 (Peso: 5%).\n"

# Função para avaliar controle de acesso (manipulação sem rastreio)
def avaliar_controle_acesso(acesso_sem_rastreio):
    if acesso_sem_rastreio:
        return 0, "Os dados podem ser manipulados sem rastreio. Score de controle de acesso: 0/10 (Peso: 10%).\n"
    return 10, "Os dados não podem ser manipulados sem rastreio. Score de controle de acesso: 10/10 (Peso: 10%).\n"

# Função principal para calcular o score total de qualidade de dados com pesos
def calcular_score_qualidade(df, colunas_obrigatorias, colunas_importantes, formatos_colunas, colunas_valores_permitidos, manipulacao_manual, acesso_sem_rastreio):
    completude_score, completude_explicacao = avaliar_completude(df, colunas_obrigatorias, colunas_importantes)
    consistencia_score, consistencia_explicacao = avaliar_consistencia(df, formatos_colunas)
    valores_score, valores_explicacao = avaliar_valores_permitidos(df, colunas_valores_permitidos)
    sigilosos_score, sigilosos_explicacao = identificar_dados_sigilosos(df, COLUNAS_SIGILOSAS_PADRAO)
    padronizacao_score, padronizacao_explicacao = avaliar_padronizacao(manipulacao_manual)
    controle_acesso_score, controle_acesso_explicacao = avaliar_controle_acesso(acesso_sem_rastreio)

    # Apresentação dos scores detalhados
    st.write("### Score de cada critério de qualidade:")
    st.write(f"**Completude:** {completude_score}/25 (Peso: 25%)")
    st.write(f"**Consistência:** {consistencia_score}/25 (Peso: 25%)")
    st.write(f"**Valores Permitidos:** {valores_score}/25 (Peso: 25%)")
    st.write(f"**Dados Sigilosos:** {sigilosos_score}/10 (Peso: 10%)")
    st.write(f"**Padronização:** {padronizacao_score}/5 (Peso: 5%)")
    st.write(f"**Controle de Acesso:** {controle_acesso_score}/10 (Peso: 10%)")

    # Soma dos scores diretamente
    score_final = completude_score + consistencia_score + valores_score + sigilosos_score + padronizacao_score + controle_acesso_score

    explicacoes = (
        "### Completude:\n" + completude_explicacao +
        "### Consistência:\n" + consistencia_explicacao +
        "### Valores Permitidos:\n" + valores_explicacao +
        "### Dados Sigilosos:\n" + sigilosos_explicacao +
        "### Padronização:\n" + padronizacao_explicacao +
        "### Controle de Acesso:\n" + controle_acesso_explicacao
    )
    return round(score_final, 2), explicacoes

# Configuração da interface Streamlit
st.title("Avaliação de Qualidade de Dados")

# Upload do arquivo
uploaded_file = st.file_uploader("Upload do arquivo (CSV ou Excel)", type=['csv', 'xlsx'])

# Após upload do arquivo, exibir as colunas
if uploaded_file:
    df = carregar_arquivo(uploaded_file)
    
    st.write("### Colunas do Arquivo:")
    st.write(df.columns.tolist())

    # Perguntar ao usuário quais são as colunas obrigatórias
    colunas_obrigatorias = st.multiselect("Selecione as colunas obrigatórias", df.columns.tolist())

    # Perguntar ao usuário quais colunas são importantes e os percentuais de preenchimento mínimo
    colunas_importantes = {}
    colunas_importantes_selecionadas = st.multiselect("Selecione as colunas importantes", df.columns.tolist())
    for col in colunas_importantes_selecionadas:
        percentual = st.slider(f"Percentual mínimo de preenchimento para a coluna '{col}'", 0.0, 1.0, 0.9)
        colunas_importantes[col] = percentual

    # Combinar colunas obrigatórias e importantes para verificar formato
    colunas_para_analise = colunas_obrigatorias + list(colunas_importantes.keys())
    formatos_colunas = {}
    for col in colunas_para_analise:
        formato = st.selectbox(f"Formato esperado da coluna '{col}'", ['data', 'monetario', 'texto', 'inteiro', 'decimal'], key=f"{col}_formato")
        formatos_colunas[col] = formato

    # Perguntar ao usuário sobre colunas com valores permitidos
    colunas_valores_permitidos = {}
    colunas_valores = st.multiselect("Selecione as colunas com valores pré-definidos", colunas_para_analise)
    for col in colunas_valores:
        valores_permitidos = st.text_input(f"Informe os valores permitidos para a coluna '{col}' separados por vírgula", key=f"{col}_valores")
        colunas_valores_permitidos[col] = valores_permitidos

    # Perguntar ao usuário sobre padronização (manipulação manual dos dados)
    manipulacao_manual = st.radio("Os dados foram manipulados manualmente?", ['Sim', 'Não']) == 'Sim'

    # Perguntar ao usuário sobre controle de acesso (dados podem ser manipulados sem rastreio)
    acesso_sem_rastreio = st.radio("Os dados podem ser manipulados sem rastreio?", ['Sim', 'Não']) == 'Sim'

    if st.button("Calcular Score"):
        score, explicacoes = calcular_score_qualidade(df, colunas_obrigatorias, colunas_importantes, formatos_colunas, colunas_valores_permitidos, manipulacao_manual, acesso_sem_rastreio)
        st.write(f"### Score de Qualidade de Dados: {score}/100")
        st.write(explicacoes)
