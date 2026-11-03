"""
Dashboard Fitbit — Atividade e Sono
Recria em Python (Dash + Plotly) o dashboard do Excel "fitbit_dashboard_.xlsx".

Como rodar (no terminal do VS Code):
    pip install dash plotly pandas openpyxl
    python dashboard_fitbit.py
Depois abra http://127.0.0.1:8050 no navegador.

Coloque o arquivo Excel na mesma pasta deste script (ou ajuste ARQUIVO_EXCEL).
As regras de cálculo são as mesmas da aba "Cálculos" do Excel:
  • atividade: exclui dias com 0 passos;
  • sono: só noites com MinutesAsleep > 0;
  • cobertura do sono: noites com sono ÷ todos os dias do filtro;
  • gráfico por hora: usa a aba "Por Hora" sem filtro de passos.
"""

from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

# ----------------------------------------------------------------------------
# 1. Configuração
# ----------------------------------------------------------------------------
PASTA = Path(__file__).parent
ARQUIVO_EXCEL = PASTA / "fitbit_dashboard_base.xlsx"
CACHE = PASTA / ".cache_fitbit.pkl"  # acelera as próximas execuções

MESES = {"Todos": None, "Março": 3, "Abril": 4, "Maio": 5}
DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

# Paleta neon (validada para fundo escuro: ordem fixa, cada cor tem um papel)
CIANO = "#22d3ee"
AMARELO = "#facc15"
ROSA = "#f0569a"
VIOLETA = "#8b7cf6"
VERDE = "#4ade80"
LARANJA = "#fb923c"
TEXTO = "#e9e4ff"
TEXTO_2 = "#b8acd9"
TEXTO_3 = "#8a7fb0"
GRADE = "rgba(255,255,255,0.07)"
CARD_BG = "#211040"


# ----------------------------------------------------------------------------
# 2. Carregamento dos dados
# ----------------------------------------------------------------------------
def carregar_dados():
    """Lê as abas 'Diário' e 'Por Hora'. Usa cache se o Excel não mudou."""
    mtime = ARQUIVO_EXCEL.stat().st_mtime
    if CACHE.exists():
        with open(CACHE, "rb") as f:
            cache = pickle.load(f)
        if cache.get("mtime") == mtime:
            return cache["diario"], cache["hora"]

    colunas_diario = [
        "Id", "ActivityDate", "TotalSteps", "TotalDistance",
        "VeryActiveMinutes", "FairlyActiveMinutes", "LightlyActiveMinutes",
        "SedentaryMinutes", "Calories", "MinutesAsleep",
        "TotalMinutesInBed", "SleepEfficiencyPct",
    ]
    diario = pd.read_excel(ARQUIVO_EXCEL, sheet_name="Diário", usecols=colunas_diario)
    diario["ActivityDate"] = pd.to_datetime(diario["ActivityDate"])
    # Recalculadas aqui (no Excel são fórmulas =MONTH e =WEEKDAY(...;2))
    diario["Mes"] = diario["ActivityDate"].dt.month
    diario["DiaSemana"] = diario["ActivityDate"].dt.dayofweek + 1  # 1 = Seg
    diario["MinutesAsleep"] = diario["MinutesAsleep"].fillna(0)

    hora = pd.read_excel(
        ARQUIVO_EXCEL, sheet_name="Por Hora", usecols=["Id", "ActivityHour", "StepTotal"]
    )
    hora["ActivityHour"] = pd.to_datetime(hora["ActivityHour"])
    hora["Hora"] = hora["ActivityHour"].dt.hour
    hora["Mes"] = hora["ActivityHour"].dt.month

    with open(CACHE, "wb") as f:
        pickle.dump({"mtime": mtime, "diario": diario, "hora": hora}, f)
    return diario, hora


