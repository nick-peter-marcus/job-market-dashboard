# job-market-dashboard

## Introduction
In this project, I gather and explore data from the German job market in the field of data science. The results will be showcased in a dashboard.

## Approach
### 1. Data collection
Data has been gathered from various job boards, searching for the keywords "Data Science" and specifying the location to be "Germany". The data collection took place between 09.12.2024 - 13.12.2024.

### 2. Data cleaning and preparation
In the next steps, the collected data was thoroughly cleaned. The code is provided in a subdirectory of this repository [(here)](data/data_cleaning/data_cleaning.ipynb).
1. First, the job ads were anonymized, removing any reference to personal data (e.g. names, email addresses, telephone numbers). 
2. Duplicates were removed by comparing categorical columns as well as the written job description. The latter was performed by utilizing the Levenshtein string similarity algorithm.
3. Columns were cleaned and added, e.g.
    - Tech stack requirement: Keyword search (e.g. "Python") in written job description.
    - Job title category: Grouping task handed to ChatPGT.
    - Geodata: Extracting coordinates of job locations for future mapping.
4. Finally, the cleaned data was stored twice - in the original format, and in long format. The latter guarantees proper filtering of the data in the dashboard application.

### 3. Building a dashboard in Streamlit
Based on the cleaned datasets, a dashboard was created using the Streamlit API.
The dashboard features dynamic filtering, interactive plotly charts, extracts from the data based on applied filters, as well as a wordcloud representing the written job descriptions.
The dashboard is hosted Streamlit Community Cloud and can be publicly accessed via [this link](https://job-market-dashboard.streamlit.app/).

## Screenshots
![main_page](https://github.com/nick-peter-marcus/job-market-dashboard/blob/main/images/main_page.png?raw=true)
![data_tab](https://github.com/nick-peter-marcus/job-market-dashboard/blob/main/images/data_tab.png?raw=true)
![wordcloud](https://github.com/nick-peter-marcus/job-market-dashboard/blob/main/images/wordcloud.png?raw=true)