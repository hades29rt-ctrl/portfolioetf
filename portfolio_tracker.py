import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import hashlib
from supabase import create_client, Client

# Configuration de la page
st.set_page_config(page_title="Suivi Portfolio ETF & SCPI", layout="wide")

# Connexion à Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase: Client = init_supabase()

# Fonctions d'authentification
def hash_password(password):
    """Hash le mot de passe avec SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, username, password):
    """Créer un nouveau utilisateur"""
    try:
        password_hash = hash_password(password)
        response = supabase.table('users').insert({
            'email': email,
            'username': username,
            'password_hash': password_hash
        }).execute()
        return True, "Compte créé avec succès !"
    except Exception as e:
        return False, f"Erreur : {str(e)}"

def login_user(username, password):
    """Connexion utilisateur"""
    try:
        password_hash = hash_password(password)
        response = supabase.table('users').select('*').eq('username', username).eq('password_hash', password_hash).execute()
        
        if response.data and len(response.data) > 0:
            return True, response.data[0]
        else:
            return False, "Identifiants incorrects"
    except Exception as e:
        return False, f"Erreur : {str(e)}"

# Fonctions de gestion des portfolios
def load_user_etfs(user_id):
    """Charger les ETF de l'utilisateur"""
    try:
        response = supabase.table('user_etfs').select('*').eq('user_id', user_id).execute()
        data = {}
        for item in response.data:
            data[item['ticker']] = float(item['amount'])
        return data
    except:
        return {}

def load_user_scpis(user_id):
    """Charger les SCPI de l'utilisateur"""
    try:
        response = supabase.table('user_scpis').select('*').eq('user_id', user_id).execute()
        data = {}
        for item in response.data:
            data[item['name']] = float(item['amount'])
        return data
    except:
        return {}

def save_user_etfs(user_id, etf_data):
    """Sauvegarder les ETF de l'utilisateur"""
    try:
        # Supprimer les anciennes données
        supabase.table('user_etfs').delete().eq('user_id', user_id).execute()
        
        # Insérer les nouvelles données
        for ticker, amount in etf_data.items():
            supabase.table('user_etfs').insert({
                'user_id': user_id,
                'ticker': ticker,
                'amount': amount
            }).execute()
        return True
    except Exception as e:
        st.error(f"Erreur sauvegarde ETF : {str(e)}")
        return False

def save_user_scpis(user_id, scpi_data):
    """Sauvegarder les SCPI de l'utilisateur"""
    try:
        # Supprimer les anciennes données
        supabase.table('user_scpis').delete().eq('user_id', user_id).execute()
        
        # Insérer les nouvelles données
        for name, amount in scpi_data.items():
            supabase.table('user_scpis').insert({
                'user_id': user_id,
                'name': name,
                'amount': amount
            }).execute()
        return True
    except Exception as e:
        st.error(f"Erreur sauvegarde SCPI : {str(e)}")
        return False

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

# Page de connexion/inscription
def auth_page():
    st.title("🔐 Connexion à Portfolio Tracker")
    
    tab1, tab2 = st.tabs(["Connexion", "Inscription"])
    
    with tab1:
        st.subheader("Connexion")
        username = st.text_input("Nom d'utilisateur", key="login_username")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        
        if st.button("Se connecter", type="primary"):
            if username and password:
                success, result = login_user(username, password)
                if success:
                    st.session_state.user = result
                    st.session_state.authenticated = True
                    st.success("Connexion réussie !")
                    st.rerun()
                else:
                    st.error(result)
            else:
                st.error("Veuillez remplir tous les champs")
    
    with tab2:
        st.subheader("Créer un compte")
        new_email = st.text_input("Email", key="signup_email")
        new_username = st.text_input("Nom d'utilisateur", key="signup_username")
        new_password = st.text_input("Mot de passe", type="password", key="signup_password")
        new_password_confirm = st.text_input("Confirmer le mot de passe", type="password", key="signup_password_confirm")
        
        if st.button("Créer le compte", type="primary"):
            if new_email and new_username and new_password and new_password_confirm:
                if new_password != new_password_confirm:
                    st.error("Les mots de passe ne correspondent pas")
                elif len(new_password) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères")
                else:
                    success, message = create_user(new_email, new_username, new_password)
                    if success:
                        st.success(message)
                        st.info("Vous pouvez maintenant vous connecter !")
                    else:
                        st.error(message)
            else:
                st.error("Veuillez remplir tous les champs")

# Application principale
def main_app():
    st.title("📊 Suivi de Portfolio - ETF & SCPI")
    
    # Bouton de déconnexion
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🚪 Déconnexion"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
    
    st.write(f"👤 Connecté en tant que : **{st.session_state.user['username']}**")
    
    # Charger les données de l'utilisateur
    user_id = st.session_state.user['id']
    saved_etfs = load_user_etfs(user_id)
    saved_scpis = load_user_scpis(user_id)
    
    # Convertir en format texte pour l'affichage
    default_etf_text = "\n".join([f"{ticker},{amount}" for ticker, amount in saved_etfs.items()]) if saved_etfs else "IWDA.AS,5000\nCW8.PA,3000"
    default_scpi_text = "\n".join([f"{name},{amount}" for name, amount in saved_scpis.items()]) if saved_scpis else "Corum Origin,4000\nPrimovie,3000"
    
    # Sidebar pour la configuration
    st.sidebar.header("Configuration du Portfolio")
    
    # Section ETF
    st.sidebar.subheader("ETF")
    etf_input = st.sidebar.text_area(
        "ETF (format: Ticker,Montant par ligne)",
        value=default_etf_text,
        height=100
    )
    
    # Section SCPI
    st.sidebar.subheader("SCPI")
    scpi_input = st.sidebar.text_area(
        "SCPI (format: Nom,Montant par ligne)",
        value=default_scpi_text,
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
            etf_data = parse_input(etf_input)
            scpi_data = parse_input(scpi_input)
            
            if save_user_etfs(user_id, etf_data) and save_user_scpis(user_id, scpi_data):
                st.success("✅ Sauvegardé !")
            else:
                st.error("❌ Erreur de sauvegarde")
    
    with col_refresh:
        refresh = st.button("🔄 Actualiser", use_container_width=True)
    
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
    if total_portfolio > 0:
        st.divider()
        st.subheader("⚖️ Répartition Bourse (ETF) vs Immobilier (SCPI)")
        
        col_graph, col_stats = st.columns([2, 1])
        
        with col_graph:
            df_repartition = pd.DataFrame({
                'Catégorie': ['ETF (Bourse)', 'SCPI (Immobilier)'],
                'Montant': [total_etf, total_scpi]
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
    # Initialiser l'état de session
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    # Afficher la page appropriée
    if st.session_state.authenticated:
        main_app()
    else:
        auth_page()

if __name__ == "__main__":
    main()
