from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time
import re

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
}

CTA_WORDS = [
    "call", "quote", "book", "contact", "enquire", "enquiry",
    "get started", "request", "schedule", "appointment"
]

def normalize_url(url):
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url

def get_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return url

def safe_request(url):
    start = time.time()
    response = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
    elapsed = time.time() - start
    return response, elapsed

def extract_page_data(html):
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    meta_description = meta_description_tag.get("content", "").strip() if meta_description_tag else ""

    viewport_tag = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
    h1_tag = soup.find("h1")
    h1_text = h1_tag.get_text(" ", strip=True) if h1_tag else ""

    body_text = soup.get_text(" ", strip=True).lower()
    images = soup.find_all("img")
    buttons_and_links = soup.find_all(["a", "button"])

    cta_matches = []
    for element in buttons_and_links:
        text = element.get_text(" ", strip=True).lower()
        if any(word in text for word in CTA_WORDS):
            cta_matches.append(text)

    return {
        "title": title,
        "meta_description": meta_description,
        "has_viewport": viewport_tag is not None,
        "has_h1": bool(h1_text),
        "h1_text": h1_text,
        "image_count": len(images),
        "cta_matches": cta_matches,
        "text_length": len(body_text)
    }

def score_website(url, response_time, page_data, html_size):
    score = 50
    issues = []
    priorities = []
    business_impact = []

    if url.startswith("https://"):
        score += 10
    else:
        issues.append("Website is not using HTTPS")
        priorities.append("Secure the site with HTTPS")

    if page_data["title"] and len(page_data["title"]) >= 10:
        score += 10
    else:
        issues.append("Weak or missing page title")
        priorities.append("Improve the page title for clarity and trust")

    if page_data["meta_description"] and len(page_data["meta_description"]) >= 50:
        score += 10
    else:
        issues.append("Missing or weak meta description")
        priorities.append("Add a stronger meta description")

    if page_data["has_viewport"]:
        score += 10
    else:
        issues.append("Missing mobile viewport tag")
        priorities.append("Improve mobile compatibility")

    if page_data["has_h1"]:
        score += 10
    else:
        issues.append("Missing clear main heading")
        priorities.append("Add a strong homepage headline")

    if len(page_data["cta_matches"]) > 0:
        score += 10
    else:
        issues.append("Weak or missing call-to-action")
        priorities.append("Add stronger CTA buttons and links")

    if response_time < 1.5:
        score += 10
    elif response_time < 3:
        score += 5
    else:
        issues.append("Slow response time")
        priorities.append("Improve page speed")

    if html_size > 800000:
        score -= 8
        issues.append("Page appears heavy in size")
        priorities.append("Reduce heavy assets and improve load speed")

    if page_data["image_count"] == 0:
        issues.append("Very limited visual content")
        priorities.append("Add stronger visual hierarchy")

    if page_data["text_length"] < 400:
        issues.append("Low content depth or weak messaging")
        priorities.append("Improve service explanation and trust signals")

    score = max(45, min(95, score))

    if score >= 75:
        lost_customers = "4–8 per month"
        extra_clients = "2–4 extra clients/month"
        summary = "Your website has a decent base, but it could guide visitors more clearly toward calling, booking, or enquiring."
        business_impact = [
            "Some visitors may hesitate before contacting you",
            "Your call-to-action could be stronger",
            "There are likely easy conversion wins available"
        ]
    elif score >= 60:
        lost_customers = "8–14 per month"
        extra_clients = "3–6 extra clients/month"
        summary = "Your homepage likely has noticeable conversion friction that could reduce calls, bookings, and enquiries."
        business_impact = [
            "Visitors may leave before taking action",
            "Mobile users may not see the next step clearly",
            "The page likely feels functional but not conversion-focused"
        ]
    else:
        lost_customers = "12–18 per month"
        extra_clients = "4–9 extra clients/month"
        summary = "Your homepage likely has avoidable friction and may be losing enquiries before visitors ever take the next step."
        business_impact = [
            "Visitors may leave early due to weak clarity",
            "Trust may feel lower on first impression",
            "The page likely needs a stronger action path"
        ]

    if len(priorities) < 3:
        fallback_priorities = [
            "Clarify the first screen message",
            "Strengthen the main call-to-action",
            "Improve mobile readability",
        ]
        for item in fallback_priorities:
            if item not in priorities:
                priorities.append(item)
            if len(priorities) == 3:
                break

    return {
        "score": score,
        "issues": issues[:4],
        "priorities": priorities[:3],
        "summary": summary,
        "lost_customers": lost_customers,
        "extra_clients": extra_clients,
        "business_impact": business_impact,
        "domain": get_domain(url),
        "response_time_ms": round(response_time * 1000),
        "html_size_kb": round(html_size / 1024),
        "cta_found": len(page_data["cta_matches"]) > 0
    }

@app.route("/scan", methods=["POST"])
def scan():
    data = request.get_json()
    raw_url = data.get("url", "").strip()

    if not raw_url:
        return jsonify({"error": "Missing URL"}), 400

    try:
        url = normalize_url(raw_url)
        response, response_time = safe_request(url)

        final_url = response.url
        html = response.text
        html_size = len(response.content)
        page_data = extract_page_data(html)
        result = score_website(final_url, response_time, page_data, html_size)

        return jsonify({
            "success": True,
            "url": final_url,
            "result": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)