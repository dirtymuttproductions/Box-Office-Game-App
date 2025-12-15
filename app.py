import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt
from datetime import datetime

# --- SETUP ---
st.set_page_config(page_title="Box Office League", page_icon="🎬", layout="centered")

st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .streamlit-expanderHeader { font-size: 18px; font-weight: 600; }
    .stProgress > div > div > div > div { background-color: #00cc00; }
</style>
""", unsafe_allow_html=True)

# --- LOADING ---
# NOTE: Removed @cache for this function so Actions update immediately
def get_connection():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    key_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key("1t43oLbdIDxdnANi_KiDd5doZUquvULt82Jshtgstrf4")

try:
    sheet = get_connection()
    # Read data into Pandas
    df_players = pd.DataFrame(sheet.worksheet("Players").get_all_records())
    df_films = pd.DataFrame(sheet.worksheet("Purchased_Films").get_all_records())
    df_draft = pd.DataFrame(sheet.worksheet("Draft_Pool").get_all_records())

    # Prep Data
    df_players['Net_worth'] = pd.to_numeric(df_players['Net_worth'], errors='coerce').fillna(0)
    df_films['Current_Total_Gross'] = pd.to_numeric(df_films['Current_Total_Gross'], errors='coerce').fillna(0)
    df_players = df_players.sort_values('Net_worth', ascending=False)
    leader = df_players.iloc[0]

    # --- TABS ---
    tab_view, tab_action = st.tabs(["🏆 Dashboard", "⚡ Actions"])

    # ==========================
    # TAB 1: VIEW (Original)
    # ==========================
    with tab_view:
        st.title("🎬 Box Office League")
        
        # Leader Banner
        st.markdown(f"### 👑 {leader['Player_Name']}")
        c1, c2 = st.columns(2)
        c1.metric("Net Worth", f"${leader['Net_worth']:,.1f}M")
        c2.metric("Films", f"{leader['Films_Owned']}")
        st.divider()

        # Chart
        st.subheader("📊 The Race")
        chart = alt.Chart(df_players).mark_bar().encode(
            x=alt.X('Net_worth', title='Net Worth ($M)'),
            y=alt.Y('Player_Name', sort='-x', title=""), 
            color=alt.Color('Net_worth', scale=alt.Scale(scheme='greens'), legend=None),
            tooltip=['Player_Name', 'Net_worth']
        ).properties(height=300)
        
        text = chart.mark_text(align='left', dx=3).encode(text=alt.Text('Net_worth', format=",.0f"))
        st.altair_chart(chart + text, use_container_width=True)

        # Standings Dropdowns
        st.subheader("🏆 Standings")
        for rank, player in df_players.iterrows():
            with st.expander(f"#{rank+1} {player['Player_Name']} — ${player['Net_worth']:,.1f}M"):
                c1, c2 = st.columns(2)
                c1.write(f"💰 Points: **{player['Remaining_Points']}**")
                c2.write(f"🎞️ Films: **{player['Films_Owned']}**")
                st.write("---")
                
                my_films = df_films[df_films['Owner'] == player['Player_Name']].sort_values("Current_Total_Gross", ascending=False)
                if not my_films.empty:
                    for _, film in my_films.iterrows():
                        f1, f2 = st.columns([3, 1])
                        f1.write(f"**{film['Title']}**")
                        # Star Rating
                        try:
                            score = float(film['Actual_LBS_Score'])
                            stars = int(round(score))
                            f1.caption("★" * stars + "☆" * (5 - stars) + f" ({score})")
                        except: pass
                        f2.write(f"**${film['Current_Total_Gross']:.0f}M**")
                else:
                    st.write("No films.")

    # ==========================
    # TAB 2: ACTIONS (New!)
    # ==========================
    with tab_action:
        st.header("⚡ Player Actions")
        st.warning("⚠️ Changes here affect the real game database immediately.")
        
        # Identity Selection
        me = st.selectbox("Who are you?", df_players['Player_Name'].tolist())
        
        st.divider()
        
        # ACTION 1: SUBMIT OWBO
        st.subheader("1. Submit Prediction")
        
        # Get movies that need predictions (Optional: Filter by date if you want)
        # For now, just listing all films in the Films roster
        try:
            prediction_films = pd.DataFrame(sheet.worksheet("Films").get_all_records())
            # Simple filter: films released in future or recently
            targets = prediction_films['Title'].tolist()
        except:
            targets = ["Error loading films"]

        with st.form("owbo_form"):
            film_choice = st.selectbox("Select Film:", targets)
            prediction_val = st.number_input("Your OWBO Guess ($M):", min_value=0.0, step=0.1)
            submitted = st.form_submit_button("Submit Prediction")
            
            if submitted:
                # Write to OWBO_Predictions sheet
                # Note: This appends a row. Your bot logic usually handles where it goes.
                # Simplest way: Append to bottom, Bot processes it later.
                try:
                    pred_ws = sheet.worksheet("OWBO_Predictions")
                    # Schema: Week, Film_ID, Title, Date, Player, ID, Prediction, Timestamp...
                    # We just fill what we know
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    pred_ws.append_row(["", "", film_choice, "", me, "", str(prediction_val), now_str])
                    st.success(f"✅ Prediction logged: {me} guessed ${prediction_val}M for {film_choice}")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.divider()

        # ACTION 2: BUY FILM
        st.subheader("2. Buy Film")
        
        # Filter Draft Pool for available films
        available_films = df_draft[df_draft['Available_For_Purchase'] == "TRUE"]
        
        if not available_films.empty:
            buy_choice = st.selectbox("Select Film to Buy:", available_films['Title'].tolist())
            film_info = available_films[available_films['Title'] == buy_choice].iloc[0]
            cost = float(film_info['Actual_OWBO_Million'] or 0) / 10 # Assuming 1 pt = $10M rule
            
            st.write(f"**Cost:** {cost:.2f} points")
            
            if st.button("Confirm Purchase"):
                # 1. Update Draft Pool (Mark FALSE)
                cell = df_draft[df_draft['Title'] == buy_choice].index[0] + 2 # +2 for header/0-index
                sheet.worksheet("Draft_Pool").update_cell(cell, 8, "FALSE") # Col 8 = Available
                
                # 2. Add to Purchased Films
                # Title, Date, Genre, Owner, OWBO, Gross, LBS...
                new_film_row = [
                    buy_choice, 
                    film_info['Release_Date'], 
                    film_info['Genre'], 
                    me, 
                    film_info['Actual_OWBO_Million'], 
                    film_info['Current_Total_Gross'], 
                    film_info['Actual_LBS_Score']
                ]
                sheet.worksheet("Purchased_Films").append_row(new_film_row)
                
                # 3. Deduct Points (Optional - requires finding player row)
                # For safety, maybe let Steve handle the deduction or add logic here.
                
                st.success(f"🎉 You bought {buy_choice}!")
                st.cache_data.clear() # Clear cache so dashboard updates
        else:
            st.write("No films available in Draft Pool.")

except Exception as e:
    st.error("Steve is offline.")
    st.write(e)