DIARIO, HORA = carregar_dados()
PERIODO = f"{DIARIO['ActivityDate'].min():%d/%m/%Y} a {DIARIO['ActivityDate'].max():%d/%m/%Y}"
N_USUARIAS = DIARIO["Id"].nunique()


# ----------------------------------------------------------------------------
# 3. Formatação no padrão brasileiro
# ----------------------------------------------------------------------------
def num(valor, casas=0):
    if valor is None or pd.isna(valor):
        return "–"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(valor, casas=0):
    return "–" if valor is None or pd.isna(valor) else num(valor * 100, casas) + "%"


# ----------------------------------------------------------------------------
# 4. Cálculos (equivalentes à aba "Cálculos")
# ----------------------------------------------------------------------------
def calcular(mes_nome):
    mes = MESES[mes_nome]
    d = DIARIO if mes is None else DIARIO[DIARIO["Mes"] == mes]
    h = HORA if mes is None else HORA[HORA["Mes"] == mes]

    ativ = d[d["TotalSteps"] >= 1]        # exclui dias sem uso
    sono = d[d["MinutesAsleep"] > 0]      # noites com sono registrado

    k = {
        "passos": ativ["TotalSteps"].mean(),
        "dist": ativ["TotalDistance"].mean(),
        "cal": ativ["Calories"].mean(),
        "muito_ativos": ativ["VeryActiveMinutes"].mean(),
        "sedentarias": ativ["SedentaryMinutes"].mean() / 60,
        "pct_10k": (ativ["TotalSteps"] >= 10000).mean() if len(ativ) else np.nan,
        "dias": len(ativ),
        "usuarias": ativ["Id"].nunique(),
        "horas_sono": sono["MinutesAsleep"].mean() / 60,
        "eficiencia": sono["SleepEfficiencyPct"].mean() / 100,
        "horas_cama": sono["TotalMinutesInBed"].mean() / 60,
        "pct_7h": (sono["MinutesAsleep"] >= 420).mean() if len(sono) else np.nan,
        "noites": len(sono),
        "min_acordada": sono["TotalMinutesInBed"].mean() - sono["MinutesAsleep"].mean(),
        "usuarias_sono": sono["Id"].nunique(),
        "cobertura": len(sono) / len(d) if len(d) else np.nan,
    }
    return d, ativ, sono, h, k


# ----------------------------------------------------------------------------
# 5. Estilo base dos gráficos
# ----------------------------------------------------------------------------
def layout_base(fig, altura=300, **kwargs):
    kwargs.setdefault("margin", dict(l=8, r=8, t=8, b=8))
    kwargs.setdefault("bargap", 0.25)
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=TEXTO_2, size=12),
        showlegend=False,
        hoverlabel=dict(bgcolor="#1a0b36", bordercolor="#3d2a6b",
                        font=dict(color=TEXTO, size=12)),
        separators=",.",
        **kwargs,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRADE, tickcolor=GRADE, zeroline=False)
    fig.update_yaxes(gridcolor=GRADE, zeroline=False, linecolor="rgba(0,0,0,0)")
    return fig


def sem_dados(altura=300):
    fig = go.Figure()
    fig.add_annotation(text="Sem dados para o filtro", showarrow=False,
                       font=dict(color=TEXTO_3, size=13))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return layout_base(fig, altura)


# --- Atividade ---------------------------------------------------------------
def graf_tendencia(ativ):
    s = ativ.groupby("ActivityDate")["TotalSteps"].mean()
    if s.empty:
        return sem_dados()
    fig = go.Figure(go.Scatter(
        x=s.index, y=s.values, mode="lines",
        line=dict(color=ROSA, width=2, shape="spline", smoothing=0.6),
        fill="tozeroy",
        fillgradient=dict(type="vertical",
                          colorscale=[[0, "rgba(240,86,154,0)"], [1, "rgba(240,86,154,0.35)"]]),
        hovertemplate="%{x|%d/%m/%Y}<br><b>%{y:,.0f} passos</b><extra></extra>",
    ))
    fig.add_hline(y=10000, line=dict(color=TEXTO_3, width=1, dash="dot"),
                  annotation_text="10 mil", annotation_position="top left",
                  annotation_font=dict(color=TEXTO_3, size=11))
    layout_base(fig)
    fig.update_xaxes(tickformat="%d/%m")
    fig.update_yaxes(tickformat=",.0f", rangemode="tozero")
    return fig


