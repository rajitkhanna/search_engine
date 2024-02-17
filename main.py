import streamlit as st
from pprint import pprint
import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
from textblob import TextBlob

def get_search_query():
    query = st.text_input("Search the web privately...")
    # st.write("The current search query is", query)
    return query

def surf_web(search_query):
    if not search_query:
        return None

    base_url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "Accept-Encoding": "gzip", "X-Subscription-Token": "BSAgRHUnJd0xjZoUVv1He5kfswtRVrM"}

    r = requests.get(base_url, headers=headers, params={"q": search_query})

    json_data = r.json()

    with open("response.json", "w", encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    return json_data

def process_results(results):
    if not results:
        return None

    results = results["web"]["results"]

    data = {"url": [], "title": [], "profile_name": []}
    for result in results:
        data["url"].append(result["url"])
        data["title"].append(result["title"])
        data["profile_name"].append(result["profile"]["name"])

    df = pd.DataFrame(data)

    return df

def save_website_data(df):
    if df is None:
        return

    for ind in df.index:
        url = df["url"][ind]
        name = df["profile_name"][ind]
        html = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}).text
        soup = BeautifulSoup(html, "html.parser")

        textblob = TextBlob(soup.get_text().replace("\n", ""))
        df.loc[ind, "polarity"] = textblob.sentiment.polarity
        df.loc[ind, "subjectivity"] = textblob.sentiment.subjectivity

        with open(f"data/{name}.txt", "w") as f:
            f.write(soup.get_text().replace("\n", ""))

    st.write(df)

def main():
    search_query = get_search_query()
    results = surf_web(search_query)
    results = process_results(results)
    save_website_data(results)

if __name__ == '__main__':
    main()
