# Metodologia e estado do experimento

A meta se refere a tokens Codex por tarefa aceita, somando tentativas malsucedidas. O total soma input_tokens e output_tokens; cached_input_tokens é subconjunto do input, reasoning_output_tokens é informado separadamente sem somá-lo novamente ao output. Nenhuma métrica local de bytes, ranking ou custo de API é convertida em limite da assinatura.

Referência: Codex CLI 0.166.0, login ChatGPT, modelo gpt-6.1-sol, esforço high, mesma configuração do usuário e ferramentas comuns a todos os braços; ephemeral, workspace-write, approval_policy=never. O perfil economy não é carregado nos braços, evitando mudança global de MCP. A é execução normal sem pacote pré-selecionado; B recebe seleção lexical e C recebe seleção híbrida lexical/TF-IDF. Ambos usam a CLI normal, que ainda pode usar ferramentas nativas. Logo, este experimento mede preparação de contexto; não demonstra interceptação ou controle universal de saídas internas. O runner retém e resume a saída da execução, mas não reescreve observações internas do Codex.

A rodada exploratória em evidence/benchmark foi interrompida após descoberta de alteração de whitespace em fixtures pelo formatador. Resultados e uma tentativa cancelada estão preservados em results.jsonl e cancelled-attempts.json; metodologia-warning.json impede interpretá-la como confirmação final. Não elimine tentativas fracassadas nem selecione apenas sucessos. Relatórios exploratórios não sustentam a meta de 80%.

A confirmação em evidence/confirmation-manifest.json usa 12 funções reservadas, distribuídas em Python, Node e C++, três repetições por braço A/B/C (108 jobs). São tarefas pequenas e representativas, com defeito existente e verificações executáveis; não representam grandes projetos Next/Android. Inputs e implementação recebem hashes congelados. Cada job copia uma fixture para workspace próprio, inicializa Git, gera contexto sem soluções, executa Codex e verifica testes e a invariância de todos arquivos salvo o alvo. Artefatos de build/cache são excluídos da comparação. Ordem aleatória fixa por seed. Todos braços usam mesmo modelo/esforço/timeout. Auxiliares remotos estão desligados; reranking local não compartilha soluções. Codex pode usar cache de prefixo do servidor e isso é registrado como cache observado, não controlado pelo produto.

D exige Jev real e permanece bloqueado pela ausência de TYPESAFE_API_KEY; não substituir por mock ou local. E só deve ser confirmado se piloto separado demonstrar vantagem de estratégia distinta; ainda pendente. Calibração Jev e variantes neurais não foram realizadas. Portanto a confirmação A/B/C, mesmo concluída, não satisfaz todos os requisitos da avaliação contratada.

Os dados brutos preservam usage, ações item.completed, duração, custo de indexação, exit codes, verificações, patches e hashes. Faltam contagens específicas confiáveis de releituras/compactações, regressões extensas e custo amortizado completo de manutenção. Ausência de usage impede calcular tokens por aceita para o braço. Consumo do limite da assinatura e custo monetário auxiliar são indisponíveis onde não expostos.

Report usa totais por braço e bootstrap pareado A–C apenas em pares disponíveis aceitos, com seed fixa e intervalo 95%. Este subconjunto pareado é descritivo; não corrige viés de sobrevivência e deve ser interpretado junto com falhas e taxas de aceite de todos os jobs. Confirmação de qualidade equivalente requer comparar essas taxas, regressões e mudanças fora de escopo, não apenas tokens. O flag complete indica conclusão da fila especificada, não validação de produção ou de todo o experimento solicitado.

```bash
ce benchmark evidence/confirmation-manifest.json        # fila restante
ce benchmark evidence/confirmation-manifest.json --execute
ce benchmark evidence/confirmation-manifest.json --report
systemctl --user status codex-economy-confirmation
journalctl --user -u codex-economy-confirmation --no-pager
```

Não inicie duas instâncias sobre a mesma fila. Se houver workspace sem linha final registrada após interrupção, conserve o workspace e a linha em runs do banco; reconcilie a tentativa cancelada antes de retomada. O executor recusa sobrescrever workspace incompleto. Recuperação automática dessa situação é uma pendência operacional conhecida.

Limiares de performance local definidos antes da execução em scripts/performance.py: carga sintética de 600 arquivos/3 projetos, fria <10s, incremental p95 <2s, lexical p95 <1s e RSS <512 MiB. Hardware, amostras, percentis e tamanho do banco estão em evidence/performance.json. Não extrapolar para repositórios gigantes.