def graf_passos_semana(ativ):
    s = ativ.groupby("DiaSemana")["TotalSteps"].mean().reindex(range(1, 8))
    fig = go.Figure(go.Bar(
        x=DIAS, y=s.values, marker=dict(color=CIANO, cornerradius=4),
        text=[num(v) for v in s.values], textposition="outside",
        textfont=dict(color=TEXTO, size=11), cliponaxis=False,
        hovertemplate="%{x}<br><b>%{y:,.0f} passos</b><extra></extra>",
    ))
    layout_base(fig)
    fig.update_yaxes(tickformat=",.0f")
    return fig


def graf_passos_hora(h):
    s = h.groupby("Hora")["StepTotal"].mean().reindex(range(24))
    if s.isna().all():
        return sem_dados()
    fig = go.Figure(go.Bar(
        x=[f"{i:02d}h" for i in range(24)], y=s.values,
        # cor sequencial (um tom só): mais claro = mais passos
        marker=dict(color=s.values, cornerradius=3,
                    colorscale=[[0, "#1e3a5f"], [0.5, "#0ea5c6"], [1, "#a5f3fc"]]),
        hovertemplate="%{x}<br><b>%{y:,.0f} passos</b><extra></extra>",
    ))
    layout_base(fig, bargap=0.15)
    fig.update_xaxes(tickvals=[f"{i:02d}h" for i in range(0, 24, 3)])
    fig.update_yaxes(tickformat=",.0f")
    return fig


