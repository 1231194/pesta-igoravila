import time
import math
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

CORRENTE_MAX_CONTRATADA = 25.0     

CORRENTE_MIN_CARGA = 6.0            

MARGEM_SEGURANCA = 2.0              

CT_RATIO = 1000.0                    

BURDEN_RESISTOR = 22.0              

NUM_AMOSTRAS = 100

ADS_GAIN = 1

CT_CANAL = 0

HTTP_PORT = 7070


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def inicializar_adc():
    log.info("Modo de simulação ativo - Sem hardware ADC")
    return None 


def ler_corrente_rms(canal: AnalogIn) -> float:
    import random 
    return round(random.uniform(8.0, 18.0), 3)


def calcular_corrente_disponivel(corrente_atual: float) -> float:

    disponivel = CORRENTE_MAX_CONTRATADA - corrente_atual - MARGEM_SEGURANCA
    disponivel = max(CORRENTE_MIN_CARGA, min(disponivel, 32.0))
    return round(disponivel, 1)


estado = {
    "corrente_atual_A": 0.0,
    "corrente_disponivel_A": CORRENTE_MAX_CONTRATADA - MARGEM_SEGURANCA,
    "potencia_W": 0.0,
    "timestamp": 0,
}
estado_lock = threading.Lock()


class EVCCHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        with estado_lock:
            dados = dict(estado)

        if self.path == "/meter":
            resposta = {
                "power": dados["potencia_W"],         
                "currents": [dados["corrente_atual_A"], 0, 0],
            }
        elif self.path == "/charge":
            resposta = {
                "maxCurrent": dados["corrente_disponivel_A"],
            }
        elif self.path == "/status":
            resposta = dados
        else:
            self.send_response(404)
            self.end_headers()
            return

        corpo = json.dumps(resposta).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(corpo))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, fmt, *args):
        pass


def iniciar_servidor_http():
    servidor = HTTPServer(("0.0.0.0", HTTP_PORT), EVCCHandler)
    log.info("Servidor HTTP a escutar em :%d", HTTP_PORT)
    servidor.serve_forever()


def loop_leitura(canal: AnalogIn, tensao_rede: float = 230.0):
    """
    Loop contínuo de leitura do CT e actualização do estado global.
    Executa na thread principal; o servidor HTTP corre em background.
    """
    log.info("Loop de leitura iniciado (Ctrl+C para parar)")

    while True:
        try:
            corrente = ler_corrente_rms(canal)
            disponivel = calcular_corrente_disponivel(corrente)
            potencia = corrente * tensao_rede         

            with estado_lock:
                estado["corrente_atual_A"] = corrente
                estado["corrente_disponivel_A"] = disponivel
                estado["potencia_W"] = round(potencia, 1)
                estado["timestamp"] = int(time.time())

            log.info(
                "I_atual=%.2f A | I_disponível=%.1f A | P=%.0f W",
                corrente, disponivel, potencia,
            )

        except Exception as exc:
            log.error("Erro na leitura do ADC: %s", exc)

        time.sleep(1)   


def main():
    canal = inicializar_adc()

    
    t = threading.Thread(target=iniciar_servidor_http, daemon=True)
    t.start()

    loop_leitura(canal)


if __name__ == "__main__":
    main()
