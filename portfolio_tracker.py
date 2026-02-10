import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

# Configuration de la page
st.set_page_config(page_title="Suivi Portfolio ETF & SCPI", layout="wide")

# Fichier de sauvegarde
SAVE_FILE = "portfolio_data.json"

# Fonctions de sauvegarde et chargement
def load_portfolio_data():
    """Charge les données sauvegardées ou retourne les valeurs par défaut"""
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('etf', "IWDA.AS,5000\nVWCE.DE,3000\nCW8.PA,2000"), \
                       data.get('scpi', "Corum Origin,4000\nPrimovie,3000\nEpargne Pierre,2000")
        except:
            pass
    # Valeurs par défaut si pas de fichier
    return "IWDA.AS,5000\nVWCE.DE,3000\nCW8.PA,2000", \
           "Corum Origin,4000\nPrimovie,3000\nEpargne Pierre,2000"

def save_portfolio_data(etf_data, scpi_data):
    """Sauvegarde les données du portfolio"""
    data = {
        'etf': etf_data,
        'scpi': scpi_data,
        'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

st.title("📊 Suivi de Portfolio - ETF & SCPI")

# Sidebar pour la configuration
st.sidebar.header("Configuration du Portfolio")

# Charger les données sauvegardées
default_etf, default_scpi = load_portfolio_data()

# Section ETF
st.sidebar.subheader("ETF")
etf_input = st.sidebar.text_area(
    "ETF (format: Ticker,Montant par ligne)",
    value=default_etf,
    height=100
)

# Section SCPI
st.sidebar.subheader("SCPI")
scpi_input = st.sidebar.text_area(
    "SCPI (format: Nom,Montant par ligne)",
    value=default_scpi,
    height=100
)

# Période historique pour les ETF
period_options = {
    "1 mois": "1mo",
    "3 mois": "3mo",
    "6 mois": "6mo",
    "1 an": "1y",
    "2 ans": "2y",
    "5 ans": "5y"
}
selected_period = st.sidebar.selectbox("Période historique", list(period_options.keys()), index=3)

# Boutons d'action
col_save, col_refresh = st.sidebar.columns(2)

with col_save:
    if st.button("💾 Sauvegarder", use_container_width=True):
        save_portfolio_data(etf_input, scpi_input)
        st.success("✅ Sauvegardé !")

with col_refresh:
    refresh = st.button("🔄 Actualiser", use_container_width=True)

# Fonction pour parser les données
def parse_input(input_text):
    data = {}
    for line in input_text.strip().split('\n'):
        line = line.strip()  # Nettoyer les espaces
        if line and ',' in line:  # Ignorer les lignes vides
            parts = line.split(',')
            if len(parts) == 2:  # S'assurer qu'il y a bien 2 éléments
                name, amount = parts
                try:
                    data[name.strip()] = float(amount.strip())
                except ValueError:
                    pass  # Ignorer les lignes avec des erreurs de format
    return data

# Parser les données
etf_data = parse_input(etf_input)
scpi_data = parse_input(scpi_input)

# Créer deux colonnes principales
col1, col2 = st.columns(2)

# --- GRAPHIQUE EN CAMEMBERT ---
with col1:
    st.subheader("🥧 Allocation d'Actifs")
    
    # Combiner ETF et SCPI pour l'allocation
    all_assets = {}
    
    # Ajouter les ETF
    for ticker, amount in etf_data.items():
        all_assets[f"ETF: {ticker}"] = amount
    
    # Ajouter les SCPI
    for name, amount in scpi_data.items():
        all_assets[f"SCPI: {name}"] = amount
    
    if all_assets:
        df_allocation = pd.DataFrame({
            'Actif': list(all_assets.keys()),
            'Montant': list(all_assets.values())
        })
        
        # Calculer les pourcentages
        total = df_allocation['Montant'].sum()
        df_allocation['Pourcentage'] = (df_allocation['Montant'] / total * 100).round(2)
        
        # Créer le graphique en camembert
        fig_pie = px.pie(
            df_allocation,
            values='Montant',
            names='Actif',
            title=f'Allocation Totale: {total:,.0f} €',
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig_pie.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Montant: %{value:,.0f} €<br>Pourcentage: %{percent}<extra></extra>'
        )
        
        st.plotly_chart(fig_pie, width="stretch")
        
        # Tableau détaillé
        st.dataframe(
            df_allocation.style.format({
                'Montant': '{:,.0f} €',
                'Pourcentage': '{:.2f}%'
            }),
            hide_index=True,
            width="stretch"
        )
    else:
        st.warning("Aucune donnée d'allocation disponible")

# --- PERFORMANCE HISTORIQUE DES ETF ---
with col2:
    st.subheader("📈 Performance Historique des ETF")
    
    if etf_data:
        try:
            # Télécharger les données historiques
            fig_line = go.Figure()
            
            for ticker in etf_data.keys():
                try:
                    # Télécharger les données
                    data = yf.download(
                        ticker,
                        period=period_options[selected_period],
                        progress=False
                    )
                    
                    if not data.empty:
                        # Gérer le format multi-index de yfinance
                        if isinstance(data.columns, pd.MultiIndex):
                            # Nouveau format avec MultiIndex
                            close_prices = data['Close'][ticker] if ticker in data['Close'].columns else data['Close'].iloc[:, 0]
                        else:
                            # Ancien format simple
                            close_prices = data['Close']
                        
                        # Normaliser à 100 pour comparer les performances
                        normalized = (close_prices / close_prices.iloc[0] * 100)
                        
                        fig_line.add_trace(go.Scatter(
                            x=data.index,
                            y=normalized,
                            mode='lines',
                            name=ticker,
                            hovertemplate='<b>' + ticker + '</b><br>Date: %{x}<br>Performance: %{y:.2f}<extra></extra>'
                        ))
                except Exception as e:
                    st.warning(f"Erreur lors du téléchargement de {ticker}: {str(e)}")
            
            if fig_line.data:
                fig_line.update_layout(
                    title=f'Performance Normalisée (Base 100) - {selected_period}',
                    xaxis_title='Date',
                    yaxis_title='Performance (Base 100)',
                    hovermode='x unified',
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    )
                )
                
                st.plotly_chart(fig_line, width="stretch")
                
                # Calculer et afficher les statistiques de performance
                st.subheader("📊 Statistiques de Performance")
                
                stats_data = []
                for ticker in etf_data.keys():
                    try:
                        data = yf.download(
                            ticker,
                            period=period_options[selected_period],
                            progress=False
                        )
                        
                        if not data.empty:
                            # Gérer le format multi-index de yfinance
                            if isinstance(data.columns, pd.MultiIndex):
                                close_prices = data['Close'][ticker] if ticker in data['Close'].columns else data['Close'].iloc[:, 0]
                            else:
                                close_prices = data['Close']
                            
                            performance = ((close_prices.iloc[-1] / close_prices.iloc[0]) - 1) * 100
                            stats_data.append({
                                'ETF': ticker,
                                'Performance': f"{performance:.2f}%",
                                'Prix Actuel': f"{close_prices.iloc[-1]:.2f} €"
                            })
                    except:
                        pass
                
                if stats_data:
                    df_stats = pd.DataFrame(stats_data)
                    st.dataframe(df_stats, hide_index=True, width="stretch")
            else:
                st.error("Impossible de charger les données des ETF. Vérifiez les tickers.")
                
        except Exception as e:
            st.error(f"Erreur lors du chargement des données: {str(e)}")
    else:
        st.warning("Aucun ETF configuré")