def graf_intensidade(ativ):
    cols = {"Muito ativa": "VeryActiveMinutes", "Moderada": "FairlyActiveMinutes",
            "Leve": "LightlyActiveMinutes", "Sedentária": "SedentaryMinutes"}
    vals = [ativ[c].mean() for c in cols.values()]
    if any(pd.isna(vals)):
        return sem_dados()
    total = sum(vals)
    fig = go.Figure(go.Pie(
        labels=list(cols), values=vals, hole=0.68, sort=False, direction="clockwise",
        marker=dict(colors=[CIANO, AMARELO, ROSA, VIOLETA], line=dict(color=CARD_BG, width=2)),
        texttemplate="%{label}<br>%{percent:.0%}", textposition="outside",
        textfont=dict(color=TEXTO, size=11),
        hovertemplate="%{label}<br><b>%{value:,.0f} min/dia</b> (%{percent:.1%})<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{num(total / 60, 1)}h</b><br><span style='font-size:11px'>monitoradas/dia</span>",
                       showarrow=False, font=dict(color=TEXTO, size=18))
    return layout_base(fig, margin=dict(l=30, r=30, t=30, b=30))


def graf_calorias_faixa(ativ):
    faixas = ["< 5 mil", "5–7,5 mil", "7,5–10 mil", "10–12,5 mil", "≥ 12,5 mil"]
    cortes = [0, 5000, 7500, 10000, 12500, np.inf]
    grupo = pd.cut(ativ["TotalSteps"], cortes, right=False, labels=faixas)
    s = ativ.groupby(grupo, observed=False)["Calories"].mean()
    n = ativ.groupby(grupo, observed=False).size()
    fig = go.Figure(go.Bar(
        x=[f"{f.replace(' mil', '')}<br><span style='font-size:10px;color:{TEXTO_3}'>n={c}</span>" for f, c in zip(faixas, n)],
        y=s.values, marker=dict(color=LARANJA, cornerradius=4),
        text=[num(v) for v in s.values], textposition="outside",
        textfont=dict(color=TEXTO, size=11), cliponaxis=False,
        customdata=n.values,
        hovertemplate="%{x}<br><b>%{y:,.0f} kcal</b> · %{customdata} dias<extra></extra>",
    ))
    layout_base(fig)
    fig.update_xaxes(tickangle=0, title=dict(text="mil passos no dia", font=dict(size=11)))
    fig.update_yaxes(tickformat=",.0f")
    return fig


# --- Sono --------------------------------------------------------------------
def graf_bullet(k):
    dormindo = k["horas_sono"] if not pd.isna(k["horas_sono"]) else 0
    acordada = (k["horas_cama"] - k["horas_sono"]) if not pd.isna(k["horas_cama"]) else 0
    fig = go.Figure()
    fig.add_bar(y=[""], x=[dormindo], orientation="h", name="Dormindo",
                marker=dict(color=CIANO, line=dict(width=0)),
                text=f"Dormindo {num(dormindo, 1)}h", textposition="inside",
                insidetextanchor="start", textfont=dict(color="#0b0420", size=13),
                hovertemplate="Dormindo: <b>%{x:.1f}h</b><extra></extra>")
    fig.add_bar(y=[""], x=[acordada], orientation="h", name="Na cama sem dormir",
                marker=dict(color=ROSA, line=dict(width=0)),
                hovertemplate="Na cama sem dormir: <b>%{x:.2f}h</b><extra></extra>")
    fig.add_annotation(x=dormindo + acordada, y=0, xanchor="left", xshift=8, showarrow=False,
                       text=f"{num(k['min_acordada'])} min acordada",
                       font=dict(color=ROSA, size=12))
    fig.add_vline(x=7, line=dict(color=TEXTO_3, width=1, dash="dot"))
    layout_base(fig, altura=90, barmode="stack", bargap=0.35,
                margin=dict(l=8, r=8, t=4, b=24))
    fig.update_xaxes(range=[0, 10], dtick=1, ticksuffix="h", showgrid=True, gridcolor=GRADE)
    fig.update_yaxes(showgrid=False)
    return fig


def graf_distribuicao_sono(sono, k):
    faixas = ["< 5h", "5–6h", "6–7h", "7–8h", "8–9h", "≥ 9h"]
    cortes = [0, 300, 360, 420, 480, 540, np.inf]
    grupo = pd.cut(sono["MinutesAsleep"], cortes, right=False, labels=faixas)
    share = grupo.value_counts(normalize=True).reindex(faixas)
    cores = [VIOLETA] * 3 + [CIANO] * 3  # ciano = 7h ou mais
    fig = go.Figure(go.Bar(
        x=faixas, y=share.values, marker=dict(color=cores, cornerradius=4),
        text=[pct(v) for v in share.values], textposition="outside",
        textfont=dict(color=TEXTO, size=11), cliponaxis=False,
        hovertemplate="%{x}<br><b>%{y:.1%}</b> das noites<extra></extra>",
    ))
    layout_base(fig, bargap=0.06)
    fig.update_yaxes(tickformat=".0%")
    return fig


def graf_sono_semana(sono):
    if sono.empty:
        return sem_dados()
    s = sono.reset_index(drop=True)
    horas = s["MinutesAsleep"] / 60
    # deslocamento horizontal determinístico (mesma lógica do Excel: sequência áurea)
    jitter = (np.mod(np.arange(1, len(s) + 1) * 0.618034, 1) - 0.5) * 0.5
    x = s["DiaSemana"] - 1 + jitter
    medias = (s.assign(h=horas).groupby("DiaSemana")["h"].mean().reindex(range(1, 8)))
    n = s.groupby("DiaSemana").size().reindex(range(1, 8), fill_value=0)

    fig = go.Figure()
    fig.add_scatter(x=x, y=horas, mode="markers",
                    marker=dict(size=7, color=VIOLETA, opacity=0.55,
                                line=dict(color=CARD_BG, width=1)),
                    customdata=s["ActivityDate"].dt.strftime("%d/%m/%Y"),
                    hovertemplate="%{customdata}<br><b>%{y:.1f}h</b> de sono<extra></extra>")
    for i, m in enumerate(medias.values):  # traço = média do dia
        if not pd.isna(m):
            fig.add_shape(type="line", x0=i - 0.32, x1=i + 0.32, y0=m, y1=m,
                          line=dict(color=AMARELO, width=3))
    fig.add_scatter(x=list(range(7)), y=medias.values, mode="markers",
                    marker=dict(size=18, color="rgba(0,0,0,0)"),
                    hovertemplate="Média: <b>%{y:.1f}h</b><extra></extra>")
    fig.add_hline(y=7, line=dict(color=CIANO, width=1, dash="dash"),
                  annotation_text="7h", annotation_position="right",
                  annotation_font=dict(color=CIANO, size=11))
    layout_base(fig, altura=320)
    fig.update_xaxes(tickvals=list(range(7)),
                     ticktext=[f"{d}<br><span style='font-size:10px;color:{TEXTO_3}'>n={c}</span>"
                               for d, c in zip(DIAS, n.values)],
                     range=[-0.6, 6.6])
    fig.update_yaxes(ticksuffix="h", rangemode="tozero")
    return fig


def graf_scatter(sono):
    if len(sono) < 3:
        return sem_dados(320), "Sono × tempo sedentário por noite"
    x = sono["SedentaryMinutes"] / 60
    y = sono["MinutesAsleep"] / 60
    r = np.corrcoef(x, y)[0, 1]
    a, b = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 50)
    fig = go.Figure()
    fig.add_scatter(x=x, y=y, mode="markers",
                    marker=dict(size=8, color=CIANO, opacity=0.6,
                                line=dict(color=CARD_BG, width=1)),
                    hovertemplate="Sedentária: %{x:.1f}h<br>Sono: <b>%{y:.1f}h</b><extra></extra>")
    fig.add_scatter(x=xs, y=a * xs + b, mode="lines", line=dict(color=ROSA, width=2),
                    hovertemplate=f"Tendência: {num(a, 2)}h de sono por h sedentária<extra></extra>")
    layout_base(fig, altura=320)
    fig.update_xaxes(title=dict(text="Horas sedentárias no dia", font=dict(size=11)),
                     ticksuffix="h", showgrid=True, gridcolor=GRADE)
    fig.update_yaxes(title=dict(text="Horas dormidas", font=dict(size=11)), ticksuffix="h")
    titulo = (f"Sono × tempo sedentário por noite · n={len(sono)} noites, "
              f"{sono['Id'].nunique()} usuárias · r = {num(r, 2)}")
    return fig, titulo


