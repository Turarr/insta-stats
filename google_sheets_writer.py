import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    
    if creds_json:
        import json
        # Parse the JSON string from the environment variable
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    elif os.path.exists("credentials.json"):
        # Fallback to local file if environment variable isn't set
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    else:
        raise EnvironmentError(
            "Google Sheets credentials not configured. "
            "Please set the GOOGLE_CREDENTIALS_JSON secret in your Streamlit Cloud app settings "
            "(App settings → Secrets), or provide a credentials.json file for local development."
        )
        
    return gspread.authorize(creds)

def check_if_synced_this_week(spreadsheet_name="Instagram Analytics Data", account_name="astana.hub"):
    """Check if the sheet was already synced within the last 5 days."""
    client = get_gspread_client()
    sheet_id_or_name = os.environ.get("SPREADSHEET_ID")
    
    if sheet_id_or_name:
        try:
            sh = client.open_by_key(sheet_id_or_name)
        except gspread.exceptions.SpreadsheetNotFound:
            try:
                sh = client.open(sheet_id_or_name)
            except gspread.exceptions.SpreadsheetNotFound:
                return False
    else:
        try:
            sh = client.open(spreadsheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            return False

    try:
        worksheet = sh.worksheet(account_name)
    except gspread.exceptions.WorksheetNotFound:
        return False
        
    col_a = worksheet.col_values(1)
    if len(col_a) <= 1:
        return False # Empty or only headers
        
    last_date_str = col_a[-1]
    try:
        last_date = datetime.strptime(last_date_str, '%Y-%m-%d %H:%M')
        if datetime.now() - last_date < timedelta(days=5):
            return True # Data is recent (less than 5 days old)
    except ValueError:
        pass
        
    return False

def write_weekly_data(data, spreadsheet_name="Instagram Analytics Data"):
    client = get_gspread_client()
    
    # Try to open by ID or Name from env, fallback to default name
    sheet_id_or_name = os.environ.get("SPREADSHEET_ID")
    if sheet_id_or_name:
        try:
            sh = client.open_by_key(sheet_id_or_name)
        except gspread.exceptions.SpreadsheetNotFound:
            # If it failed, they probably typed the name instead of the ID
            try:
                sh = client.open(sheet_id_or_name)
            except gspread.exceptions.SpreadsheetNotFound:
                sh = client.create(sheet_id_or_name)
    else:
        try:
            sh = client.open(spreadsheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            sh = client.create(spreadsheet_name)
    
    account_name = data["account"]
    
    try:
        worksheet = sh.worksheet(account_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=account_name, rows="1000", cols="15")
        # Add headers
        worksheet.update(
            values=[[
                'parsed_at', 'followers', 'total_posts', 'avg_er', '',
                'parsed_at', 'rank', 'shortcode', 'format', 'likes', 'comments', 'views', 'er'
            ]],
            range_name='A1'
        )
    
    col_a = worksheet.col_values(1)
    col_f = worksheet.col_values(6)
    
    next_row_a = len(col_a) + 1
    next_row_f = len(col_f) + 1
    
    # Zone 1 Update (A to D)
    zone1_data = [
        data["parsed_at"],
        data["followers"],
        data["total_posts"],
        data["avg_er"]
    ]
    worksheet.update(values=[zone1_data], range_name=f'A{next_row_a}')
    
    # Zone 2 Update (F to M)
    zone2_data = []
    for post in data["top3"]:
        zone2_data.append([
            data["parsed_at"],
            post["rank"],
            post["shortcode"],
            post["format"],
            post["likes"],
            post["comments"],
            post["views"],
            post["er"]
        ])
    
    if zone2_data:
        worksheet.update(values=zone2_data, range_name=f'F{next_row_f}')

    return True

def read_historical_data(spreadsheet_name="Instagram Analytics Data", account_name="astana.hub"):
    """Reads historical Zone 1 metrics for a given hub to generate timeline charts."""
    client = get_gspread_client()
    sheet_id_or_name = os.environ.get("SPREADSHEET_ID")
    
    if sheet_id_or_name:
        try:
            sh = client.open_by_key(sheet_id_or_name)
        except gspread.exceptions.SpreadsheetNotFound:
            try:
                sh = client.open(sheet_id_or_name)
            except gspread.exceptions.SpreadsheetNotFound:
                return []
    else:
        try:
            sh = client.open(spreadsheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            return []

    try:
        worksheet = sh.worksheet(account_name)
    except gspread.exceptions.WorksheetNotFound:
        return []
        
    all_values = worksheet.get_all_values()
    if len(all_values) <= 1:
        return []
        
    history = []
    for row in all_values[1:]:
        if len(row) >= 4 and str(row[0]).strip():
            try:
                # Replace comma decimal separator (e.g. "1,7" in Russian locale) with period
                avg_er_str = str(row[3]).replace('%', '').replace(',', '.').strip()
                history.append({
                    "parsed_at": str(row[0]).strip(),
                    "followers": int(str(row[1]).replace(',', '').replace('.', '').strip() or 0),
                    "total_posts": int(str(row[2]).replace(',', '').replace('.', '').strip() or 0),
                    "avg_er": float(avg_er_str or 0.0)
                })
            except Exception as parse_err:
                import logging
                logging.warning(f"Skipping unparseable row in history: {row} — {parse_err}")
    return history
