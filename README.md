# Contador de Produção Não-Intrusivo

## Identificação do Candidato

- **Nome completo:** Eduardo Rodrigues Do Nascimento
- **GitHub:** https://github.com/Eduardo-Rodri

---

## Visão Geral da Solução

O projeto implementa um **contador de produção não-intrusivo** para linhas de montagem manuais ou semiautomáticas que operam sem CLP. O objetivo é substituir a contagem manual de peças por uma solução de baixo custo baseada em sensor óptico.

O sistema utiliza um sensor LDR posicionado sobre uma esteira: sempre que um objeto interrompe o feixe de luz e depois libera novamente, uma peça é contabilizada. Em paralelo, o firmware monitora quanto tempo o sensor permanece bloqueado continuamente, emitindo um alerta caso esse tempo indique uma possível parada da linha (gargalo). Um botão físico permite ao operador resetar a contagem e os temporizadores ao final de um turno.

O usuário interage com o sistema apenas através do botão de reset; toda a leitura e contagem acontece de forma automática, e o status é reportado via saída Serial (UART).

---

## Arquitetura do Sistema Embarcado

O firmware é organizado em torno de um **loop principal não-bloqueante**, que a cada iteração (com um pequeno intervalo de 10ms) executa duas verificações independentes:

```
main()
 ├── verificar_sensor()   → máquina de estados do LDR
 └── verificar_botao()    → leitura do botão com debounce
```

### Máquina de estados do sensor (`verificar_sensor`)

- **LIVRE**: estado inicial, luz alta chegando ao LDR.
- **BLOQUEADO**: um objeto interrompeu o feixe de luz.

A transição `LIVRE → BLOQUEADO` ocorre quando a leitura do ADC ultrapassa o limiar de escuridão. A contagem só é incrementada na transição de volta `BLOQUEADO → LIVRE` (borda de subida da luminosidade), garantindo que o objeto tenha passado completamente pelo sensor antes de ser contado.

Enquanto o estado permanece em `BLOQUEADO`, um cronômetro não-bloqueante (baseado em `time.ticks_ms()` / `time.ticks_diff()`) verifica se o tempo de bloqueio contínuo ultrapassou o limite parametrizado, disparando o alerta de micro-parada uma única vez por evento de bloqueio.

### Leitura do botão (`verificar_botao`)

Implementa debounce por software: mantém separada a última leitura bruta do pino (`estado_btn_bruto`) da última leitura já confirmada como estável (`estado_btn_confirmado`). Só depois que o pino permanece estável por mais que `DEBOUNCE_MS` a mudança é considerada válida, evitando falsos acionamentos por ruído no sinal. O reset é disparado quando o botão é **solto** após ter sido pressionado (transição estável para nível alto, já que o pino está configurado com pull-up interno).

---

## Componentes Utilizados na Simulação

| Componente | ID no `diagram.json` | Função |
|---|---|---|
| ESP32 DevKit C v4 | `esp` | Microcontrolador principal, executa o firmware MicroPython |
| Sensor fotorresistor (LDR) | `ldr1` | Detecta a passagem de objetos pela variação de luminosidade, ligado ao pino ADC (GPIO 34) |
| Botão de pressão | `btn1` | Reset manual de turno, ligado ao GPIO 15 com pull-up interno |
| Serial Monitor (UART) | — | Transmissão de logs de status, contagem e alertas |

---

## Decisões Técnicas Relevantes

- **Calibração direta no valor bruto do ADC, em vez de uma fórmula de "lux estimado":** inicialmente o firmware convertia a leitura do ADC para uma escala de 0–1000 assumindo relação linear direta com a luminosidade. Ao testar no simulador, percebeu-se que o módulo de LDR utilizado tem comportamento **inverso e não-linear** (quanto mais escuro, maior o valor lido no ADC). Por isso, os limiares (`ADC_LIMIAR_CLARO` e `ADC_LIMIAR_ESCURO`) foram recalibrados empiricamente a partir de medições reais no simulador, com folga de segurança em torno dos valores observados para os cenários de teste (claro e escuro).
- **Histerese de dois limiares:** em vez de um único ponto de corte, foram usados dois limiares distintos (um para entrar em `BLOQUEADO`, outro para voltar a `LIVRE`), evitando oscilações de estado quando a leitura do sensor fica próxima da fronteira.
- **Debounce com estado bruto e estado confirmado separados:** a primeira versão do debounce comparava a leitura atual com uma variável que era sobrescrita a cada iteração do loop, o que impedia a condição de reset de ser satisfeita. A correção separou a leitura instantânea do pino da leitura já validada como estável, resolvendo o problema.
- **Arquitetura 100% não-bloqueante:** nenhuma função usa `sleep` prolongado ou espera ativa; todos os temporizadores (micro-parada, debounce) são controlados por comparação de timestamps (`time.ticks_ms()`), garantindo que o loop principal continue respondendo aos estímulos do simulador em tempo hábil.

---

## Resultados Obtidos

Os três cenários de validação foram testados manualmente no simulador antes do envio, com resultado positivo em todos:

- **Contagem de peças:** ao simular a queda e o retorno da luminosidade no LDR, o sistema imprime corretamente `"Peca detectada! Total: X"`, incrementando a cada ciclo completo.
- **Micro-parada:** ao manter o sensor bloqueado continuamente por mais de 5 segundos, o sistema imprime `"Alerta: Micro-parada detectada!"` uma única vez por evento.
- **Reset de turno:** ao acionar o botão, o sistema imprime `"Turno resetado com sucesso. Contadores zerados."` e a contagem seguinte reinicia do zero, confirmando que os contadores e temporizadores internos foram efetivamente zerados.

---

## Comentários Adicionais

O maior aprendizado do desafio foi entender que o comportamento elétrico de um componente simulado (como o LDR) não pode ser assumido a partir de teoria genérica, foi necessário instrumentar o código com prints de depuração (valor bruto do ADC) para calibrar os limiares corretamente contra os valores reais que o simulador entrega. Da mesma forma, o bug no debounce do botão reforçou a importância de separar claramente "leitura instantânea" de "estado confirmado" em qualquer lógica baseada em temporização. Também foi observado que o tempo de boot completo do ESP32 somado à inicialização do MicroPython pode consumir boa parte do orçamento de tempo padrão da simulação no CI, exigindo atenção ao ajustar os parâmetros de timeout dos cenários de teste.

Com mais tempo, uma melhoria possível seria tornar os limiares de luminosidade autoajustáveis (calibração automática nos primeiros segundos de execução), em vez de valores fixos definidos manualmente.
