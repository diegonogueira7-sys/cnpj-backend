from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
from io import BytesIO
import zipfile
import json
import time
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

app = Flask(__name__)
CORS(app)

class CNPJConsulta:
    """Consulta CNPJ usando API pública da Receita Federal"""
    
    def __init__(self):
        self.base_url = "https://www.receitaws.com.br/v1/cnpj/"
    
    def consultar_cnpj(self, cnpj):
        """Consulta dados do CNPJ via API"""
        try:
            # Remove formatação
            cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
            
            # Faz requisição para API
            response = requests.get(f"{self.base_url}{cnpj_limpo}", timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"Erro na consulta: {str(e)}")
            return None
    
    def gerar_pdf_cartao(self, dados):
        """Gera PDF do Cartão CNPJ"""
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        
        # Título
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(2*cm, 28*cm, "CARTÃO CNPJ")
        
        # Linha separadora
        pdf.line(2*cm, 27.5*cm, 19*cm, 27.5*cm)
        
        # Dados
        y = 26*cm
        pdf.setFont("Helvetica", 11)
        
        campos = [
            ("CNPJ:", dados.get('cnpj', 'N/A')),
            ("Razão Social:", dados.get('nome', 'N/A')),
            ("Nome Fantasia:", dados.get('fantasia', 'N/A')),
            ("Data Abertura:", dados.get('abertura', 'N/A')),
            ("Situação:", dados.get('situacao', 'N/A')),
            ("Tipo:", dados.get('tipo', 'N/A')),
            ("Porte:", dados.get('porte', 'N/A')),
            ("Natureza Jurídica:", dados.get('natureza_juridica', 'N/A')),
            ("Capital Social:", f"R$ {dados.get('capital_social', 'N/A')}"),
            ("", ""),
            ("Endereço:", ""),
            ("Logradouro:", dados.get('logradouro', 'N/A')),
            ("Número:", dados.get('numero', 'N/A')),
            ("Complemento:", dados.get('complemento', 'N/A')),
            ("Bairro:", dados.get('bairro', 'N/A')),
            ("Município:", dados.get('municipio', 'N/A')),
            ("UF:", dados.get('uf', 'N/A')),
            ("CEP:", dados.get('cep', 'N/A')),
            ("", ""),
            ("Contato:", ""),
            ("Telefone:", dados.get('telefone', 'N/A')),
            ("Email:", dados.get('email', 'N/A')),
        ]
        
        for campo, valor in campos:
            if campo:
                pdf.setFont("Helvetica-Bold", 10)
                pdf.drawString(2*cm, y, campo)
                pdf.setFont("Helvetica", 10)
                pdf.drawString(6*cm, y, str(valor))
                y -= 0.6*cm
            else:
                y -= 0.3*cm
        
        # Rodapé
        pdf.setFont("Helvetica-Oblique", 8)
        pdf.drawString(2*cm, 2*cm, "Documento gerado via API pública da Receita Federal")
        pdf.drawString(2*cm, 1.5*cm, f"Data: {time.strftime('%d/%m/%Y %H:%M:%S')}")
        
        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def gerar_pdf_qsa(self, dados):
        """Gera PDF do QSA (Quadro de Sócios e Administradores)"""
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        
        # Título
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(2*cm, 28*cm, "QUADRO DE SÓCIOS E ADMINISTRADORES (QSA)")
        
        # Linha separadora
        pdf.line(2*cm, 27.5*cm, 19*cm, 27.5*cm)
        
        # Dados da empresa
        y = 26.5*cm
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(2*cm, y, "CNPJ:")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(5*cm, y, dados.get('cnpj', 'N/A'))
        
        y -= 0.7*cm
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(2*cm, y, "Razão Social:")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(5*cm, y, dados.get('nome', 'N/A'))
        
        # Lista de sócios
        y -= 1.5*cm
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(2*cm, y, "Sócios e Administradores:")
        
        y -= 1*cm
        qsa = dados.get('qsa', [])
        
        if qsa and len(qsa) > 0:
            for i, socio in enumerate(qsa, 1):
                pdf.setFont("Helvetica-Bold", 10)
                pdf.drawString(2*cm, y, f"{i}. {socio.get('nome', 'N/A')}")
                y -= 0.5*cm
                
                pdf.setFont("Helvetica", 9)
                pdf.drawString(2.5*cm, y, f"Qualificação: {socio.get('qual', 'N/A')}")
                y -= 1*cm
                
                if y < 3*cm:
                    pdf.showPage()
                    y = 28*cm
        else:
            pdf.setFont("Helvetica", 10)
            pdf.drawString(2*cm, y, "Nenhum sócio encontrado.")
        
        # Rodapé
        pdf.setFont("Helvetica-Oblique", 8)
        pdf.drawString(2*cm, 2*cm, "Documento gerado via API pública da Receita Federal")
        pdf.drawString(2*cm, 1.5*cm, f"Data: {time.strftime('%d/%m/%Y %H:%M:%S')}")
        
        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de verificação de saúde"""
    return jsonify({"status": "ok", "message": "Backend rodando! (Versão API)"})

@app.route('/api/consult', methods=['POST'])
def consult_cnpj():
    """Endpoint principal de consulta"""
    try:
        data = request.json
        cnpj = data.get('cnpj')
        
        if not cnpj:
            return jsonify({"error": "CNPJ não fornecido"}), 400
        
        # Consulta CNPJ
        consulta = CNPJConsulta()
        dados = consulta.consultar_cnpj(cnpj)
        
        if not dados:
            return jsonify({"error": "CNPJ não encontrado ou inválido"}), 404
        
        if dados.get('status') == 'ERROR':
            return jsonify({"error": dados.get('message', 'Erro desconhecido')}), 400
        
        # Nome da empresa para a pasta
        company_name = dados.get('nome', 'Empresa_Desconhecida')
        company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
        
        # Gera PDFs
        pdf_cartao = consulta.gerar_pdf_cartao(dados)
        pdf_qsa = consulta.gerar_pdf_qsa(dados)
        
        # Cria ZIP com ambos os PDFs
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f'{company_name}/Cartao_CNPJ.pdf', pdf_cartao)
            zip_file.writestr(f'{company_name}/QSA.pdf', pdf_qsa)
        
        zip_buffer.seek(0)
        
        # Retorna o ZIP
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{company_name}.zip'
        )
        
    except Exception as e:
        print(f"Erro na consulta: {str(e)}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
