# Prévia das métricas coletadas
2026-11-10T00:19:05.322881+00:00

Tokens totais = entrada + saída; cache é subconjunto de entrada; raciocínio é subconjunto de saída. Rodadas não são somadas como percentuais de economia.

Veredito A/E atual: achieved (84.16% observada; IC 95% agrupado por tarefa 82.83%–85.30%; aceite A/E 36/36).

| Rodada | Braço | Tentativas | Aceitas | Entrada | Cache | Saída | Raciocínio | Total observado | Tokens/aceita | Tempo s | p50 s | p95 s | Ações |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|benchmark|C|13|12|864325|762112|6277|119|870602|None|264.027|20.055|29.982|83|
|benchmark|B|11|10|765600|677504|6149|114|771749|77174.9|235.591|20.706|29.199|79|
|benchmark|A|8|7|612347|549376|4201|96|616548|88078.28571428571|182.719|23.51|27.875|61|
|confirmation|C|5|5|388119|342912|4308|378|392427|78485.4|142.287|25.92|42.323|37|
|confirmation|B|2|1|65969|61056|881|38|66850|None|41.134|20.567|28.186|10|
|confirmation|A|2|2|168496|147328|2452|258|170948|85474.0|70.378|35.189|38.717|18|
|confirmation-v2|C|36|36|2664961|2322944|30733|1523|2695694|74880.38888888889|1066.712|28.01|39.484|264|
|confirmation-v2|B|36|35|2677674|2390400|30879|1804|2708553|None|1026.506|27.092|34.815|283|
|confirmation-v2|A|36|36|3035583|2731008|35056|3954|3070639|85295.52777777778|1189.901|32.374|42.796|279|
|editor-pilot|E|3|3|53852|0|338|17|54190|18063.333333333332|21.971|7.336|8.261|3|
|editor-pilot|A|3|3|215271|181888|2907|503|218178|72726.0|99.921|34.953|38.015|21|
|editor-confirmation|E|1|0|0|0|0|0|0|None|1.318|1.318|1.318|0|
|editor-confirmation-r2|E|36|36|470871|80000|10404|3894|481275|13368.75|436.547|11.062|22.472|36|
|editor-confirmation-r2|A|36|36|2981286|2680064|33436|4076|3014722|83742.27777777778|1205.893|33.149|52.824|281|
|representative-pilot|A|3|3|233487|207744|2420|210|235907|78635.66666666667|99.407|26.25|52.838|22|
|representative-pilot|E|3|3|38439|0|402|0|38841|12947.0|28.571|7.385|14.831|3|
|representative-confirmation|E|12|11|154286|10624|3023|1178|157309|14300.818181818182|141.304|10.529|25.053|11|
|representative-confirmation|A|12|11|849124|762112|9672|1616|858796|None|422.917|32.535|69.708|81|
|representative-confirmation-v2|E|36|33|477522|123648|8974|4063|486496|14742.30303030303|320.689|7.041|21.757|33|
|representative-confirmation-v2|A|36|36|2926173|2638592|30887|4071|2957060|82140.55555555556|982.16|24.06|42.802|271|
|representative-confirmation-redaction-remediation|A|3|3|254766|228480|3101|435|257867|85955.66666666667|90.432|30.077|33.402|27|
|representative-confirmation-redaction-remediation|E|3|3|39453|0|823|439|40276|13425.333333333334|31.84|9.537|12.815|3|
|representative-confirmation-v3|E|36|36|476970|244736|9083|4145|486053|13501.472222222223|330.681|7.316|16.602|36|
|representative-confirmation-v3|A|36|36|3037214|2739968|31587|4012|3068801|85244.47222222222|1024.685|24.095|46.972|289|

Snapshot histórico do CLI, fora do total experimental: 78 execuções, 7 turnos Codex observados, 508,278 tokens. Não some este snapshot aos experimentos: possível sobreposição não pôde ser excluída.
Métricas anonimizadas por execução: runtime-runs.csv. IDs, projetos, comandos, prompts e saídas foram omitidos.

Detalhe por tarefa: metrics-preview-tasks.csv. Artefatos e todas as categorias adicionais: metrics-preview.json.

{
  "requests": 5,
  "input_tokens": 4389,
  "output_tokens": 751,
  "latency_seconds": [
    0.2898440030403435,
    0.29847678600344807,
    0.2602176599903032,
    0.2550935000181198,
    0.34499775897711515
  ],
  "monetary_cost": null
}

Alertas:
- historical exploratory rounds are not confirmation
- representative-confirmation is an earlier 24/72 partial round after its frozen Codex configuration changed
- representative-confirmation-v2 measured the redaction bug before its fix and remains preserved as a separate result
- the redaction-remediation follow-up is one targeted task and is not part of the overall confirmation
- Jev arm D was not run because paid auxiliary calls are disabled
- the supported account subscription usage counter is unavailable
- the anonymized historical runtime snapshot is separate and is not added to experiment totals because overlap cannot be excluded
- four historical attempts have unknown usage; one native B run hit the subscription limit
- historical editor confirmation used code before subsequent hardening
- neural document compression is not Codex task savings
- cached input is part of input, reasoning output part of output
- experiment totals exclude other Codex validation calls; inspect their individual event logs
- current A/E confirmation: 84.16% observed reduction, 95% task-cluster interval 82.83%–85.30%; paired acceptance A-only=0, E-only=0; verdict=achieved