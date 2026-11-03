<img src="assets/logo_pulso.png" alt="Pulso · Atividade e Sono" width="320">

# Dashboard Fitbit — Atividade e Sono

Dashboard interativo em Python (Dash + Plotly) com os dados de atividade física e sono de 35 usuárias de Fitbit, de 12/03/2016 a 12/05/2016.

## Como rodar

```bash
pip install -r requirements.txt
python dashboard_fitbit.py
```

Depois abra http://127.0.0.1:8050 no navegador.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `dashboard_fitbit.py` | Código do dashboard |
| `fitbit_dashboard_base.xlsx` | Base de dados (abas "Diário" e "Por Hora") |
| `fitbit_dashboard_.xlsx` | Versão do dashboard feita no Excel |
| `assets/logo_pulso.png` | Logo |

## Regras de cálculo

- **Atividade:** exclui dias com 0 passos (dias sem uso do aparelho).
- **Sono:** considera só as noites com `MinutesAsleep > 0`.
- **Cobertura do sono:** noites com sono ÷ todos os dias do filtro.
- **Passos por hora:** usa a aba "Por Hora", sem filtro de passos.
- O filtro de mês (Todos, Março, Abril, Maio) recalcula o painel inteiro.

## Fonte dos dados

FitBit Fitness Tracker Data: Furberg, Brinton, Keating e Ortiz (RTI International), *Crowd-sourced Fitbit datasets 03.12.2016-05.12.2016*, Zenodo, licença CC-BY 4.0. Republicado no Kaggle.

---
Isabella Fernandes · Insper