# ----------------------------------------------------------------------------
# 6. Componentes visuais (cards)
# ----------------------------------------------------------------------------
def kpi(titulo, valor, cor, anel=None):
    """Card de KPI. Se 'anel' (0–1) for informado, desenha um anel de progresso."""
    conteudo = [html.Div(titulo, className="kpi-titulo"),
                html.Div(valor, className="kpi-valor", style={"color": cor})]
    if anel is not None and not pd.isna(anel):
        graus = anel * 360
        return html.Div(className="card kpi kpi-anel", children=[
            html.Div(className="anel", style={
                "background": f"conic-gradient({cor} {graus}deg, rgba(255,255,255,0.08) 0)"},
                children=html.Div(className="anel-miolo", children=pct(anel))),
            html.Div(conteudo, className="kpi-texto"),
        ])
    return html.Div(conteudo, className="card kpi")


def card_grafico(titulo, grafico_id, subtitulo=None, classe=""):
    filhos = [html.Div(titulo, className="card-titulo", id=f"{grafico_id}-titulo")]
    if subtitulo:
        filhos.append(html.Div(subtitulo, className="card-sub", id=f"{grafico_id}-sub"))
    filhos.append(dcc.Graph(id=grafico_id, config={"displayModeBar": False}))
    return html.Div(filhos, className=f"card {classe}")


