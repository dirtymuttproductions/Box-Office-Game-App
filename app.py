import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

# --- SETUP ---
st.set_page_config(page_title="Box Office League", page_icon="🎬", layout="centered")

# Custom CSS
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stProgress > div > div > div > div { background-color: #00cc00; }
    .streamlit-expanderHeader { font-size: 18px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- DATA LOADING ---
@st.cache_data(ttl=600)
def load_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # --- DEPLOYMENT CREDENTIALS ---
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
    df_players['Net_worth'] = pd.to_numeric(df_players['Net_worth'], errors='coerce').fillna(0)
    df_players['Remaining_Points'] = pd.to_numeric(df_players['Remaining_Points'], errors='coerce').fillna(0)
    df_films['Current_Total_Gross'] = pd.to_numeric(df_films['Current_Total_Gross'], errors='coerce').fillna(0)
    
    # Sort for Leaderboard
    df_players = df_players.sort_values('Net_worth', ascending=False).reset_index(drop=True)
    leader = df_players.iloc[0]

    # --- HEADER ---
    st.title("🎬 Box Office League")
    st.markdown("### 👑 Season Leader")
    st.markdown(f"<p class='big-font'>{leader['Player_Name']}</p>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Net Worth", f"${leader['Net_worth']:,.1f}M")
    with c2:
        st.metric("Films Owned", f"{leader['Films_Owned']}")
    
    st.divider()

    # --- NEW VISUAL: SIMPLE BAR CHART ---
    st.subheader("📊 The Race")
    
    # Create a clean horizontal bar chart
    chart = alt.Chart(df_players).mark_bar().encode(
        x=alt.X('Net_worth', title='Net Worth ($M)'),
        y=alt.Y('Player_Name', sort='-x', title=""), # Sort by value, hide axis title
        color=alt.Color('Net_worth', scale=alt.Scale(scheme='greens'), legend=None),
        tooltip=['Player_Name', 'Net_worth', 'Remaining_Points']
    ).properties(height=300) # Fixed height
    
    # Add text labels to the bars for readability
    text = chart.mark_text(
        align='left',
        baseline='middle',
        dx=3  # Nudges text to right so it doesn't overlap bar
    ).encode(
        text=alt.Text('Net_worth', format=",.0f")
    )
    
    st.altair_chart(chart + text, use_container_width=True)

    # --- LEADERBOARD ---
    st.subheader("🏆 Standings")
    
    for rank, player in df_players.iterrows():
        real_rank = rank + 1
        name = player['Player_Name']
        net_worth = player['Net_worth']
        
        with st.expander(f"#{real_rank} {name}  —  ${net_worth:,.1f}M"):
            
            # Stats Row
            c1, c2 = st.columns(2)
            c1.write(f"💰 Cash: **{player['Remaining_Points']}**")
            c2.write(f"🎞️ Films: **{player['Films_Owned']}**")
            
            st.write("---")
            
            # Film List
            my_films = df_films[df_films['Owner'] == name].sort_values("Current_Total_Gross", ascending=False)
            
            if not my_films.empty:
                for _, film in my_films.iterrows():
                    f1, f2 = st.columns([3, 1])
                    with f1:
                        st.write(f"**{film['Title']}**")
                        try:
                            score = float(film['Actual_LBS_Score'])
                            st.progress(score / 5.0)
                        except:
                            pass
                    with f2:
                        st.write(f"**${film['Current_Total_Gross']:.0f}M**")
            else:
                st.write("No films.")

except Exception as e:
    st.error("Steve is rebooting. (Data Error)")
    st.exception(e)
