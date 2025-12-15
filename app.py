import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

# --- SETUP ---
# Page configuration for mobile-friendly view
st.set_page_config(page_title="Box Office League", page_icon="🎬", layout="centered")

# Custom CSS to make it look like a native app
st.markdown("""
<style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stProgress > div > div > div > div { background-color: #00cc00; }
</style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
# Uses the same "GOOGLE_CREDS" json file your bot uses
@st.cache_data(ttl=600) # Cache data for 10 minutes to save API quotas
def load_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    # Ensure 'steve_creds.json' matches your actual credential filename
    key_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    
    # Open your spreadsheet
    sheet = client.open_by_key("1t43oLbdIDxdnANi_KiDd5doZUquvULt82Jshtgstrf4")
    
    # Fetch specific worksheets
    standings_data = sheet.worksheet("Standings").get_all_records()
    films_data = sheet.worksheet("Purchased_Films").get_all_records()
    
    return pd.DataFrame(standings_data), pd.DataFrame(films_data)

try:
    df_standings, df_films = load_data()

    # --- PROCESSING DATA ---
    # Ensure numbers are floats for sorting
    df_standings['Total_Net_Worth_Million'] = pd.to_numeric(df_standings['Total_Net_Worth_Million'], errors='coerce').fillna(0)
    df_standings = df_standings.sort_values('Total_Net_Worth_Million', ascending=False)
    
    # Get the Leader
    leader = df_standings.iloc[0]

    # --- TAB 1: THE DASHBOARD ---
    st.title("🎬 Box Office Game")
    
    # The "Victor" Banner
    st.markdown("### 👑 Season Leader")
    col1, col2 = st.columns([1, 2])
    with col1:
        # Generates a fun avatar based on the player's name
        st.image(f"https://api.dicebear.com/7.x/adventurer/svg?seed={leader['Player_Name']}", width=100)
    with col2:
        st.subheader(leader['Player_Name'])
        st.metric("Net Worth", f"${leader['Total_Net_Worth_Million']:,.1f}M")
        st.caption(f"Films Owned: {leader['Films_Owned']}")

    st.divider()

    # The Chart
    st.subheader("📈 The Race")
    chart = alt.Chart(df_standings).mark_bar().encode(
        x=alt.X('Total_Net_Worth_Million', title='Net Worth ($M)'),
        y=alt.Y('Player_Name', sort='-x', title=None),
        color=alt.Color('Total_Net_Worth_Million', scale=alt.Scale(scheme='greens')),
        tooltip=['Player_Name', 'Total_Net_Worth_Million', 'Liquid_Cash_Million']
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    # --- TAB 2: FILM GALLERY ---
    st.subheader("🎥 Film Performance")
    
    # Filter for owned films only and sort by Gross
    df_films['Current_Total_Gross'] = pd.to_numeric(df_films['Current_Total_Gross'], errors='coerce').fillna(0)
    owned_films = df_films[df_films['Owner'] != ""].sort_values("Current_Total_Gross", ascending=False)

    for index, row in owned_films.iterrows():
        with st.expander(f"{row['Title']} (${row['Current_Total_Gross']}M)"):
            st.write(f"**Owner:** {row['Owner']}")
            st.write(f"**Genre:** {row['Genre']}")
            st.write(f"**LBS Score:** {row['Actual_LBS_Score']}")
            # Visual progress bar for LBS score (out of 5)
            try:
                score = float(row['Actual_LBS_Score'])
                st.progress(score / 5.0)
            except:
                pass

except Exception as e:
    st.error("Steve is on coffee break. (Connection Error)")

    st.write(e)
