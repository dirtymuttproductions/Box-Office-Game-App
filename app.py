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
    .big-font { font-size:20px !important; font-weight: bold; }
    .stProgress > div > div > div > div { background-color: #00cc00; }
</style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
@st.cache_data(ttl=600)
def load_data():
    # 1. SETUP CREDENTIALS
    # If you are running locally, use the file. 
    # If on Streamlit Cloud, use st.secrets logic (commented out below)
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # --- OPTION A: LOCAL FILE (Use this if testing on PC) ---
    creds = ServiceAccountCredentials.from_json_keyfile_name('steve_creds.json', scope)
    
    # --- OPTION B: STREAMLIT CLOUD (Uncomment this when deploying!) ---
    # key_dict = st.secrets["gcp_service_account"]
    # creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1t43oLbdIDxdnANi_KiDd5doZUquvULt82Jshtgstrf4")
    
    # 2. FETCH DATA
    # We switch to 'Players' because 'Standings' has empty zeros
    players_data = sheet.worksheet("Players").get_all_records()
    films_data = sheet.worksheet("Purchased_Films").get_all_records()
    
    return pd.DataFrame(players_data), pd.DataFrame(films_data)

try:
    df_players, df_films = load_data()

    # --- CLEAN DATA ---
    # Ensure numbers are numeric
    df_players['Net_worth'] = pd.to_numeric(df_players['Net_worth'], errors='coerce').fillna(0)
    df_players['Total_Money_Million'] = pd.to_numeric(df_players['Total_Money_Million'], errors='coerce').fillna(0)
    
    # Sort by Net Worth (High to Low)
    df_players = df_players.sort_values('Net_worth', ascending=False).reset_index(drop=True)
    
    # Get the Leader
    leader = df_players.iloc[0]

    # --- TAB 1: THE DASHBOARD ---
    st.title("🎬 Box Office Game")
    
    # Victor Banner
    st.markdown("### 👑 Season Leader")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(f"https://api.dicebear.com/7.x/adventurer/svg?seed={leader['Player_Name']}", width=100)
    with col2:
        st.subheader(leader['Player_Name'])
        st.metric("Net Worth", f"${leader['Net_worth']:,.1f}M")
        st.caption(f"Films Owned: {leader['Films_Owned']}")

    st.divider()

    # The Chart
    st.subheader("📈 The Race")
    chart = alt.Chart(df_players).mark_bar().encode(
        x=alt.X('Net_worth', title='Net Worth ($M)'),
        y=alt.Y('Player_Name', sort='-x', title=None),
        color=alt.Color('Net_worth', scale=alt.Scale(scheme='greens')),
        tooltip=[
            alt.Tooltip('Player_Name', title='Player'),
            alt.Tooltip('Net_worth', title='Net Worth ($M)'),
            alt.Tooltip('Total_Money_Million', title='Box Office ($M)'),
            alt.Tooltip('Remaining_Points', title='Points Left')
        ]
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    # --- TAB 2: FILM GALLERY ---
    st.subheader("🎥 Film Performance")
    
    # Filter for owned films
    df_films['Current_Total_Gross'] = pd.to_numeric(df_films['Current_Total_Gross'], errors='coerce').fillna(0)
    owned_films = df_films[df_films['Owner'] != ""].sort_values("Current_Total_Gross", ascending=False)

    for index, row in owned_films.iterrows():
        with st.expander(f"{row['Title']} (${row['Current_Total_Gross']}M)"):
            st.write(f"**Owner:** {row['Owner']}")
            st.write(f"**Genre:** {row['Genre']}")
            st.write(f"**LBS Score:** {row['Actual_LBS_Score']}")
            try:
                score = float(row['Actual_LBS_Score'])
                st.progress(score / 5.0)
            except:
                pass

except Exception as e:
    st.error("Steve is having trouble reading the score. (Data Error)")
    st.write(e)
