import json
import random
from concurrent.futures import ThreadPoolExecutor

import newspaper
import requests
import streamlit as st
from together import Together

st.set_page_config(layout="wide")

client = Together(api_key=st.secrets["togetherai"]["api_key"])

config = newspaper.Config()
config.REQUEST_TIMEOUT = 10
config.browser_user_agent = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0"
)
config.max_summary_sent = 3


# Logic
@st.cache_data
def surf_web(search_query):
    base_url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": st.secrets["brave_search"]["subscription_token"],
    }

    r = requests.get(base_url, headers=headers, params={"q": search_query})

    if not r.status_code == 200:
        raise Exception(f"Error: {r.status_code}")

    json_data = r.json()

    return json_data


def download_article(url, website_name, title, description):
    article = newspaper.Article(url, config=config)
    try:
        article.download()
        article.parse()
        article.nlp()
    except Exception as e:
        print(f"Failed to download {url}: {e}")
    finally:
        article.title = title
        article.meta_site_name = website_name
        article.meta_description = description
        return article


@st.cache_data
def download_articles(search_results):
    results = search_results["web"]["results"]

    data = {"url": [], "title": [], "website_name": [], "description": []}

    for result in results:
        data["url"].append(result["url"])
        data["title"].append(result["title"])
        data["website_name"].append(result["profile"]["name"])
        data["description"].append(result["description"])

    with ThreadPoolExecutor(max_workers=10) as executor:
        articles = list(
            executor.map(
                download_article,
                data["url"],
                data["website_name"],
                data["title"],
                data["description"],
            )
        )

    article_information = []
    for article in articles:
        article_information.append(
            {
                "url": article.url,
                "title": article.title,
                "description": article.meta_description,
                "website_name": article.meta_site_name,
                "summary": article.summary,
            }
        )
    return article_information


@st.cache_data
def group_articles(articles):
    article_information = []
    for article in articles:
        if not article["summary"] or "Something went wrong" in article["summary"]:
            article_information.append(
                f"Title: {article['title']}\n Description: {article['description']}\n Url: {article['url']}"
            )
        else:
            article_information.append(
                f"Title: {article['title']}\n Summary: {article['summary']}\n Url: {article['url']}"
            )

    messages = [
        {
            "role": "user",
            "content": f"I will give you 20 headlines or article summaries. I want you to \
            give me a scale that would let me plot these news articles on a graph. I \
            want you to give me five groups for me to place these articles in. Avoid using \
            the words Unclear, Miscellaneous, or Unrelated in a category name. Groups that \
            include opposing viewpoints should be as far apart on the x-axis as possible. Here \
            are the 20 articles: {article_information}.\
            Here is the format of your response: \
            1. <Group 1> \
            - Article: <Article x url> \
            - Article: <as many articles as you put in this category> \
            2. <Group 2> \
            - Article: <Article y url> \
            - Article: <as many articles as you put in this category> \
            3. <Group 3> \
            - Article: <Article z url> \
            - Article: <as many articles as you put in this category> \
            4. <Group 4> \
            - Article: <Article k url> \
            - Article: <as many articles as you put in this category> \
            5. <Group 5> \
            - Article: <Article l url> \
            - Article: <as many articles as you put in this category>",
        },
    ]
        
    response = client.chat.completions.create(
        model="meta-llama/Llama-3-70b-chat-hf",
        messages=messages,
    )

    lines = response.choices[0].message.content.split("\n")

    curr_group = ""
    grouped_articles = {}
    for i in range(len(lines)):
        line = lines[i].strip("**")
        if line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or line.startswith("4.") or line.startswith("5."):
            curr_group = line.split(". ")[1]
            grouped_articles[curr_group] = []   
        elif line.startswith("- Article:"):
            url = line.split("Article: ")[1]
            article = [article for article in articles if article["url"] == url][0]
            grouped_articles[curr_group].append(article)
        else:
            continue

    return grouped_articles


def main():
    # UI
    query = st.text_input("Search the web privately...")
    if query:
        results = surf_web(query)
        articles = download_articles(results)
        grouped_articles = group_articles(articles)

        col1, col2, col3, col4, col5 = st.columns(5)

        group1, group2, group3, group4, group5 = grouped_articles.keys()

        with col1:
            st.write(group1)
            for article in grouped_articles[group1]:
                if st.button(article["website_name"], help=article["title"], key=article["url"]):
                    st.session_state["search_result"] = article
                    
        with col2:
            st.write(group2)
            for article in grouped_articles[group2]:
                if st.button(article["website_name"], help=article["title"], key=article["url"]):
                    st.session_state["search_result"] = article

        with col3:
            st.write(group3)
            for article in grouped_articles[group3]:
                if st.button(article["website_name"], help=article["title"], key=article["url"]):
                    st.session_state["search_result"] = article

        with col4:
            st.write(group4)
            for article in grouped_articles[group4]:
                if st.button(article["website_name"], help=article["title"], key=article["url"]):
                    st.session_state["search_result"] = article

        with col5:
            st.write(group5)
            for article in grouped_articles[group5]:
                if st.button(article["website_name"], help=article["title"], key=article["url"]):
                    st.session_state["search_result"] = article

        with st.sidebar:
            if not st.session_state.get("search_result"):
                st.write("Click a button to view the search result here.")
            else:
                st.write(f'## {st.session_state["search_result"]["title"]}')
                st.write(f'{st.session_state["search_result"]["summary"]}')
                st.markdown(
                    f"[Go to this page]({st.session_state['search_result']['url']})",
                    unsafe_allow_html=True,
                )


if __name__ == "__main__":
    main()
