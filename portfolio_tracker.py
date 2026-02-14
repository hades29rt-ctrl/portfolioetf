import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os

# Configuration de la page
st.set_page_config(page_title="Suivi Portfolio ETF & SCPI", layout="wide")

# Mot de passe (à configurer dans les secrets Streamlit)
def check_password():
    """Retourne True si le mot de passe est correct"""
    
    def password_entered():
        """Vérifie si le mot de passe entré est correct"""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Ne pas stocker le mot de passe
        else:
            st.session_state["password_correct"] = False

    # Première visite ou mot de passe incorrect
    if "password_correct" not in st.session_state:
        st.title("🔐 Portfolio Tracker")
        st.text_input(
            "Mot de passe", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.info("ℹ️ Entrez le mot de passe pour accéder à l'application")
        return False
    
    # Mot de passe incorrect
    elif not st.session_state["password_correct"]:
        st.title("🔐 Portfolio Tracker")
        st.text_input(
            "Mot de passe", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ Mot de passe incorrect")
        return False
    
    # Mot de passe correct
    else:
        return True

# Fonctions de sauvegarde (utilise les secrets Streamlit pour stocker les données)
def load_portfolio_data():
    """Charge les données du portfolio depuis les secrets"""
    try:
        if "portfolio_data" in st.secrets:
            etf_data = st.secrets["portfolio_data"].get("etf", "IWDA.AS,5000\nCW8.PA,3000")
            scpi_data = st.secrets["portfolio_data"].get("scpi", "Corum Origin,4000\nPrimovie,3000")
            return etf_data, scpi_data
    except:
        pass
    
    # Valeurs par défaut
    return "IWDA.AS,5000\nCW8.PA,3000", "Corum Origin,4000\nPrimovie,3000"

# Fonction pour parser les données
def parse_input(input_text):
    data = {}
    for line in input_text.strip().split('\n'):
        line = line.strip()
        if line and ',' in line:
            parts = line.split(',')
            if len(parts) == 2:
                name, amount = parts
                try:
                    data[name.strip()] = float(amount.strip())
                except ValueError:
                    pass
    return data

def main_app():
    """Application principale"""
    
    st.title("📊 Suivi de Portfolio - ETF & SCPI")
    
    # Bouton de déconnexion
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🚪 Déconnexion"):
            st.session_state["password_correct"] = False
            st.rerun()
    
    # Charger les données sauvegardées
    default_etf, default_scpi = load_portfolio_data()
    
    # Sidebar pour la configuration
    st.sidebar.header("Configuration du Portfolio")
    
    # Initialiser session_state pour les données
    if 'etf_data_text' not in st.session_state:
        st.session_state.etf_data_text = default_etf
    if 'scpi_data_text' not in st.session_state:
        st.session_state.scpi_data_text = default_scpi
    
    # Import Excel
    st.sidebar.subheader("📤 Import Excel")
    uploaded_file = st.sidebar.file_uploader(
        "Importer un fichier Excel",
        type=['xlsx', 'xls'],
        help="Le fichier doit contenir deux feuilles : 'ETF' et 'SCPI'"
    )
    
    if uploaded_file is not None:
        try:
            # Lire le fichier Excel
            xls = pd.ExcelFile(uploaded_file)
            
            # Lire la feuille ETF
            if 'ETF' in xls.sheet_names:
                df_etf = pd.read_excel(uploaded_file, sheet_name='ETF')
                if 'Ticker' in df_etf.columns and 'Montant' in df_etf.columns:
                    etf_lines = []
                    for _, row in df_etf.iterrows():
                        if pd.notna(row['Ticker']) and pd.notna(row['Montant']):
                            etf_lines.append(f"{row['Ticker']},{row['Montant']}")
                    st.session_state.etf_data_text = "\n".join(etf_lines)
                    st.sidebar.success(f"✅ {len(etf_lines)} ETF importés")
                else:
                    st.sidebar.error("❌ La feuille ETF doit avoir les colonnes 'Ticker' et 'Montant'")
            else:
                st.sidebar.warning("⚠️ Feuille 'ETF' non trouvée")
            
            # Lire la feuille SCPI
            if 'SCPI' in xls.sheet_names:
                df_scpi = pd.read_excel(uploaded_file, sheet_name='SCPI')
                if 'Nom' in df_scpi.columns and 'Montant' in df_scpi.columns:
                    scpi_lines = []
                    for _, row in df_scpi.iterrows():
                        if pd.notna(row['Nom']) and pd.notna(row['Montant']):
                            scpi_lines.append(f"{row['Nom']},{row['Montant']}")
                    st.session_state.scpi_data_text = "\n".join(scpi_lines)
                    st.sidebar.success(f"✅ {len(scpi_lines)} SCPI importées")
                else:
                    st.sidebar.error("❌ La feuille SCPI doit avoir les colonnes 'Nom' et 'Montant'")
            else:
                st.sidebar.warning("⚠️ Feuille 'SCPI' non trouvée")
            
            # Bouton pour appliquer les données importées
            if st.sidebar.button("✨ Appliquer les données importées", type="primary"):
                st.rerun()
                
        except Exception as e:
            st.sidebar.error(f"❌ Erreur lors de la lecture du fichier : {str(e)}")
    
    st.sidebar.divider()
    
    # Section ETF
    st.sidebar.subheader("ETF")
    etf_input = st.sidebar.text_area(
        "ETF (format: Ticker,Montant par ligne)",
        value=st.session_state.etf_data_text,
        height=100,
        key="etf_input"
    )
    
    # Section SCPI
    st.sidebar.subheader("SCPI")
    scpi_input = st.sidebar.text_area(
        "SCPI (format: Nom,Montant par ligne)",
        value=st.session_state.scpi_data_text,
        height=100,
        key="scpi_input"
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
    
    # Instructions de sauvegarde
    st.sidebar.divider()
    st.sidebar.info("""
    💾 **Pour sauvegarder vos modifications :**
    
    1. Modifiez vos ETF et SCPI ci-dessus
    2. Allez dans les Settings de l'app Streamlit
    3. Onglet "Secrets"
    4. Ajoutez/modifiez la section `[portfolio_data]`
    
    Les données se rechargeront automatiquement !
    """)
    
    # Bouton d'actualisation
    refresh = st.sidebar.button("🔄 Actualiser les données", use_container_width=True)
    
    # Parser les données
    etf_data = parse_input(etf_input)
    scpi_data = parse_input(scpi_input)
    
    # Créer deux colonnes principales
    col1, col2 = st.columns(2)
    
    # --- GRAPHIQUE EN CAMEMBERT ---
    with col1:
        st.subheader("🥧 Allocation d'Actifs")
        
        all_assets = {}
        for ticker, amount in etf_data.items():
            all_assets[f"ETF: {ticker}"] = amount
        for name, amount in scpi_data.items():
            all_assets[f"SCPI: {name}"] = amount
        
        if all_assets:
            df_allocation = pd.DataFrame({
                'Actif': list(all_assets.keys()),
                'Montant': list(all_assets.values())
            })
            
            total = df_allocation['Montant'].sum()
            df_allocation['Pourcentage'] = (df_allocation['Montant'] / total * 100).round(2)
            
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
                fig_line = go.Figure()
                
                for ticker in etf_data.keys():
                    try:
                        data = yf.download(
                            ticker,
                            period=period_options[selected_period],
                            progress=False
                        )
                        
                        if not data.empty:
                            if isinstance(data.columns, pd.MultiIndex):
                                close_prices = data['Close'][ticker] if ticker in data['Close'].columns else data['Close'].iloc[:, 0]
                            else:
                                close_prices = data['Close']
                            
                            normalized = (close_prices / close_prices.iloc[0] * 100)
                            
                            fig_line.add_trace(go.Scatter(
                                x=data.index,
                                y=normalized,
                                mode='lines',
                                name=ticker,
                                hovertemplate='<b>' + ticker + '</b><br>Date: %{x}<br>Performance: %{y:.2f}<extra></extra>'
                            ))
                    except Exception as e:
                        st.warning(f"Erreur pour {ticker}: {str(e)}")
                
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
    if total_portfolio > 0 and (total_etf > 0 or total_scpi > 0):
        st.divider()
        st.subheader("⚖️ Répartition Bourse (ETF) vs Immobilier (SCPI)")
        
        col_graph, col_stats = st.columns([2, 1])
        
        with col_graph:
            # Créer les données seulement pour les catégories non vides
            categories = []
            montants = []
            
            if total_etf > 0:
                categories.append('ETF (Bourse)')
                montants.append(total_etf)
            
            if total_scpi > 0:
                categories.append('SCPI (Immobilier)')
                montants.append(total_scpi)
            
            df_repartition = pd.DataFrame({
                'Catégorie': categories,
                'Montant': montants
            })
            
            df_repartition['Pourcentage'] = (df_repartition['Montant'] / total_portfolio * 100).round(2)
            
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
    
    st.info("ℹ️ **Note**: Les SCPI ne sont pas cotées en bourse. Les montants affichés sont vos investissements.")
    
    st.divider()
    st.caption("📅 Dernière actualisation: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    st.caption("Les données ETF proviennent de Yahoo Finance.")

# Point d'entrée principal
def main():
    if check_password():
        main_app()

if __name__ == "__main__":
    main()
