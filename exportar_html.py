"""
Gera "dashboard_pulso.html": uma versão do dashboard em um único arquivo,
que abre direto no navegador (sem Python, funciona offline).

Usa os mesmos cálculos e gráficos de dashboard_fitbit.py. Os quatro filtros
de mês são pré-calculados e o JavaScript só troca o que está na tela.

    python exportar_html.py
"""

import base64
import json
from html import escape

import plotly.io as pio
from plotly.offline import get_plotlyjs

import dashboard_fitbit as d
from dashboard_fitbit import num, pct, CIANO, AMARELO, LARANJA, VERDE, VIOLETA, ROSA, TEXTO_3

SAIDA = d.PASTA / "dashboard_pulso.html"
GRAFICOS = ["g-tendencia", "g-intensidade", "g-semana", "g-hora", "g-calorias",
            "g-bullet", "g-dist", "g-sono-semana", "g-scatter"]


# ----------------------------------------------------------------------------
# Componentes em HTML (equivalentes a kpi() e legenda() do app)
# ----------------------------------------------------------------------------
def kpi(titulo, valor, cor, anel=None):
    texto = (f'<div class="kpi-titulo">{escape(titulo)}</div>'
             f'<div class="kpi-valor" style="color:{cor}">{valor}</div>')
    if anel is not None and not d.pd.isna(anel):
        return (f'<div class="card kpi kpi-anel">'
                f'<div class="anel" style="background:conic-gradient({cor} {anel * 360}deg, '
                f'rgba(255,255,255,0.08) 0)"><div class="anel-miolo">{pct(anel)}</div></div>'
                f'<div class="kpi-texto">{texto}</div></div>')
    return f'<div class="card kpi">{texto}</div>'


def legenda(itens):
    spans = "".join(f'<span style="--c:{c}">{escape(t)}</span>' for t, c in itens)
    return f'<div class="legenda">{spans}</div>'


def card(titulo, grafico_id, subtitulo=None):
    sub = f'<div class="card-sub">{escape(subtitulo)}</div>' if subtitulo else ""
    return (f'<div class="card"><div class="card-titulo">{escape(titulo)}</div>{sub}'
            f'<div id="{grafico_id}" class="grafico"></div></div>')


# ----------------------------------------------------------------------------
# Pré-cálculo dos quatro filtros
# ----------------------------------------------------------------------------
def estado(mes_nome):
    _, ativ, sono, h, k = d.calcular(mes_nome)
    fig_scatter, titulo_scatter = d.graf_scatter(sono)
    figs = {
        "g-tendencia": d.graf_tendencia(ativ),
        "g-intensidade": d.graf_intensidade(ativ),
        "g-semana": d.graf_passos_semana(ativ),
        "g-hora": d.graf_passos_hora(h),
        "g-calorias": d.graf_calorias_faixa(ativ),
        "g-bullet": d.graf_bullet(k),
        "g-dist": d.graf_distribuicao_sono(sono, k),
        "g-sono-semana": d.graf_sono_semana(sono),
        "g-scatter": fig_scatter,
    }
    if k["noites"]:
        bullet_sub = (f"Tempo na cama: {num(k['horas_cama'], 1)}h por noite · "
                      f"eficiência {pct(k['eficiencia'], 1)}")
    else:
        bullet_sub = "Sem noites registradas"
    return {
        "textos": {
            "subtitulo": (f"Dados diários e por hora · {d.PERIODO} · filtro: {mes_nome} · "
                          f"{num(k['dias'])} dias com uso de {k['usuarias']} usuárias"),
            "bullet-sub": bullet_sub,
            "dist-sub": f"Em ciano: 7h ou mais ({pct(k['pct_7h'])} das noites)",
            "scatter-titulo": titulo_scatter,
        },
        "html": {
            "kpis-atividade": "".join([
                kpi("Passos por dia", num(k["passos"]), CIANO),
                kpi("Distância por dia (km)", num(k["dist"], 1), AMARELO),
                kpi("Calorias por dia", num(k["cal"]), LARANJA),
                kpi("Minutos muito ativos por dia", num(k["muito_ativos"]), VERDE),
                kpi("Horas sedentárias por dia", num(k["sedentarias"], 1), VIOLETA),
                kpi("Dias com 10 mil+ passos", pct(k["pct_10k"]), ROSA, anel=k["pct_10k"]),
            ]),
            "kpis-sono": "".join([
                kpi("Noites com 7h ou mais", pct(k["pct_7h"]), CIANO, anel=k["pct_7h"]),
                kpi("Noites registradas", num(k["noites"]), AMARELO),
                kpi("Usuárias com sono registrado", num(k["usuarias_sono"]), VERDE),
                kpi("Cobertura do sono (% dos dias)", pct(k["cobertura"]), ROSA,
                    anel=k["cobertura"]),
            ]),
        },
        "figs": {gid: json.loads(pio.to_json(f, validate=False)) for gid, f in figs.items()},
    }


