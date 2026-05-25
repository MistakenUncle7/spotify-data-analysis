import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# ==========================================================
# 1. Streamlit settings
# ==========================================================
st.set_page_config(
    page_title="Datos Masivos Spotify",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS personalizado para adaptar la paleta de colores a Spotify
st.markdown("""
    <style>
    .main { background-color: #121212; color: #FFFFFF; }
    .stMetric { background-color: #181818; padding: 15px; border-radius: 10px; border: 1px solid #282828; }
    div[data-testid="stMetricValue"] { color: #1DB954; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎵 Analisis Datos Masivos Spotify_History_Audio")
st.markdown("---")

# ==========================================================
# 2. Load data
# ==========================================================
@st.cache_data
def load_gold_layer():
    try:
        hourly = pd.read_parquet("/app/data/gold/hourly_distribution.parquet")
        weekly = pd.read_parquet("/app/data/gold/weekly_distribution.parquet")
        heatmap_matrix = pd.read_parquet("/app/data/gold/eda_temporal_heatmap.parquet")
        artists = pd.read_parquet("/app/data/gold/top_artists.parquet")
        tracks = pd.read_parquet("/app/data/gold/top_tracks.parquet")
        skips = pd.read_parquet("/app/data/gold/skip_rates.parquet")
        diversity = pd.read_parquet("/app/data/gold/musical_diversity.parquet")
        return hourly, weekly, heatmap_matrix, artists, tracks, skips, diversity
    except Exception as e:
        st.error(f"Error al cargar la capa Gold. Asegúrate de correr los agregados en tu notebook primero. Detalle: {e}")
        return None, None, None, None, None, None, None

df_hourly, df_weekly, df_heatmap, df_artists, df_tracks, df_skips, df_diversity = load_gold_layer()

days_dict = {2: "Lunes", 3: "Martes", 4: "Miércoles", 5: "Jueves", 6: "Viernes", 7: "Sábado", 1: "Domingo"}
order_days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# ==========================================================
# 3. Filters sidebar
# ==========================================================
st.sidebar.header("🎛️ Paneles de Control")

if df_hourly is not None:
    usuarios_disponibles = ["Todos"] + list(df_hourly["user_id"].unique())
    user_select = st.sidebar.selectbox("Seleccionar Perfil de Usuario:", options=usuarios_disponibles)
    
    if user_select != "Todos":
        df_hourly = df_hourly[df_hourly["user_id"] == user_select]
        df_weekly = df_weekly[df_weekly["user_id"] == user_select]
        df_artists = df_artists[df_artists["user_id"] == user_select]
        df_tracks = df_tracks[df_tracks["user_id"] == user_select]
        df_skips = df_skips[df_skips["user_id"] == user_select]
        df_diversity = df_diversity[df_diversity["user_id"] == user_select]

st.sidebar.markdown("---")
st.sidebar.info("💡 **Arquitectura del Sistema:** Este Dashboard opera sobre la **Gold Layer** (Servicios Agregados en Parquet). Carga instantánea sin latencia de Spark.")

# ==========================================================
# 4. Content
# ==========================================================

st.header("📈 Análisis Exploratorio de Datos Consolidado")
st.markdown("Vistas integradas del comportamiento temporal y métricas de consumo de contenido.")

if df_hourly is not None and df_weekly is not None:

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_streams = df_hourly["count"].sum()
        st.metric("Reproducciones Totales", f"{total_streams:,}")
    with col2:
        peak_hour = df_hourly.groupby("hour")["count"].sum().idxmax()
        st.metric("Hora Pico de Consumo", f"{peak_hour}:00 hrs")
    with col3:
        peak_day_idx = df_weekly.groupby("day_of_week")["count"].sum().idxmax()
        st.metric("Día Más Activo", days_dict.get(peak_day_idx, "Desconocido"))
    with col4:
        if df_artists is not None:
            total_artistas = df_artists["master_metadata_album_artist_name"].nunique()
            st.metric("Artistas Únicos Escuchados", f"{total_artistas:,}")
        
    st.markdown("---")
    

    st.subheader("⏱️ Distribuciones Cronológicas de Escucha")
    graf_temp1, graf_temp2 = st.columns(2)
    
    with graf_temp1:
        st.markdown("**Flujo de Escucha por Hora del Día**")
        hourly_chart = df_hourly.groupby("hour")["count"].sum().reset_index()
        fig, ax = plt.subplots(figsize=(7, 3.5))
        sns.barplot(data=hourly_chart, x="hour", y="count", palette="magma", ax=ax)
        ax.set_xlabel("Hora (0-23)")
        ax.set_ylabel("Streams")
        plt.tight_layout()
        st.pyplot(fig)
        
    with graf_temp2:
        st.markdown("**Flujo de Escucha por Día de la Semana**")
        weekly_chart = df_weekly.groupby("day_of_week")["count"].sum().reset_index()
        weekly_chart["Día"] = weekly_chart["day_of_week"].map(days_dict)
        weekly_chart["Día"] = pd.Categorical(weekly_chart["Día"], categories=order_days, ordered=True)
        weekly_chart = weekly_chart.sort_values("Día")
        
        fig, ax = plt.subplots(figsize=(7, 3.5))
        sns.barplot(data=weekly_chart, x="count", y="Día", palette="viridis", ax=ax, orient="h")
        ax.set_xlabel("Streams")
        ax.set_ylabel("")
        plt.tight_layout()
        st.pyplot(fig)


    if df_heatmap is not None:
        st.markdown("**Densidad de Escucha Cruzada (Hora vs Día)**")
        try:
            
            if user_select != "Todos":
                df_heatmap_filtered = df_heatmap[df_heatmap["user_id"] == user_select]
            else:
                df_heatmap_filtered = df_heatmap.copy()
            
            df_pivot = df_heatmap_filtered.groupby("hour").sum(numeric_only=True).sort_index()
            
            df_pivot = df_pivot.reindex(columns=["2", "3", "4", "5", "6", "7", "1"])
            
            df_pivot.columns = order_days
            
            fig, ax = plt.subplots(figsize=(14, 4))
            sns.heatmap(df_pivot, cmap="YlGnBu", annot=False, cbar=True, ax=ax)
            ax.set_ylabel("Hora")
            ax.set_xlabel("Día")
            plt.tight_layout()
            st.pyplot(fig)
            
        except Exception as heatmap_error:
            st.warning(f"Ajustando matriz del mapa de calor... {heatmap_error}")

    st.markdown("---")
    
    st.subheader("🏆 Análisis de Contenido y Preferencias")
    graf_cont1, graf_cont2 = st.columns(2)
    
    with graf_cont1:
        if df_artists is not None:
            st.markdown("**Top 10 Artistas Más Escuchados**")
            top_art = df_artists.groupby("master_metadata_album_artist_name")["count"].sum().reset_index()
            top_art = top_art.sort_values("count", ascending=False).head(10)
            
            fig, ax = plt.subplots(figsize=(7, 4))
            sns.barplot(data=top_art, x="count", y="master_metadata_album_artist_name", palette="coolwarm", ax=ax)
            ax.set_xlabel("Reproducciones")
            ax.set_ylabel("")
            plt.tight_layout()
            st.pyplot(fig)
        
    with graf_cont2:
        if df_skips is not None:
            st.markdown("**Perfil del Usuario: Tasa de Reproducción Completa vs Skip**")
            skip_chart = df_skips.groupby("skipped")["count"].sum().reset_index()
            skip_chart["Estado"] = skip_chart["skipped"].map({True: "Saltada (Skip)", False: "Escuchada Completa"})
            
            fig, ax = plt.subplots(figsize=(7, 3.2))
            colors = ["#1DB954", "#E11212"]
            ax.pie(skip_chart["count"], labels=skip_chart["Estado"], autopct='%1.1f%%', startangle=90, colors=colors, textprops={'color':"black", 'weight':'bold'})
            ax.axis('equal')  
            plt.tight_layout()
            st.pyplot(fig)

    if df_diversity is not None:
        st.markdown("**Índice de Diversidad Musical Histórica por Año**")
        div_chart = df_diversity.groupby("year").sum().reset_index()
        div_chart["ratio_diversidad"] = div_chart["unique_artists"] / div_chart["total_streams"]
        
        fig, ax = plt.subplots(figsize=(14, 3))
        sns.lineplot(data=div_chart, x="year", y="ratio_diversidad", marker="o", color="#1DB954", linewidth=2.5, ax=ax)
        ax.set_xlabel("Año")
        ax.set_ylabel("Ratio (Artistas Únicos / Total Streams)")
        plt.tight_layout()
        st.pyplot(fig)