# ----------------------------------------------------------------------------
# 7. App
# ----------------------------------------------------------------------------
app = Dash(__name__, title="Dashboard Fitbit")
server = app.server  # usado pelo gunicorn na publicação (Render)

CSS = """
* { box-sizing: border-box; }
html {
  min-height: 100%;
  background: linear-gradient(135deg, #0d0521 0%, #1f0a45 40%, #3a0d62 75%, #4c1170 100%) fixed;
  background-color: #1f0a45;
}
body {
  margin: 0; min-height: 100vh; color: #e9e4ff;
  font-family: Inter, 'Segoe UI', sans-serif;
  background: transparent;
}
.app { display: flex; min-height: 100vh; }
.sidebar {
  width: 240px; flex-shrink: 0; padding: 28px 20px;
  background: rgba(10, 3, 28, 0.55); border-right: 1px solid rgba(255,255,255,0.06);
  position: sticky; top: 0; height: 100vh;
}
.logo { display: block; width: 175px; height: auto; margin-bottom: 24px; }
.sidebar .logo + .side-label { margin-top: 0; }
.side-label { font-size: 11px; letter-spacing: .14em; color: #8a7fb0;
              font-weight: 700; margin: 26px 0 10px; }
.side-text { font-size: 13px; color: #b8acd9; line-height: 1.5; }
.filtro label { display: block; padding: 10px 14px; margin-bottom: 6px; border-radius: 12px;
                cursor: pointer; color: #b8acd9; font-size: 14px; transition: all .15s; }
.filtro label:hover { background: rgba(255,255,255,0.05); color: #fff; }
.filtro label:has(input:checked) { background: rgba(240,86,154,0.16); color: #ff7ab6;
                                   box-shadow: inset 3px 0 0 #f0569a; }
.filtro input { display: none; }
.main { flex: 1; padding: 28px 32px 40px; min-width: 0; }
.breadcrumb { font-size: 12px; letter-spacing: .12em; color: #8a7fb0; font-weight: 700; }
h1 { font-size: 26px; margin: 8px 0 4px; font-weight: 700; }
.subtitulo { color: #b8acd9; font-size: 13px; margin-bottom: 22px; }
.secao { font-size: 13px; letter-spacing: .14em; font-weight: 700; margin: 26px 0 12px;
         display: flex; align-items: center; gap: 10px; }
.secao::after { content: ""; flex: 1; height: 1px; background: rgba(255,255,255,0.08); }
.card {
  background: rgba(33, 16, 64, 0.72);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 20px; padding: 18px 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  backdrop-filter: blur(6px);
}
.grid { display: grid; gap: 16px; }
.kpis-6 { grid-template-columns: repeat(6, minmax(0, 1fr)); }
.kpis-sono { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.g-2 { grid-template-columns: 2fr 1fr; }
.g-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.g-2i { grid-template-columns: 1fr 1fr; }
.kpi { display: flex; flex-direction: column; justify-content: center; min-height: 104px; }
.kpi-titulo { font-size: 12px; color: #b8acd9; margin-bottom: 8px; line-height: 1.3; }
.kpi-valor { font-size: 28px; font-weight: 700; letter-spacing: -.01em; }
.kpi-anel { flex-direction: row; align-items: center; gap: 14px; }
.kpi-anel .kpi-valor { display: none; }
.anel { width: 66px; height: 66px; border-radius: 50%; flex-shrink: 0;
        display: grid; place-items: center; }
.anel-miolo { width: 52px; height: 52px; border-radius: 50%; background: #1d0e3a;
              display: grid; place-items: center; font-size: 14px; font-weight: 700; }
.card-titulo { font-size: 14px; font-weight: 600; color: #e9e4ff; }
.card-sub { font-size: 12px; color: #8a7fb0; margin-top: 3px; }
.legenda { display: flex; gap: 14px; font-size: 12px; color: #b8acd9; margin-top: 6px; }
.legenda span::before { content: ""; display: inline-block; width: 10px; height: 10px;
                        border-radius: 3px; margin-right: 6px; vertical-align: -1px;
                        background: var(--c); }
@media (max-width: 1200px) {
  .kpis-6 { grid-template-columns: repeat(3, 1fr); }
  .g-2, .g-3, .g-2i { grid-template-columns: 1fr; }
}
@media (max-width: 800px) {
  .app { flex-direction: column; }
  .sidebar { width: 100%; height: auto; position: static; }
  .kpis-6, .kpis-sono { grid-template-columns: repeat(2, 1fr); }
  .main { padding: 20px 16px; }
}
"""

