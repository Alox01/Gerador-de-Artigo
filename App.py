from flask import Flask, request, send_from_directory, render_template, make_response
import os
import google.generativeai as genai
import re
from servico_banco import salvar_trabalho
from servico_banco import listar_trabalhos
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from docx.shared import Cm
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
modelo = genai.GenerativeModel(model_name="gemini-2.0-flash")

OUTPUT_DIR = "output_files"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def formatar_titulo(titulo):
    return titulo.title()

def formatar_autor(nome):
    partes = nome.strip().split()
    if len(partes) < 2:
        return nome  
    sobrenome = partes[-1].upper()
    nome = " ".join(partes[:-1])
    return f"{sobrenome}, {nome}"

def remover_asteriscos(texto):
    return re.sub(r"\*+", "", texto)

def gerar_artigo_abnt(titulo, tema, autor):
    titulo = formatar_titulo(titulo)

    prompt = f"""
    Gere um artigo acadêmico completo e bem estruturado sobre **"{tema}"** com o título **"{titulo}"**, seguindo rigorosamente as normas da ABNT. O artigo deve conter as seguintes seções obrigatórias, com seus respectivos conteúdos e tamanhos mínimos:

    **1. Título**
    - Deve aparecer centralizado no início.

    **2. Resumo (em português)**
    - Um parágrafo entre 150 a 250 palavras que sintetize os principais pontos do artigo.
    
    **3. Palavras-chave (em português)**
    - De 3 a 5 palavras separadas por ponto e vírgula (;).

    **4. Abstract (em inglês)**
    - Um parágrafo com a tradução do resumo, entre 150 a 250 palavras.
    - Sintetize os principais pontos do artigo em inglês.
    
    **5. Keywords (em inglês)**
    - Tradução das palavras-chave, entre 3 e 5 termos separados por ponto e vírgula (;).

    **6. Introdução**
    - Apresente o tema, justificativa, problema e objetivo da pesquisa.
    - Mínimo de 200 palavras.

    **7. Revisão de Literatura**
    - Discorra sobre conceitos teóricos importantes sobre o tema.
    - Utilize ao menos 2 citações no estilo ABNT: (SOBRENOME, ano, p.xx).
    - Mínimo de 300 palavras.

    **8. Metodologia**
    - Descreva os métodos e procedimentos adotados para desenvolver o trabalho.
    - Pode incluir abordagem qualitativa/quantitativa, revisão bibliográfica, etc.
    - Mínimo de 200 palavras.

    **9. Resultados e Discussão**
    - Apresente os principais resultados esperados ou obtidos.
    - Relacione com a literatura citada.
    - Mínimo de 300 palavras.

    **10. Conclusão**
    - Retome os objetivos, destaque as contribuições e proponha trabalhos futuros.
    - Mínimo de 150 palavras.

    **11. Referências**
    - Liste pelo menos **3 referências no formato ABNT.**
    - Exemplo: SOBRENOME, Nome. *Título do Livro ou Artigo*. Local: Editora, Ano.
    """
    resposta = modelo.generate_content(prompt)
    return resposta.text

