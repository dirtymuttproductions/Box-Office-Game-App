import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

# --- SETUP ---
st.set_page_config(page_title="Box Office League", page_icon="🎬", layout="centered")

# Custom CSS for a clean mobile look
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stProgress > div > div > div > div { background-color: #00cc00; }
    .metric-card { background-color: #f9f9f9; border-radius: 10px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# --- DATA LOADING ---
@st.cache_data(ttl=600)
def load_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # --- OPTION A: LOCAL FILE (Use this if testing on PC) ---
    # creds = ServiceAccountCredentials.from_json_keyfile_name('steve_creds.json', scope)
    
    # --- OPTION B: STREAMLIT CLOUD (Uncomment for deployment) ---
    key_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1t43oLbdIDxdnANi_KiDd5doZUquvULt82Jshtgstrf4")
    
    players_data = sheet.worksheet("Players").get_all_records()
    films_data = sheet.worksheet("Purchased_Films").get_all_records()
    
    return pd.DataFrame(players_data), pd.DataFrame(films_data)

try:
    df_players, df_films = load_data()

    # --- DATA PREP ---
    # Clean Numbers
    df_players['Net_worth'] = pd.to_numeric(df_players['Net_worth'], errors='coerce').fillna(0)
    df_players['Remaining_Points'] = pd.to_numeric(df_players['Remaining_Points'], errors='coerce').fillna(0)
    df_films['Current_Total_Gross'] = pd.to_numeric(df_films['Current_Total_Gross'], errors='coerce').fillna(0)
    
    # Sort players by Net Worth for the dropdown
    df_players = df_players.sort_values('Net_worth', ascending=False)
    player_list = df_players['Player_Name'].tolist()

    # --- INTERFACE ---
    
    # 1. PLAYER SELECTOR (Top of screen)
    selected_player_name = st.selectbox("Select Player:", player_list)
    
    # Get the specific data for this player
    player_stats = df_players[df_players['Player_Name'] == selected_player_name].iloc[0]
    
    # Filter films for this player
    player_films = df_films[df_films['Owner'] == selected_player_name].sort_values("Current_Total_Gross", ascending=False)

    # 2. PROFILE HEADER
    st.title(f"{selected_player_name}")
    
    # 3. KEY METRICS ROW
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Net Worth", f"${player_stats['Net_worth']:,.1f}M")
    with col2:
        st.metric("Films Owned", f"{len(player_films)}")
    with col3:
        st.metric("Cash Left", f"{player_stats['Remaining_Points']:.1f} pts")

    st.divider()

    # 4. CHART: THEIR FILM PERFORMANCE
    if not player_films.empty:
        st.subheader("📊 Portfolio Performance")
        chart = alt.Chart(player_films).mark_bar().encode(
            x=alt.X('Current_Total_Gross', title='Total Gross ($M)'),
            y=alt.Y('Title', sort='-x', title=None),
            color=alt.Color('Current_Total_Gross', scale=alt.Scale(scheme='greens')),
            tooltip=['Title', 'Genre', 'Current_Total_Gross']
        ).properties(height=max(200, len(player_films) * 40)) # Dynamic height based on film count
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("This player hasn't bought any films yet.")

    # 5. MOVIE ROSTER LIST
    st.subheader("🎥 Film Roster")
    
    if not player_films.empty:
        for index, row in player_films.iterrows():
            # Create a card for each movie
            with st.container():
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{row['Title']}**")
                    st.caption(f"{row['Genre']} | Released: {row['Release_Date']}")
                with c2:
                    st.markdown(f"**${row['Current_Total_Gross']:.1f}M**")
                
                # LBS Progress Bar
                try:
                    score = float(row['Actual_LBS_Score'])
                    st.progress(score / 5.0)
                    st.caption(f"LBS Score: {score}/5.0")
                except:
                    st.caption("LBS Score: Pending")
                
                st.write("---") # Thin separator line
    else:
        st.write("No films to display.")

except Exception as e:
    st.error("Steve encountered an error loading the data.")
    st.exception(e)
