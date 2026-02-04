from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from playwright.sync_api import sync_playwright
import time
import os
import base64
from io import BytesIO
import zipfile
import re

app = Flask(__name__)
CORS(app)

class CNPJAutomation:
    def __init__(self):
        self.browser = None
        self.page = None
    
    def setup_browser(self):
        """Configura o Playwright"""
        try:
            playwright = sync_playwright().start()
            
            # Inicia browser headless
            self.browser = playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-extensions'
                ]
            )
            
            # Cria nova página
            self.page = self.browser.new_page()
            return True
        except Exception as e:
            print(f"Erro ao iniciar browser: {str(e)}")
            return False
    
    def access_receita_federal(self, cnpj):
        """Acessa o site da Receita Federal e preenche o CNPJ"""
        try:
            url = "https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp"
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Limpa e formata o CNPJ
            cnpj_clean = ''.join(filter(str.isdigit, cnpj))
            
            # Preenche o campo CNPJ
            self.page.fill('input[name="cnpj"]', cnpj_clean)
            
            # Aguarda um pouco
            time.sleep(1)
            
            return True
        except Exception as e:
            print(f"Erro ao acessar Receita Federal: {str(e)}")
            return False
    
    def check_and_solve_captcha(self):
        """Verifica se há captcha e aguarda resolução"""
        try:
            # Verifica se existe captcha
            captcha_exists = self.page.locator('img[src*="captcha"]').count() > 0
            
            if captcha_exists:
                print("Captcha detectado - aguardando resolução manual...")
                # Em produção, você implementaria uma pausa para o usuário resolver
                # Por enquanto, vamos aguardar alguns segundos
                time.sleep(5)
            
            return True
        except Exception as e:
            print(f"Erro ao verificar captcha: {str(e)}")
            return False
    
    def submit_form(self):
        """Submete o formulário"""
        try:
            # Clica no botão de consultar
            self.page.click('input[type="submit"]')
            
            # Aguarda a página carregar
            self.page.wait_for_load_state('networkidle', timeout=30000)
            time.sleep(2)
            
            return True
        except Exception as e:
            print(f"Erro ao submeter formulário: {str(e)}")
            return False
    
    def extract_company_name(self):
        """Extrai o nome da empresa da página"""
        try:
            # Procura pelo campo com a razão social
            content = self.page.content()
            
            # Busca por NOME EMPRESARIAL ou RAZAO SOCIAL
            match = re.search(r'(?:NOME EMPRESARIAL|RAZAO SOCIAL)[:\s]*([A-Z0-9\s\-\.]+)', content)
            if match:
                company_name = match.group(1).strip()
                # Remove caracteres inválidos para nome de arquivo
                company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
                return company_name[:50]  # Limita tamanho
            
            return "Empresa_CNPJ"
        except Exception as e:
            print(f"Erro ao extrair nome: {str(e)}")
            return "Empresa_CNPJ"
    
    def generate_pdf_from_page(self):
        """Gera PDF da página atual (exatamente como está na tela)"""
        try:
            # Gera PDF da página inteira
            pdf_bytes = self.page.pdf(
                format='A4',
                print_background=True,
                margin={
                    'top': '1cm',
                    'right': '1cm',
                    'bottom': '1cm',
                    'left': '1cm'
                }
            )
            
            return pdf_bytes
        except Exception as e:
            print(f"Erro ao gerar PDF: {str(e)}")
            return None
    
    def navigate_to_qsa(self):
        """Navega para a página do QSA"""
        try:
            # Procura pelo link do QSA
            qsa_link = self.page.locator('a:has-text("Quadro de Sócios")').first
            
            if qsa_link.count() > 0:
                qsa_link.click()
                self.page.wait_for_load_state('networkidle', timeout=30000)
                time.sleep(2)
                return True
            else:
                # Tenta alternativa
                qsa_link = self.page.locator('a:has-text("QSA")').first
                if qsa_link.count() > 0:
                    qsa_link.click()
                    self.page.wait_for_load_state('networkidle', timeout=30000)
                    time.sleep(2)
                    return True
            
            return False
        except Exception as e:
            print(f"Erro ao navegar para QSA: {str(e)}")
            return False
    
    def close(self):
        """Fecha o navegador"""
        if self.browser:
            self.browser.close()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de verificação de saúde"""
    return jsonify({"status": "ok", "message": "Backend rodando! (Versão Playwright)"})

@app.route('/api/consult', methods=['POST'])
def consult_cnpj():
    """Endpoint principal de consulta"""
    automation = None
    try:
        data = request.json
        cnpj = data.get('cnpj')
        
        if not cnpj:
            return jsonify({"error": "CNPJ não fornecido"}), 400
        
        # Inicia automação
        automation = CNPJAutomation()
        
        if not automation.setup_browser():
            return jsonify({"error": "Erro ao iniciar navegador"}), 500
        
        # Acessa Receita Federal
        if not automation.access_receita_federal(cnpj):
            return jsonify({"error": "Erro ao acessar Receita Federal"}), 500
        
        # Verifica captcha
        automation.check_and_solve_captcha()
        
        # Submete formulário
        if not automation.submit_form():
            return jsonify({"error": "Erro ao submeter consulta"}), 500
        
        # Extrai nome da empresa
        company_name = automation.extract_company_name()
        
        # Gera PDF do Cartão CNPJ (página atual)
        pdf_cartao = automation.generate_pdf_from_page()
        if not pdf_cartao:
            return jsonify({"error": "Erro ao gerar PDF do Cartão"}), 500
        
        # Navega para QSA
        pdf_qsa = None
        if automation.navigate_to_qsa():
            # Gera PDF do QSA
            pdf_qsa = automation.generate_pdf_from_page()
        
        # Cria ZIP com os PDFs
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f'{company_name}/Cartao_CNPJ.pdf', pdf_cartao)
            if pdf_qsa:
                zip_file.writestr(f'{company_name}/QSA.pdf', pdf_qsa)
        
        zip_buffer.seek(0)
        
        # Fecha o navegador
        automation.close()
        
        # Retorna o ZIP
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{company_name}.zip'
        )
        
    except Exception as e:
        print(f"Erro na consulta: {str(e)}")
        if automation:
            automation.close()
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
