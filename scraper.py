import requests
from datetime import datetime

def get_instagram_profile(user, key):
    """Fetch profile metrics from instagram-looter2 /profile endpoint."""
    url = "https://instagram-looter2.p.rapidapi.com/profile"
    querystring = {"username": user}
    headers = {
        "X-RapidAPI-Key": key,
        "X-RapidAPI-Host": "instagram-looter2.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring, timeout=15)
    response.raise_for_status()
    return response.json()

def find_key(data, target_key):
    """Recursively search for a key in a nested dictionary/list."""
    if isinstance(data, dict):
        if target_key in data:
            return data[target_key]
        for v in data.values():
            res = find_key(v, target_key)
            if res is not None:
                return res
    elif isinstance(data, list):
        for item in data:
            res = find_key(item, target_key)
            if res is not None:
                return res
    return None

def fetch_and_parse_data(username, api_key):
    """
    Fetches raw profile data and parses it into a structured format
    suitable for both the Streamlit UI and the Google Sheets sync.
    """
    profile_data = get_instagram_profile(username, api_key)

    # -- Parse Profile Metrics --
    followers_data = find_key(profile_data, 'edge_followed_by')
    followers = followers_data.get('count', 0) if isinstance(followers_data, dict) else 0
    if not followers: followers = find_key(profile_data, 'follower_count') or 0

    posts_node = find_key(profile_data, 'edge_owner_to_timeline_media')
    total_posts = posts_node.get('count', 0) if isinstance(posts_node, dict) else 0
    if not total_posts: total_posts = find_key(profile_data, 'media_count') or 0

    # -- Parse Posts Metrics --
    edges = posts_node.get('edges', []) if isinstance(posts_node, dict) else []
    
    if not edges:
        edges = find_key(profile_data, 'edges') or []

    if not edges:
        return {"error": "No posts found or the API response structure was unexpected.", "raw_data": profile_data}

    processed_posts = []
    
    for item in edges:
        node = item.get('node', item) if isinstance(item, dict) else {}
        
        shortcode = node.get('shortcode', 'Unknown')
        
        is_video = node.get('is_video', False)
        format_type = "Reel/Video" if is_video else "Static Image"
        
        likes_data = node.get('edge_liked_by') or node.get('edge_media_preview_like') or {}
        likes = likes_data.get('count', 0) if isinstance(likes_data, dict) else 0
        if not likes: likes = node.get('like_count', 0)
            
        comments_data = node.get('edge_media_to_comment') or {}
        comments = comments_data.get('count', 0) if isinstance(comments_data, dict) else 0
        if not comments: comments = node.get('comment_count', 0)
            
        views = node.get('video_view_count') if is_video else None
            
        caption = ""
        caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
        if caption_edges and isinstance(caption_edges, list):
            caption = caption_edges[0].get('node', {}).get('text', '')
        elif 'caption' in node:
            caption_data = node.get('caption')
            if isinstance(caption_data, str):
                caption = caption_data
            elif isinstance(caption_data, dict):
                caption = caption_data.get('text', '')
        
        timestamp = find_key(node, 'taken_at_timestamp')
        post_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M') if timestamp else "Unknown Date"
        
        post_url = f"https://www.instagram.com/p/{shortcode}/" if shortcode != 'Unknown' else ""
        
        engagement_rate = ((likes + comments) / followers * 100) if followers > 0 else 0.0

        processed_posts.append({
            "Post Date": post_date,
            "Shortcode": shortcode,
            "Post URL": post_url,
            "Format": format_type,
            "Views": views,
            "Likes": likes,
            "Comments": comments,
            "Engagement Rate (%)": round(engagement_rate, 4),
            "Caption": caption
        })

    # Sort processed posts by total engagement for top3 logic
    sorted_posts = sorted(processed_posts, key=lambda p: p["Likes"] + p["Comments"], reverse=True)
    top_3_raw = sorted_posts[:3]

    top3_formatted = []
    for i, p in enumerate(top_3_raw):
        # API requires Format: "Reel" or "Static" based on prompt
        fmt = "Reel" if "Reel" in p["Format"] else "Static"
        top3_formatted.append({
            "rank": i + 1,
            "shortcode": p["Shortcode"],
            "format": fmt,
            "likes": p["Likes"],
            "comments": p["Comments"],
            "views": p["Views"] if p["Views"] is not None else 0,
            "er": round(p["Engagement Rate (%)"], 2)
        })

    avg_er = sum(p["Engagement Rate (%)"] for p in processed_posts) / len(processed_posts) if processed_posts else 0.0

    # Build the final structured payload as requested by the user
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    sync_payload = {
        "account": username,
        "parsed_at": now_str,
        "followers": followers,
        "total_posts": total_posts,
        "avg_er": round(avg_er, 2),
        "top3": top3_formatted
    }

    return {
        "error": None,
        "followers": followers,
        "total_posts": total_posts,
        "processed_posts": processed_posts,
        "sync_payload": sync_payload
    }
