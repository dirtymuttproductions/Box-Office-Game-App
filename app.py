import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

# --- SETUP ---
st.set_page_config(page_title="Box Office League", page_icon="🎬", layout="centered")

# Custom CSS for cleaner look
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stProgress > div > div > div > div { background-color: #00cc00; }
    /* Make expander headers look like a leaderboard row */
    .streamlit-expanderHeader {
        font-size: 18px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- DATA LOADING ---
@st.cache_data(ttl=600)
def load_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # --- DEPLOYMENT CREDENTIALS ---
    # Use st.secrets when running on Streamlit Cloud
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
    # Ensure numbers are numeric and handle missing values
    df_players['Net_worth'] = pd.to_numeric(df_players['Net_worth'], errors='coerce').fillna(0)
    df_players['Remaining_Points'] = pd.to_numeric(df_players['Remaining_Points'], errors='coerce').fillna(0)
    df_films['Current_Total_Gross'] = pd.to_numeric(df_films['Current_Total_Gross'], errors='coerce').fillna(0)
    
    # Sort players by Net Worth (Highest First)
    df_players = df_players.sort_values('Net_worth', ascending=False).reset_index(drop=True)
    
    # Identify Leader
    leader = df_players.iloc[0]

    # --- HEADER SECTION ---
    st.title("🎬 Box Office League")

    # Leader Spotlight (No Avatar)
    st.markdown("### 👑 Season Leader")
    st.markdown(f"<p class='big-font'>{leader['Player_Name']}</p>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Net Worth", f"${leader['Net_worth']:,.1f}M")
    with c2:
        st.metric("Films Owned", f"{leader['Films_Owned']}")
    
    st.divider()

    # --- CHART SECTION ---
    st.subheader("📈 The Race")
    chart = alt.Chart(df_players).mark_bar().encode(
        x=alt.X('Net_worth', title='Net Worth ($M)'),
        y=alt.Y('Player_Name', sort='-x', title=None),
        color=alt.Color('Net_worth', scale=alt.Scale(scheme='greens')),
        tooltip=['Player_Name', 'Net_worth', 'Remaining_Points']
    ).properties(height=250)
    st.altair_chart(chart, use_container_width=True)

    # --- LEADERBOARD (Dropdowns) ---
    st.subheader("🏆 Standings")
    st.caption("Click on a player to see their roster.")

    # Iterate through players in ranked order
    for rank, player in df_players.iterrows():
        real_rank = rank + 1
        name = player['Player_Name']
        net_worth = player['Net_worth']
        cash = player['Remaining_Points']
        
        # The Dropdown Header: "1. Matt - $1,250.4M"
        with st.expander(f"#{real_rank} {name}  —  ${net_worth:,.1f}M"):
            
            # Inside the dropdown: Stats
            m1, m2 = st.columns(2)
            m1.write(f"💰 **Cash Available:** {cash} pts")
            m2.write(f"🎞️ **Films Owned:** {player['Films_Owned']}")
            
            st.markdown("#### Film Roster")
            
            # Filter films for this specific player
            my_films = df_films[df_films['Owner'] == name].sort_values("Current_Total_Gross", ascending=False)
            
            if not my_films.empty:
                for _, film in my_films.iterrows():
                    # Film Row layout
                    f1, f2 = st.columns([3, 1])
                    with f1:
                        st.write(f"**{film['Title']}**")
                        st.caption(f"{film['Genre']} | LBS: {film['Actual_LBS_Score']}")
                    with f2:
                        st.write(f"**${film['Current_Total_Gross']:.1f}M**")
                    
                    # Progress bar for LBS
                    try:
                        score = float(film['Actual_LBS_Score'])
                        st.progress(score / 5.0)
                    except:
                        pass
                    st.write("") # Spacer
            else:
                st.write("*No films purchased yet.*")

except Exception as e:
    st.error("Steve lost the script. (Connection Error)")
    st.exception(e)