# --- RÉSUMÉ GLOBAL ---
st.divider()
st.subheader("💼 Résumé Global")

col_etf, col_scpi, col_total = st.columns(3)

total_etf = sum(etf_data.values())
total_scpi = sum(scpi_data.values())
total_portfolio = total_etf + total_scpi

with col_etf:
    st.metric("Total ETF", f"{total_etf:,.0f} €")

with col_scpi:
    st.metric("Total SCPI", f"{total_scpi:,.0f} €")

with col_total:
    st.metric("Total Portfolio", f"{total_portfolio:,.0f} €")

# --- GRAPHIQUE ETF vs SCPI ---
if total_portfolio > 0:
    st.divider()
    st.subheader("⚖️ Répartition Bourse (ETF) vs Immobilier (SCPI)")
    
    col_graph, col_stats = st.columns([2, 1])
    
    with col_graph:
        # Données pour le graphique
        df_repartition = pd.DataFrame({
            'Catégorie': ['ETF (Bourse)', 'SCPI (Immobilier)'],
            'Montant': [total_etf, total_scpi]
        })
        
        # Calculer les pourcentages
        df_repartition['Pourcentage'] = (df_repartition['Montant'] / total_portfolio * 100).round(2)
        
        # Créer le graphique en camembert
        fig_categories = px.pie(
            df_repartition,
            values='Montant',
            names='Catégorie',
            title='Allocation par Type d\'Actif',
            color='Catégorie',
            color_discrete_map={
                'ETF (Bourse)': '#636EFA',
                'SCPI (Immobilier)': '#EF553B'
            },
            hole=0.4
        )
        
        fig_categories.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont_size=14,
            hovertemplate='<b>%{label}</b><br>Montant: %{value:,.0f} €<br>Pourcentage: %{percent}<extra></extra>'
        )
        
        st.plotly_chart(fig_categories, width="stretch")
    
    with col_stats:
        st.markdown("### 📊 Détails")
        
        # Pourcentages
        pct_etf = (total_etf / total_portfolio * 100) if total_portfolio > 0 else 0
        pct_scpi = (total_scpi / total_portfolio * 100) if total_portfolio > 0 else 0
        
        st.metric(
            "Part ETF",
            f"{pct_etf:.1f}%",
            f"{total_etf:,.0f} €"
        )
        
        st.metric(
            "Part SCPI",
            f"{pct_scpi:.1f}%",
            f"{total_scpi:,.0f} €"
        )
        
        # Recommandation simple
        st.markdown("---")
        st.markdown("#### 💡 Diversification")
        
        if pct_etf > 80:
            st.info("🔵 Portfolio fortement orienté bourse")
        elif pct_scpi > 80:
            st.info("🔴 Portfolio fortement orienté immobilier")
        elif 40 <= pct_etf <= 60:
            st.success("✅ Bonne diversification équilibrée")
        else:
            st.info("ℹ️ Portfolio mixte")

# Note sur les SCPI
st.info("ℹ️ **Note**: Les SCPI ne sont pas cotées en bourse. Les montants affichés sont vos investissements. Pour le suivi détaillé de leur performance, consultez les bulletins trimestriels de vos SCPI.")

# Footer
st.divider()
st.caption("📅 Dernière actualisation: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
st.caption("Les données ETF proviennent de Yahoo Finance. Les performances passées ne préjugent pas des performances futures.")
