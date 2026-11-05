# Prévia das métricas coletadas
2026-11-05T13:23:36.538102+00:00

Tokens totais = entrada + saída; cache é subconjunto de entrada; raciocínio é subconjunto de saída. Rodadas não são somadas como percentuais de economia.

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
- one native B run has incomplete usage after subscription limit
- latest editor confirmation used code before subsequent hardening
- neural document compression is not Codex task savings
- cached input is part of input, reasoning output part of output
- experiment totals exclude other Codex validation calls; inspect their individual event logs