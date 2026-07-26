
import machine
import time


LDR_PIN = 34
BTN_PIN = 15

adc = machine.ADC(machine.Pin(LDR_PIN))
adc.atten(machine.ADC.ATTN_11DB)

btn = machine.Pin(BTN_PIN, machine.Pin.IN, machine.Pin.PULL_UP)

ADC_LIMIAR_CLARO = 1200
ADC_LIMIAR_ESCURO = 2000
MICROPARADA_MS = 5000
DEBOUNCE_MS = 50


estado_sensor = "LIVRE"
contador_pecas = 0
tempo_inicio_bloqueio = None
alerta_microparada_emitido = False

estado_btn_bruto = 1
estado_btn_confirmado = 1
tempo_ultima_mudanca_btn = 0


def ler_adc():

    return adc.read()

def resetar_turno():
    global contador_pecas, tempo_inicio_bloqueio, alerta_microparada_emitido
    contador_pecas = 0
    tempo_inicio_bloqueio = None
    alerta_microparada_emitido = False
    print("Turno resetado com sucesso. Contadores zerados.")


def verificar_botao():
    global estado_btn_bruto, estado_btn_confirmado, tempo_ultima_mudanca_btn

    leitura = btn.value()
    agora = time.ticks_ms()

    if leitura != estado_btn_bruto:
        estado_btn_bruto = leitura
        tempo_ultima_mudanca_btn = agora

    if time.ticks_diff(agora, tempo_ultima_mudanca_btn) > DEBOUNCE_MS:
        if leitura != estado_btn_confirmado:
            estado_btn_confirmado = leitura

            if leitura == 1:
                resetar_turno()


def verificar_sensor():
    global estado_sensor, contador_pecas, tempo_inicio_bloqueio, alerta_microparada_emitido

    valor_adc = ler_adc()
    agora = time.ticks_ms()

    if estado_sensor == "LIVRE":
        if valor_adc > ADC_LIMIAR_ESCURO:
            estado_sensor = "BLOQUEADO"
            tempo_inicio_bloqueio = agora
            alerta_microparada_emitido = False

    elif estado_sensor == "BLOQUEADO":
        if valor_adc < ADC_LIMIAR_CLARO:

            estado_sensor = "LIVRE"
            contador_pecas += 1
            tempo_inicio_bloqueio = None
            alerta_microparada_emitido = False
            print("Peca detectada! Total: {}".format(contador_pecas))
        else:

            if tempo_inicio_bloqueio is not None and not alerta_microparada_emitido:
                if time.ticks_diff(agora, tempo_inicio_bloqueio) > MICROPARADA_MS:
                    print("Alerta: Micro-parada detectada!")
                    alerta_microparada_emitido = True


def main():
    print("Contador de Producao Inicializado")
    while True:
        verificar_sensor()
        verificar_botao()
        time.sleep_ms(10)


main()