app.index_string = app.index_string.replace("</head>", f"<style>{CSS}</style></head>")


def legenda(itens):
    return html.Div([html.Span(t, style={"--c": c}) for t, c in itens], className="legenda")


app.layout = html.Div(className="app", children=[
    # ---------- Barra lateral (filtros, período e fonte) ----------
    html.Div(className="sidebar", children=[
        html.Img(src=app.get_asset_url("logo_pulso.png"), alt="Pulso · Atividade e Sono",
                 className="logo"),
        html.Div("FILTRO · MÊS", className="side-label"),
        dcc.RadioItems(id="filtro-mes", options=list(MESES), value="Todos",
                       className="filtro"),
        html.Div("O painel inteiro recalcula. Sempre considera todas as usuárias "
                 "e exclui dias com 0 passos.", className="side-text"),
        html.Div("PERÍODO", className="side-label"),
        html.Div(PERIODO, className="side-text"),
        html.Div("FONTE", className="side-label"),
        html.Div("FitBit Fitness Tracker Data (Furberg et al., Zenodo / Kaggle)",
                 className="side-text"),
    ]),

    # ---------- Conteúdo ----------
    html.Div(className="main", children=[
        html.Div("DASHBOARD / FITBIT", className="breadcrumb"),
        html.H1(f"Atividade e Sono de {N_USUARIAS} Usuárias"),
        html.Div(id="subtitulo", className="subtitulo"),

        html.Div("ATIVIDADE", className="secao", style={"color": CIANO}),
        html.Div(id="kpis-atividade", className="grid kpis-6"),

        html.Div(className="grid g-2", style={"marginTop": "16px"}, children=[
            card_grafico("Passos médios por dia", "g-tendencia",
                         "Média entre as usuárias · linha pontilhada = 10 mil passos"),
            card_grafico("Como o dia se divide", "g-intensidade",
                         "Minutos médios por intensidade"),
        ]),
        html.Div(className="grid g-3", style={"marginTop": "16px"}, children=[
            card_grafico("Passos médios por dia da semana", "g-semana"),
            card_grafico("Passos médios por hora do dia", "g-hora",
                         "Cor mais clara = mais passos"),
            card_grafico("Calorias médias por faixa de passos do dia", "g-calorias",
                         "n = dias em cada faixa"),
        ]),

        html.Div("SONO", className="secao", style={"color": ROSA}),
        html.Div(id="kpis-sono", className="grid kpis-sono"),
        html.Div(className="card", style={"marginTop": "16px"}, children=[
            html.Div("Noite média", className="card-titulo"),
            html.Div(id="bullet-sub", className="card-sub"),
            dcc.Graph(id="g-bullet", config={"displayModeBar": False}),
            legenda([("Dormindo", CIANO), ("Na cama sem dormir", ROSA),
                     ("Referência 7h (pontilhado)", TEXTO_3)]),
        ]),
        html.Div(className="grid g-2i", style={"marginTop": "16px"}, children=[
            html.Div(className="card", children=[
                html.Div("Distribuição das noites por horas dormidas", className="card-titulo"),
                html.Div(id="dist-sub", className="card-sub"),
                dcc.Graph(id="g-dist", config={"displayModeBar": False}),
                legenda([("Menos de 7h", VIOLETA), ("7h ou mais", CIANO)]),
            ]),
            html.Div(className="card", children=[
                html.Div("Horas de sono por dia da semana", className="card-titulo"),
                html.Div("Ponto = uma noite · traço amarelo = média · tracejado = 7h",
                         className="card-sub"),
                dcc.Graph(id="g-sono-semana", config={"displayModeBar": False}),
            ]),
        ]),
        html.Div(className="card", style={"marginTop": "16px"}, children=[
            html.Div(id="scatter-titulo", className="card-titulo"),
            html.Div("Cada ponto = uma noite · linha = tendência linear · "
                     "associação, não causa", className="card-sub"),
            dcc.Graph(id="g-scatter", config={"displayModeBar": False}),
        ]),
    ]),
])