def salvar_em_pdf(titulo, texto, autor):
    nome_arquivo = os.path.join(OUTPUT_DIR, titulo.replace(" ", "_") + ".pdf")
    doc = SimpleDocTemplate(nome_arquivo, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Titulo', fontSize=16, spaceAfter=12, alignment=1))
    styles.add(ParagraphStyle(name='Secao', fontSize=14, spaceAfter=8, spaceBefore=12, leading=18, alignment=0, firstLineIndent=0, leftIndent=0))
    styles.add(ParagraphStyle(name='Texto', fontSize=12, leading=18, alignment=TA_JUSTIFY, firstLineIndent=1.25 * cm, spaceAfter=10))
    styles.add(ParagraphStyle(name='TextoSemRecuo', fontSize=12, leading=18, alignment=TA_JUSTIFY, firstLineIndent=0, spaceAfter=10))

    elementos = []
    from reportlab.platypus import KeepTogether

    autor_formatado = formatar_autor(autor)
    autor_sem_quebra = autor_formatado.replace(" ", "\u00A0")
    autor_para_pdf = Paragraph(autor_sem_quebra, ParagraphStyle(
        'AutorDireita',
        parent=styles['TextoSemRecuo'],
        alignment=2,
        spaceAfter=12,
    ))

    elementos.append(autor_para_pdf)
    elementos.append(Spacer(1, 1.2 * cm))
    titulo_upper = titulo.upper()
    elementos.append(Paragraph(titulo_upper, styles['Titulo']))
    elementos.append(Spacer(1, 0.6*cm))

    padroes = {
    "Resumo": re.compile(r"^\s*\d{0,2}\.?\s*resumo\s*:?\s*(.*)$", re.IGNORECASE),
    "Palavras-chave": re.compile(r"^\s*\d{0,2}\.?\s*palavras-chave\s*:?\s*(.*)$", re.IGNORECASE),
    "Abstract": re.compile(r"^\s*\d{0,2}\.?\s*abstract\s*:?\s*(.*)$", re.IGNORECASE),
    "Keywords": re.compile(r"^\s*\d{0,2}\.?\s*keywords\s*:?\s*(.*)$", re.IGNORECASE),
    "Introdução": re.compile(r"^\s*\d{0,2}\.?\s*introdução\s*:?\s*(.*)$", re.IGNORECASE),
    "Revisão de Literatura": re.compile(r"^\s*\d{0,2}\.?\s*revis[aã]o de literatura\s*:?\s*(.*)$", re.IGNORECASE),
    "Metodologia": re.compile(r"^\s*\d{0,2}\.?\s*metodologia\s*:?\s*(.*)$", re.IGNORECASE),
    "Resultados e Discussão": re.compile(r"^\s*\d{0,2}\.?\s*resultados e discussão\s*:?\s*(.*)$", re.IGNORECASE),
    "Conclusão": re.compile(r"^\s*\d{0,2}\.?\s*conclus[aã]o\s*:?\s*(.*)$", re.IGNORECASE),
    "Referências": re.compile(r"^\s*\d{0,2}\.?\s*refer[eê]ncias\s*:?\s*(.*)$", re.IGNORECASE)
    }

    conteudo = {}
    atual = None
    aguardando_conteudo_direto = False
    ultima_secao = None

    for linha in texto.splitlines():
        linha_limpa = remover_asteriscos(linha.strip())
        if not linha_limpa:
            continue

        mudou_secao = False
        for nome_secao, padrao in padroes.items():
            match = padrao.match(linha_limpa)
            if match:
                atual = nome_secao
                if atual not in conteudo:
                    conteudo[atual] = []

                inline = match.group(1).strip()
                if inline:
                    conteudo[atual].append(inline)
                    aguardando_conteudo_direto = False
                else:
                    aguardando_conteudo_direto = True
                    ultima_secao = atual

                mudou_secao = True
                break

        if not mudou_secao:
            if aguardando_conteudo_direto and ultima_secao:
                if ultima_secao not in conteudo:
                    conteudo[ultima_secao] = []
                conteudo[ultima_secao].append(linha_limpa)
                continue
            if atual:
                if atual not in conteudo:
                    conteudo[atual] = []
                conteudo[atual].append(linha_limpa)

    for secao in ["Resumo", "Palavras-chave", "Abstract", "Keywords", "Introdução", "Revisão de Literatura", "Metodologia", "Resultados e Discussão", "Conclusão", "Referências"]:
        elementos.append(Paragraph(secao.upper(), styles['Secao']))
        if secao in conteudo and conteudo[secao]:
            for paragrafo in conteudo[secao]:
                estilo = styles['TextoSemRecuo'] if secao in ["Resumo", "Palavras-chave", "Abstract", "Keywords", "Introdução", "Conclusão", "Referências"] else styles['Texto']
                elementos.append(Paragraph(paragrafo, estilo))
                elementos.append(Spacer(1, 0.4 * cm))
        else:
            elementos.append(Paragraph("Conteúdo não disponível.", styles['Texto']))

    doc.build(elementos)
    return nome_arquivo 

def salvar_em_docx(titulo, texto, autor):
    doc = Document()
    
    doc.add_paragraph("")
    doc.add_paragraph("")
    par_autor = doc.add_paragraph(formatar_autor(autor))
    par_autor.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    par_autor.paragraph_format.space_after = Pt(20)
    run_autor = par_autor.runs[0]
    run_autor.font.name = "Times New Roman"
    run_autor.font.size = Pt(12)
    run_autor.font.color.rgb = RGBColor(0, 0, 0)

    titulo_paragrafo = doc.add_paragraph()
    titulo_paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_titulo = titulo_paragrafo.add_run(titulo.upper())
    run_titulo.font.name = "Times New Roman"
    run_titulo.font.size = Pt(16)
    run_titulo.bold = True

    padroes = {
    "Resumo": re.compile(r"^\s*\d{0,2}\.?\s*resumo\s*:?\s*(.*)$", re.IGNORECASE),
    "Palavras-chave": re.compile(r"^\s*\d{0,2}\.?\s*palavras-chave\s*:?\s*(.*)$", re.IGNORECASE),
    "Abstract": re.compile(r"^\s*\d{0,2}\.?\s*abstract\s*:?\s*(.*)$", re.IGNORECASE),
    "Keywords": re.compile(r"^\s*\d{0,2}\.?\s*keywords\s*:?\s*(.*)$", re.IGNORECASE),
    "Introdução": re.compile(r"^\s*\d{0,2}\.?\s*introdução\s*:?\s*(.*)$", re.IGNORECASE),
    "Revisão de Literatura": re.compile(r"^\s*\d{0,2}\.?\s*revis[aã]o de literatura\s*:?\s*(.*)$", re.IGNORECASE),
    "Metodologia": re.compile(r"^\s*\d{0,2}\.?\s*metodologia\s*:?\s*(.*)$", re.IGNORECASE),
    "Resultados e Discussão": re.compile(r"^\s*\d{0,2}\.?\s*resultados e discussão\s*:?\s*(.*)$", re.IGNORECASE),
    "Conclusão": re.compile(r"^\s*\d{0,2}\.?\s*conclus[aã]o\s*:?\s*(.*)$", re.IGNORECASE),
    "Referências": re.compile(r"^\s*\d{0,2}\.?\s*refer[eê]ncias\s*:?\s*(.*)$", re.IGNORECASE)
    }

    conteudo = {}
    atual = None
    aguardando_conteudo_direto = False
    ultima_secao = None

    for linha in texto.splitlines():
        linha_limpa = remover_asteriscos(linha.strip())
        if not linha_limpa:
            continue

        mudou_secao = False
        for nome_secao, padrao in padroes.items():
            match = padrao.match(linha_limpa)
            if match:
                atual = nome_secao
                if atual not in conteudo:
                    conteudo[atual] = []

                inline = match.group(1).strip()
                if inline:
                    conteudo[atual].append(inline)
                    aguardando_conteudo_direto = False
                else:
                    aguardando_conteudo_direto = True
                    ultima_secao = atual

                mudou_secao = True
                break

        if not mudou_secao:
            if aguardando_conteudo_direto and ultima_secao:
                if ultima_secao not in conteudo:
                    conteudo[ultima_secao] = []
                conteudo[ultima_secao].append(linha_limpa)
                continue
            if atual:
                if atual not in conteudo:
                    conteudo[atual] = []
                conteudo[atual].append(linha_limpa)

    for secao in ["Resumo", "Palavras-chave", "Abstract", "Keywords", "Introdução", "Revisão de Literatura", "Metodologia", "Resultados e Discussão", "Conclusão", "Referências"]:
        heading = doc.add_heading(secao.upper(), level=2)
        heading.paragraph_format.space_after = Pt(10)
        if secao in conteudo and conteudo[secao]:
            for paragrafo in conteudo[secao]:
                p = doc.add_paragraph()
                run = p.add_run(paragrafo)
                run.font.name = "Times New Roman"
                run.font.size = Pt(12)
                run.font.color.rgb = RGBColor(0, 0, 0)
                
                if secao in ["Resumo", "Palavras-chave", "Abstract", "Keywords", "Introdução", "Conclusão", "Referências"]:
                    p.paragraph_format.first_line_indent = Cm(0)
                else:
                    p.paragraph_format.first_line_indent = Cm(1.25)

                p.paragraph_format.line_spacing = 1.5
                if secao != "Referências":
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    nome_arquivo = os.path.join(OUTPUT_DIR, titulo.replace(" ", "_") + ".docx")
    doc.save(nome_arquivo)
    return nome_arquivo

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/gerar_trabalho', methods=['POST'])
def gerar_trabalho():
    autor = request.form.get('autor')
    titulo = request.form.get('titulo')
    tema = request.form.get('tema')

    if not titulo or not tema:
        return "Erro: Título e Tema são obrigatórios", 400

    trabalho = gerar_artigo_abnt(titulo, tema, autor)

    salvar_trabalho(titulo, tema, autor, trabalho, pdf=True, docx=True)

    return render_template('download.html', titulo=titulo, autor=autor, preview=trabalho)

@app.route('/baixar_trabalho_editado', methods=['POST'])
def baixar_trabalho_editado():
    texto_editado = request.form.get('texto_editado')
    titulo = request.form.get('titulo')
    autor = request.form.get('autor')
    formato = request.form.get('formato')  # "pdf" ou "docx"

    if not texto_editado or not titulo or not autor or not formato:
        return "Dados incompletos para geração do arquivo.", 400

    if formato == 'pdf':
        caminho_arquivo = salvar_em_pdf(titulo, texto_editado, autor)
    elif formato == 'docx':
        caminho_arquivo = salvar_em_docx(titulo, texto_editado, autor)
    else:
        return "Formato inválido.", 400

    with open(caminho_arquivo, 'rb') as f:
        dados = f.read()

    nome_arquivo = os.path.basename(caminho_arquivo)
    response = make_response(dados)
    if formato == 'pdf':
        response.headers.set('Content-Type', 'application/pdf')
    else:
        response.headers.set('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response.headers.set('Content-Disposition', 'attachment', filename=nome_arquivo)

    return response

@app.route('/download/<nome_arquivo>')
def baixar_arquivo(nome_arquivo):
    return send_from_directory(OUTPUT_DIR, nome_arquivo, as_attachment=True)

@app.route('/trabalhos')
def trabalhos():
    lista = listar_trabalhos()
    return render_template('trabalhos.html', trabalhos=lista)

import webbrowser
import threading

def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1.0, abrir_navegador).start()
    app.run(debug=True, use_reloader=False)
