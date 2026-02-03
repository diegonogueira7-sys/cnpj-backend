from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import os
import base64
from io import BytesIO
import zipfile
import json

app = Flask(__name__)
CORS(app)

class CNPJAutomation:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Configura o Chrome com Selenium"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--single-process')
        
        # User agent para evitar detecção de bot
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Para produção no Render
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
        
        service = Service(executable_path=os.environ.get("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver"))
        
        try:
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"Erro ao iniciar Chrome: {str(e)}")
            # Tenta caminho alternativo
            service = Service(executable_path="/usr/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def access_receita_federal(self, cnpj):
        """Acessa o site da Receita Federal"""
        try:
            url = "https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp"
            self.driver.get(url)
            
            # Aguarda o campo CNPJ estar disponível
            cnpj_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "cnpj"))
            )
            
            # Limpa e formata o CNPJ
            cnpj_clean = ''.join(filter(str.isdigit, cnpj))
            cnpj_input.clear()
            cnpj_input.send_keys(cnpj_clean)
            
            return True
        except Exception as e:
            print(f"Erro ao acessar Receita Federal: {str(e)}")
            return False
    
    def check_captcha(self):
        """Verifica se há captcha na página"""
        try:
            # Procura por elementos comuns de captcha
            captcha_elements = self.driver.find_elements(By.XPATH, "//*[contains(@id, 'captcha') or contains(@class, 'captcha')]")
            
            if captcha_elements:
                # Captura screenshot do captcha
                captcha_img = captcha_elements[0].screenshot_as_base64
                return True, captcha_img
            
            return False, None
        except Exception as e:
            print(f"Erro ao verificar captcha: {str(e)}")
            return False, None
    
    def wait_for_captcha_resolution(self):
        """Aguarda resolução do captcha pelo usuário"""
        # Implementação simplificada - na prática, usaríamos WebSockets
        time.sleep(2)
        return True
    
    def extract_company_name(self):
        """Extrai o nome da empresa da página"""
        try:
            # Aguarda a página carregar
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Procura pelo nome/razão social
            elements = self.driver.find_elements(By.XPATH, "//b[contains(text(), 'RAZAO SOCIAL')]/following::font[1]")
            if elements:
                company_name = elements[0].text.strip()
                # Remove caracteres inválidos para nome de arquivo
                company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
                return company_name
            
            return "Empresa_Desconhecida"
        except Exception as e:
            print(f"Erro ao extrair nome da empresa: {str(e)}")
            return "Empresa_Desconhecida"
    
    def generate_pdf_cartao(self):
        """Gera PDF do Cartão CNPJ"""
        try:
            # Captura a página atual como PDF
            pdf_data = self.driver.execute_cdp_cmd("Page.printToPDF", {
                "printBackground": True,
                "landscape": False,
                "paperWidth": 8.27,
                "paperHeight": 11.69,
                "marginTop": 0,
                "marginBottom": 0,
                "marginLeft": 0,
                "marginRight": 0
            })
            
            pdf_bytes = base64.b64decode(pdf_data['data'])
            return pdf_bytes
        except Exception as e:
            print(f"Erro ao gerar PDF do Cartão: {str(e)}")
            return None
    
    def navigate_to_qsa(self):
        """Navega para a página do QSA"""
        try:
            # Procura pelo link do QSA
            qsa_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "QSA"))
            )
            qsa_link.click()
            
            # Aguarda a nova página carregar
            time.sleep(2)
            return True
        except Exception as e:
            print(f"Erro ao navegar para QSA: {str(e)}")
            return False
    
    def generate_pdf_qsa(self):
        """Gera PDF do QSA"""
        try:
            pdf_data = self.driver.execute_cdp_cmd("Page.printToPDF", {
                "printBackground": True,
                "landscape": False,
                "paperWidth": 8.27,
                "paperHeight": 11.69,
                "marginTop": 0,
                "marginBottom": 0,
                "marginLeft": 0,
                "marginRight": 0
            })
            
            pdf_bytes = base64.b64decode(pdf_data['data'])
            return pdf_bytes
        except Exception as e:
            print(f"Erro ao gerar PDF do QSA: {str(e)}")
            return None
    
    def close(self):
        """Fecha o navegador"""
        if self.driver:
            self.driver.quit()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de verificação de saúde"""
    return jsonify({"status": "ok", "message": "Backend rodando!"})

@app.route('/api/consult', methods=['POST'])
def consult_cnpj():
    """Endpoint principal de consulta"""
    try:
        data = request.json
        cnpj = data.get('cnpj')
        
        if not cnpj:
            return jsonify({"error": "CNPJ não fornecido"}), 400
        
        # Inicia automação
        automation = CNPJAutomation()
        
        # Acessa Receita Federal
        if not automation.access_receita_federal(cnpj):
            return jsonify({"error": "Erro ao acessar Receita Federal"}), 500
        
        # Verifica captcha
        has_captcha, captcha_img = automation.check_captcha()
        
        if has_captcha:
            return jsonify({
                "status": "captcha_required",
                "captcha_image": captcha_img,
                "message": "Por favor, resolva o captcha"
            })
        
        # Extrai nome da empresa
        company_name = automation.extract_company_name()
        
        # Gera PDF do Cartão CNPJ
        pdf_cartao = automation.generate_pdf_cartao()
        if not pdf_cartao:
            return jsonify({"error": "Erro ao gerar PDF do Cartão"}), 500
        
        # Navega para QSA
        if not automation.navigate_to_qsa():
            return jsonify({"error": "Erro ao acessar QSA"}), 500
        
        # Gera PDF do QSA
        pdf_qsa = automation.generate_pdf_qsa()
        if not pdf_qsa:
            return jsonify({"error": "Erro ao gerar PDF do QSA"}), 500
        
        # Cria ZIP com ambos os PDFs
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f'{company_name}/Cartao_CNPJ.pdf', pdf_cartao)
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
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@app.route('/api/resolve-captcha', methods=['POST'])
def resolve_captcha():
    """Endpoint para continuar após resolução do captcha"""
    # Implementação futura com WebSockets ou polling
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