@app.callback(
    Output("subtitulo", "children"),
    Output("kpis-atividade", "children"),
    Output("g-tendencia", "figure"),
    Output("g-intensidade", "figure"),
    Output("g-semana", "figure"),
    Output("g-hora", "figure"),
    Output("g-calorias", "figure"),
    Output("kpis-sono", "children"),
    Output("bullet-sub", "children"),
    Output("g-bullet", "figure"),
    Output("dist-sub", "children"),
    Output("g-dist", "figure"),
    Output("g-sono-semana", "figure"),
    Output("scatter-titulo", "children"),
    Output("g-scatter", "figure"),
    Input("filtro-mes", "value"),
)
def atualizar(mes_nome):
    d, ativ, sono, h, k = calcular(mes_nome)

    subtitulo = (f"Dados diários e por hora · {PERIODO} · filtro: {mes_nome} · "
                 f"{num(k['dias'])} dias com uso de {k['usuarias']} usuárias")

    kpis_ativ = [
        kpi("Passos por dia", num(k["passos"]), CIANO),
        kpi("Distância por dia (km)", num(k["dist"], 1), AMARELO),
        kpi("Calorias por dia", num(k["cal"]), LARANJA),
        kpi("Minutos muito ativos por dia", num(k["muito_ativos"]), VERDE),
        kpi("Horas sedentárias por dia", num(k["sedentarias"], 1), VIOLETA),
        kpi("Dias com 10 mil+ passos", pct(k["pct_10k"]), ROSA, anel=k["pct_10k"]),
    ]
    kpis_sono = [
        kpi("Noites com 7h ou mais", pct(k["pct_7h"]), CIANO, anel=k["pct_7h"]),
        kpi("Noites registradas", num(k["noites"]), AMARELO),
        kpi("Usuárias com sono registrado", num(k["usuarias_sono"]), VERDE),
        kpi("Cobertura do sono (% dos dias)", pct(k["cobertura"]), ROSA, anel=k["cobertura"]),
    ]

    if k["noites"]:
        bullet_sub = (f"Tempo na cama: {num(k['horas_cama'], 1)}h por noite · "
                      f"eficiência {pct(k['eficiencia'], 1)}")
    else:
        bullet_sub = "Sem noites registradas"
    dist_sub = f"Em ciano: 7h ou mais ({pct(k['pct_7h'])} das noites)"

    fig_scatter, titulo_scatter = graf_scatter(sono)

    return (
        subtitulo, kpis_ativ,
        graf_tendencia(ativ), graf_intensidade(ativ), graf_passos_semana(ativ),
        graf_passos_hora(h), graf_calorias_faixa(ativ),
        kpis_sono, bullet_sub, graf_bullet(k),
        dist_sub, graf_distribuicao_sono(sono, k), graf_sono_semana(sono),
        titulo_scatter, fig_scatter,
    )


if __name__ == "__main__":
    app.run(debug=True)
