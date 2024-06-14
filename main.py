import requests
import json
import re
import random
import newspaper

import streamlit as st

import pandas as pd
from transformers import BartTokenizer, BartForConditionalGeneration
from openai import OpenAI

st.set_page_config(layout="wide")

OPENAI_API_KEY = st.secrets["openai"]["api_key"]
llm = OpenAI(api_key=OPENAI_API_KEY)

@st.cache_resource
def load_model():
    tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
    model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")
    return model, tokenizer

# Logic
@st.cache_data
def surf_web(search_query):
    base_url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "Accept-Encoding": "gzip", "X-Subscription-Token": st.secrets["brave_search"]["subscription_token"]}

    r = requests.get(base_url, headers=headers, params={"q": search_query})

    if not r.status_code == 200:
        raise Exception(f"Error: {r.status_code}")

    json_data = r.json()

    with open("response.json", "w", encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    return json_data

def remove_html_tags(text):
    # Regular expression to match HTML tags
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def remove_quotation_marks(text):
    return text.replace('&quot;', '')

def generate_summary(text, max_length=512, min_length=30):
    model, tokenizer = load_model()

    inputs = tokenizer(text, return_tensors='pt', max_length=max_length, truncation=True)
    summary_ids = model.generate(inputs['input_ids'], max_length=max_length, min_length=min_length, length_penalty=1.0, num_beams=4, early_stopping=True)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

@st.cache_data
def search_results_to_dataframe(search_results):
    results = search_results["web"]["results"]

    data = {"url": [], "title": [], "website_name": [], "description": [], "content": [], "summary": []}
    for result in results:
        data["url"].append(result["url"])
        data["title"].append(result["title"])
        data["website_name"].append(result["profile"]["name"])
        description = result["description"] # a little bit of processing
        data["description"].append(remove_html_tags(remove_quotation_marks(description)))

        try:
            article = newspaper.article(result["url"])
            data["content"].append(article.text)
        except Exception as e:
            data["content"].append(None)
            data["summary"].append(None)
            print(e)
            continue

        data["summary"].append(generate_summary(article.text))

    return pd.DataFrame(data)

def select_article_identifier(article_dict):
    if article_dict.get("summary") and "Something went wrong" not in article_dict["summary"]:
        return article_dict["summary"]
    else:
        return article_dict["title"]

@st.cache_data
def group_search_results(results_df):
    random_ind = random.sample(range(len(results_df)), 10)

    article_information = []
    for ind in random_ind:
        random_sample = results_df.loc[ind]

        if random_sample["summary"] and "Something went wrong" not in random_sample["summary"]:
            article_information.append(random_sample["summary"])
        else:
            article_information.append(random_sample["title"])

    messages = [
        {
            "role": "user",
            "content": f"I will give you 10 headlines or article summaries. I want you to give me a scale that would \
                let me plot these news articles on a graph. This scale can be, for example, left, right, or center \
                    of the political spectrum. want you to give me five groups for me to place these articles in. Please \
                        list the categories as comma-separated values. Here are 10 articles: \
                            {article_information}."
        },
    ]

    response = response = llm.chat.completions.create(
        model="gpt-4",
        messages=messages
    )

    scale = response.choices[0].message.content.strip("\"")

    messages.append({
        "role": "system",
        "content": scale,
    })

    grouped_data = {group.strip("\'\"[]").strip(): [] for group in scale.split(",")}

    for _, row in results_df.iterrows():
        messages.append(
            {
                "role": "user",
                "content": f"Given this scale you've provided, please categorize the following article given \
                    the summary: {select_article_identifier(row)}. Please only output the category name."
            }
        )

        response = llm.chat.completions.create(
            model="gpt-4",
            messages=messages
        )

        from pprint import pprint
        pprint(response)

        group = response.choices[0].message.content.strip("\"\'").strip()
        grouped_data[group].append(
            {
                "url": row["url"],
                "title": row["title"],
                "website_name": row["website_name"],
                "summary": row["summary"]
            }
        )

    return grouped_data

def main():
    # UI
    query = st.text_input("Search the web privately...")
    # num_results = st.slider("Number of results", min_value=10, max_value=100, value=20)
    if query:
        results = surf_web(query)
        results_df = search_results_to_dataframe(results)
        grouped_results = group_search_results(results_df)

        col1, col2, col3, col4, col5 = st.columns(5)
        group1, group2, group3, group4, group5 = grouped_results.keys()

        with col1:
            st.write(group1)
            for result in grouped_results[group1]:
                if st.button(result["website_name"], key=result["url"]):
                    st.session_state["search_result"] = result
        with col2:
            st.write(group2)
            for result in grouped_results[group2]:
                if st.button(result["website_name"], key=result["url"]):
                    st.session_state["search_result"] = result
        with col3:
            st.write(group3)
            for result in grouped_results[group3]:
                if st.button(result["website_name"], key=result["url"]):
                    st.session_state["search_result"] = result

        with col4:
            st.write(group4)
            for result in grouped_results[group4]:
                if st.button(result["website_name"], key=result["url"]):
                    st.session_state["search_result"] = result
        
        with col5:
            st.write(group5)
            for result in grouped_results[group5]:
                if st.button(result["website_name"], key=result["url"]):
                    st.session_state["search_result"] = result

        
        with st.sidebar:
            if not st.session_state.get("search_result"):
                st.write("Click a button to view the search result here.")
            else:
                st.write(f'## {st.session_state["search_result"]["title"]}')
                st.write(f'{st.session_state["search_result"]["summary"]}')
                st.markdown(f"[Go to this page]({st.session_state['search_result']['url']})", unsafe_allow_html=True)


if __name__ == '__main__':
    main()
