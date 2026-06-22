import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# Set up the page configuration
st.set_page_config(
    page_title="Instagram Analytics Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App Title and Description
st.title("📱 Instagram Analytics Dashboard")
st.markdown("Analyze Instagram profiles and posts using the **instagram-looter2** RapidAPI.")

# CSS to make metrics look like rounded cards
st.markdown("""
<style>
[data-testid="stMetric"] {
    background-color: rgba(128, 128, 128, 0.1);
    border-radius: 15px;
    padding: 15px;
    border: 1px solid rgba(128, 128, 128, 0.2);
    box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 1. Sidebar Controls
# ------------------------------------------------------------------------------
st.sidebar.header("⚙️ Configuration")
HUBS_LIST = ["oskemen.hub", "astana.hub", "almaty_hub", "terriconvalley", "shymkent__hub", "batys.hub", "turkistan.hub", "zhambyl_hub", "jetisu_digital", "sko_hub", "abai_it", "pavlodar.hub", "kyzylordahub", "qostanai.hub", "alatau.hub", "aqmola.hub", "ulytau.hub", "atyrau_it_hub", "aqtobe.hub", "mangystau.hub"]
username = st.sidebar.selectbox("Instagram Username", HUBS_LIST)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_key = os.environ.get("RAPIDAPI_KEY", "")
if not api_key:
    st.sidebar.warning("⚠️ `RAPIDAPI_KEY` not found in `.env` or environment variables.")
else:
    st.sidebar.success("🔑 Welcome!")

fetch_button = st.sidebar.button("Fetch Live Metrics", type="primary")

st.sidebar.divider()
st.sidebar.markdown("### 🔄 Bulk Actions")
sync_all_button = st.sidebar.button("Sync All Hubs to Google Sheets", type="secondary")

# ------------------------------------------------------------------------------
# API Helper Functions
# ------------------------------------------------------------------------------
from scraper import fetch_and_parse_data
from google_sheets_writer import write_weekly_data
import time

@st.cache_data(show_spinner=False, ttl=600)
def cached_fetch_and_parse(user, key):
    return fetch_and_parse_data(user, key)

if sync_all_button:
    if not api_key:
        st.sidebar.error("⚠️ RAPIDAPI_KEY is missing. Cannot sync.")
    else:
        from google_sheets_writer import check_if_synced_this_week
        
        with st.spinner("Checking if data is already up-to-date..."):
            try:
                already_synced = check_if_synced_this_week()
            except Exception as e:
                already_synced = False
                st.toast(f"Error checking sheet: {e}")
                
        if already_synced:
            st.sidebar.info("✅ Everything is relevant! The data for this week was already saved recently. No need to update.")
        else:
            progress_bar = st.sidebar.progress(0)
            status_text = st.sidebar.empty()
            
            with st.spinner("Syncing all 20 hubs to Google Sheets... This will take a few minutes."):
                for i, hub in enumerate(HUBS_LIST):
                    status_text.text(f"Syncing {hub} ({i+1}/{len(HUBS_LIST)})...")
                    try:
                        result = fetch_and_parse_data(hub, api_key) # Do not cache this for the sync
                        if not result.get("error"):
                            write_weekly_data(result["sync_payload"])
                    except Exception as e:
                        st.toast(f"Failed to sync {hub}: {e}")
                    time.sleep(2) # Prevent rate limits
                    progress_bar.progress((i + 1) / len(HUBS_LIST))
                
                status_text.text("All hubs synced successfully! ✅")
                st.sidebar.success("🎉 Google Sheets Sync Complete!")

if fetch_button:
    if not username.strip():
        st.sidebar.error("⚠️ Please select an Instagram Username.")
    elif not api_key.strip():
        st.sidebar.error("⚠️ RAPIDAPI_KEY is missing. Please add it to your `.env` file.")
    else:
        with st.spinner("Fetching data from Instagram APIs... This might take a moment."):
            try:
                # API Calls and Parsing via scraper.py
                result = cached_fetch_and_parse(username, api_key)
                
                if result.get("error"):
                    st.warning(result["error"])
                    if "raw_data" in result:
                        st.json(result["raw_data"])
                    st.stop()
                    
                followers = result["followers"]
                total_posts = result["total_posts"]
                processed_posts = result["processed_posts"]

                # 3. Data Processing & Tabular View
                df = pd.DataFrame(processed_posts)

                if df.empty:
                    st.warning("Dataframe is empty after parsing. Check the JSON structure.")
                    st.stop()

                # Calculate Average Engagement Rate
                avg_er = df["Engagement Rate (%)"].mean()

                # ----------------------------------------------------------------------
                # 2. KPI Metrics Panel (Top Row)
                # ----------------------------------------------------------------------
                st.markdown("### 🏆 Core Metrics")
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric(label="Total Subscribers (Followers)", value=f"{followers:,}")
                kpi2.metric(label="Total Posts", value=f"{total_posts:,}")
                kpi3.metric(label="Average Engagement Rate (Latest Posts)", value=f"{avg_er:.2f}%")
                
                # ER Evaluation Logic based on follower count
                if followers < 10000:
                    if avg_er >= 3.0: er_msg, er_state = "🟢 **Excellent ER!** Your audience is highly engaged.", "success"
                    elif avg_er >= 1.5: er_msg, er_state = "🟡 **Average ER.** Result is moderate. You should consider experimenting with your content plan to improve engagement.", "warning"
                    else: er_msg, er_state = "🔴 **Low ER.** Your content plan needs immediate improvement to engage your followers.", "error"
                elif followers < 100000:
                    if avg_er >= 2.0: er_msg, er_state = "🟢 **Excellent ER!** High engagement for this follower bracket.", "success"
                    elif avg_er >= 1.0: er_msg, er_state = "🟡 **Average ER.** Solid performance, but room to grow with new content strategies.", "warning"
                    else: er_msg, er_state = "🔴 **Low ER.** Consider adjusting your content plan to revive your audience.", "error"
                else:
                    if avg_er >= 1.5: er_msg, er_state = "🟢 **Excellent ER!** Fantastic engagement for a large account.", "success"
                    elif avg_er >= 0.7: er_msg, er_state = "🟡 **Average ER.** Normal engagement levels for this tier.", "warning"
                    else: er_msg, er_state = "🔴 **Low ER.** Try more interactive formats like Reels or polls to improve.", "error"
                
                if er_state == "success": st.success(er_msg)
                elif er_state == "warning": st.warning(er_msg)
                else: st.error(er_msg)
                
                st.divider()
                # Create Tabs for different views
                tab_data, tab_charts, tab_intelligence = st.tabs([
                    "🗂️ Data View", 
                    "📊 Interactive Visualizations", 
                    "💡 Content Intelligence"
                ])

                # ----------------------------------------------------------------------
                # Tab 1: Tabular View
                # ----------------------------------------------------------------------
                with tab_data:
                    st.subheader("Cleaned Dataset")
                    
                    # Apply background gradient to engagement columns
                    cols_to_color = ['Likes', 'Comments', 'Engagement Rate (%)']
                    if df['Views'].notna().any():
                        cols_to_color.append('Views')
                    styled_df = df.style.background_gradient(subset=cols_to_color, cmap='Blues')
                    
                    st.dataframe(
                        styled_df, 
                        width='stretch',
                        column_config={
                            "Engagement Rate (%)": st.column_config.NumberColumn(format="%.2f%%"),
                            "Post URL": st.column_config.LinkColumn("Link")
                        }
                    )

                # ----------------------------------------------------------------------
                # Tab 2: Interactive Visualizations
                # ----------------------------------------------------------------------
                with tab_charts:
                    st.header("📈 Historical Timeline (Google Sheets)")
                    from google_sheets_writer import read_historical_data
                    import pandas as pd
                    
                    try:
                        with st.spinner("Loading historical data..."):
                            history = read_historical_data(account_name=username)
                            
                        if len(history) > 0:
                            df_hist = pd.DataFrame(history)
                            df_hist['parsed_at'] = pd.to_datetime(df_hist['parsed_at'])
                            df_hist = df_hist.sort_values(by="parsed_at").reset_index(drop=True)
                            
                            if len(df_hist) > 1:
                                latest = df_hist.iloc[-1]
                                previous = df_hist.iloc[-2]
                                
                                delta_followers = int(latest["followers"] - previous["followers"])
                                delta_posts = int(latest["total_posts"] - previous["total_posts"])
                                delta_er = float(latest["avg_er"] - previous["avg_er"])
                                
                                st.subheader("Week-over-Week Growth")
                                h_col1, h_col2, h_col3 = st.columns(3)
                                h_col1.metric("Followers", f"{latest['followers']:,}", f"{delta_followers:,}")
                                h_col2.metric("Total Posts", f"{latest['total_posts']:,}", f"{delta_posts:,}")
                                h_col3.metric("Avg Engagement Rate", f"{latest['avg_er']:.2f}%", f"{delta_er:.2f}%")
                                
                                st.subheader("Trends")
                                t_col1, t_col2 = st.columns(2)
                                with t_col1:
                                    fig_f = px.line(df_hist, x="parsed_at", y="followers", markers=True, title="Followers Growth", color_discrete_sequence=['#405DE6'])
                                    st.plotly_chart(fig_f, width='stretch')
                                    
                                    fig_p = px.line(df_hist, x="parsed_at", y="total_posts", markers=True, title="Total Posts Over Time", color_discrete_sequence=['#F56040'])
                                    st.plotly_chart(fig_p, width='stretch')
                                    
                                with t_col2:
                                    fig_er = px.line(df_hist, x="parsed_at", y="avg_er", markers=True, title="Avg Engagement Rate Over Time", color_discrete_sequence=['#E1306C'])
                                    st.plotly_chart(fig_er, width='stretch')
                            else:
                                st.info("📊 We need at least 2 weeks of data to calculate growth and trends. Check back next week after the next sync!")
                        else:
                            st.warning("⚠️ No historical data found for this hub in Google Sheets. Please sync the data first to start tracking growth over time!")
                    except EnvironmentError as cred_err:
                        st.warning(f"🔑 Google Sheets not connected: {cred_err}")
                        
                    st.divider()
                    st.header("📊 Latest Post Analysis")
                    chart_col1, chart_col2 = st.columns(2)

                    with chart_col1:
                        st.subheader("Engagement Breakdown: Likes vs Comments")
                        # Melt the dataframe to have Likes and Comments in the same column for grouped bar chart
                        df_melted = df.melt(
                            id_vars=['Shortcode'], 
                            value_vars=['Likes', 'Comments'], 
                            var_name='Metric', 
                            value_name='Count'
                        )
                        fig_bar = px.bar(
                            df_melted, 
                            x='Shortcode', 
                            y='Count', 
                            color='Metric', 
                            barmode='group',
                            color_discrete_sequence=['#E1306C', '#405DE6'] # Instagram-ish colors
                        )
                        fig_bar.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig_bar, width='stretch')

                    with chart_col2:
                        st.subheader("Content Format Distribution")
                        format_counts = df['Format'].value_counts().reset_index()
                        format_counts.columns = ['Format', 'Count']
                        fig_pie = px.pie(
                            format_counts, 
                            names='Format', 
                            values='Count', 
                            hole=0.4, # Donut chart
                            color_discrete_sequence=px.colors.sequential.Agsunset
                        )
                        st.plotly_chart(fig_pie, width='stretch')

                # ----------------------------------------------------------------------
                # Tab 3: Actionable Content Intelligence
                # ----------------------------------------------------------------------
                with tab_intelligence:
                    st.subheader("🔥 Top 3 Performing Posts")
                    st.markdown("Based on total engagement (Likes + Comments).")
                    
                    df['Total Engagement'] = df['Likes'] + df['Comments']
                    top_3_posts = df.sort_values(by='Total Engagement', ascending=False).head(3)

                    for index, row in top_3_posts.iterrows():
                        with st.container():
                            col_img, col_info = st.columns([1, 4])
                            with col_img:
                                st.markdown(f"### `#{row['Shortcode']}`")
                                st.markdown(f"📅 **{row['Post Date']}**")
                                st.caption(f"Format: {row['Format']}")
                            
                            with col_info:
                                if row.get('Post URL'):
                                    st.markdown(f"**[🔗 View Post on Instagram]({row['Post URL']})**")
                                st.write(f"**Total Engagement:** {row['Total Engagement']:,}")
                                st.write(f"- **Likes:** {row['Likes']:,}")
                                st.write(f"- **Comments:** {row['Comments']:,}")
                                if pd.notna(row.get('Views')):
                                    st.write(f"- **Views:** {int(row['Views']):,}")
                                
                                # Shorten text caption
                                raw_caption = str(row['Caption'])
                                short_caption = (raw_caption[:150] + '...') if len(raw_caption) > 150 else raw_caption
                                st.info(f"**Caption Snippet:** {short_caption}")
                        st.divider()

            except requests.exceptions.Timeout:
                st.error("🚨 API Connection Timeout: The request to RapidAPI took too long. Please try again.")
            except requests.exceptions.HTTPError as http_err:
                st.error(f"🚨 HTTP Error occurred: {http_err} - Check your API key and username.")
            except requests.exceptions.RequestException as req_err:
                st.error(f"🚨 Request Exception: {req_err}")
            except KeyError as key_err:
                st.error(f"🚨 Data Parsing Error: Missing expected key in the JSON response: {key_err}")
            except Exception as e:
                st.error(f"🚨 An unexpected error occurred: {e}")
else:
    st.info("👈 Select an Instagram Username and click 'Fetch Live Metrics' to get started!")