def gerar():
    dados = {mes: estado(mes) for mes in d.MESES}
    logo = base64.b64encode((d.PASTA / "assets" / "logo_pulso.png").read_bytes()).decode()
    filtros = "".join(
        f'<label><input type="radio" name="mes" value="{m}"{" checked" if m == "Todos" else ""}>{m}</label>'
        for m in d.MESES)

    corpo = f"""
<div class="app">
  <div class="sidebar">
    <img class="logo" src="data:image/png;base64,{logo}" alt="Pulso · Atividade e Sono">
    <div class="side-label">FILTRO · MÊS</div>
    <div class="filtro">{filtros}</div>
    <div class="side-text">O painel inteiro recalcula. Sempre considera todas as usuárias e exclui dias com 0 passos.</div>
    <div class="side-label">PERÍODO</div>
    <div class="side-text">{d.PERIODO}</div>
    <div class="side-label">FONTE</div>
    <div class="side-text">FitBit Fitness Tracker Data (Furberg et al., Zenodo / Kaggle)</div>
  </div>
  <div class="main">
    <div class="breadcrumb">DASHBOARD / FITBIT</div>
    <h1>Atividade e Sono de {d.N_USUARIAS} Usuárias</h1>
    <div id="subtitulo" class="subtitulo"></div>

    <div class="secao" style="color:{CIANO}">ATIVIDADE</div>
    <div id="kpis-atividade" class="grid kpis-6"></div>
    <div class="grid g-2" style="margin-top:16px">
      {card("Passos médios por dia", "g-tendencia", "Média entre as usuárias · linha pontilhada = 10 mil passos")}
      {card("Como o dia se divide", "g-intensidade", "Minutos médios por intensidade")}
    </div>
    <div class="grid g-3" style="margin-top:16px">
      {card("Passos médios por dia da semana", "g-semana")}
      {card("Passos médios por hora do dia", "g-hora", "Cor mais clara = mais passos")}
      {card("Calorias médias por faixa de passos do dia", "g-calorias", "n = dias em cada faixa")}
    </div>

    <div class="secao" style="color:{ROSA}">SONO</div>
    <div id="kpis-sono" class="grid kpis-sono"></div>
    <div class="card" style="margin-top:16px">
      <div class="card-titulo">Noite média</div>
      <div id="bullet-sub" class="card-sub"></div>
      <div id="g-bullet" class="grafico"></div>
      {legenda([("Dormindo", CIANO), ("Na cama sem dormir", ROSA), ("Referência 7h (pontilhado)", TEXTO_3)])}
    </div>
    <div class="grid g-2i" style="margin-top:16px">
      <div class="card">
        <div class="card-titulo">Distribuição das noites por horas dormidas</div>
        <div id="dist-sub" class="card-sub"></div>
        <div id="g-dist" class="grafico"></div>
        {legenda([("Menos de 7h", VIOLETA), ("7h ou mais", CIANO)])}
      </div>
      {card("Horas de sono por dia da semana", "g-sono-semana", "Ponto = uma noite · traço amarelo = média · tracejado = 7h")}
    </div>
    <div class="card" style="margin-top:16px">
      <div id="scatter-titulo" class="card-titulo"></div>
      <div class="card-sub">Cada ponto = uma noite · linha = tendência linear · associação, não causa</div>
      <div id="g-scatter" class="grafico"></div>
    </div>
  </div>
</div>
"""

    script = f"""
const DADOS = {json.dumps(dados, ensure_ascii=False)};
const GRAFICOS = {json.dumps(GRAFICOS)};
const CONFIG = {{displayModeBar: false, responsive: true}};

function mostrar(mes) {{
  const e = DADOS[mes];
  for (const [id, t] of Object.entries(e.textos)) document.getElementById(id).textContent = t;
  for (const [id, h] of Object.entries(e.html)) document.getElementById(id).innerHTML = h;
  for (const id of GRAFICOS) Plotly.react(id, e.figs[id].data, e.figs[id].layout, CONFIG);
}}

document.querySelectorAll('input[name="mes"]').forEach(r =>
  r.addEventListener('change', () => mostrar(r.value)));
mostrar('Todos');
"""

    pagina = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pulso · Dashboard Fitbit</title>
<style>{d.CSS}</style>
<script>{get_plotlyjs()}</script>
</head>
<body>
{corpo}
<script>{script}</script>
</body>
</html>
"""
    SAIDA.write_text(pagina, encoding="utf-8")
    print(f"Gerado: {SAIDA} ({SAIDA.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    gerar()
