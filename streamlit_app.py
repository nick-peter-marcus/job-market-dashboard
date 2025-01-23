import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck
import math
import matplotlib.pyplot as plt
import numpy as np
from streamlit_dynamic_filters import DynamicFilters
from wordcloud import WordCloud, STOPWORDS


# Load dataframes
df_raw = pd.read_csv(f"data/job_data.csv", index_col=0)
df_raw.index.name = "ID"

df_long = pd.read_csv(f"data/job_data_long.csv")
df_long = df_long.fillna("N/A")


# Rescale initial size of location count bubbles shown in map
def initial_size_scale(x, low, high):
    if max(x) == min(x): return low
    return (high - low)*(x - min(x)) / (max(x) - min(x)) + low
low, high = (6500, 30000)

df_raw["location_count_initial"] = df_raw["location_clean"] \
    .map(df_raw["location_clean"].value_counts())
df_raw["location_size_initial"] = initial_size_scale(np.sqrt(df_raw["location_count_initial"]), low, high)


def create_data_table(data: pd.DataFrame, column_in: str, column_out: str) -> pd.DataFrame:
    """ 
    Creates a dataframe containg counts and percentages of a specified column.

    Args:
        data:       Original dataframe used to draw the data from.
        column_in:  Name of column to be addressed in data.
        column_out: Column name in returned dataframe that contains
                    the unique values (keys) from the input column.

    Returns:
        A dataframe containing columns [column_out], "Count" and "Percent".
    """
    data_keys = data[column_in].unique().tolist()
    data_keys = [k for k in data_keys if k != "-"]

    data_counts = data[column_in].value_counts()

    data_table = pd.DataFrame({column_out: data_keys})
    data_table["Count"] = data_table[column_out].map(data_counts)
    data_table["Percent"] = round(data_table["Count"] / n_rows_filtered * 100, 1)
    data_table = data_table.sort_values(by="Count", ascending=False)

    return data_table



####  FILTERS  ####
###################

filters_dict = {
    "location_clean": "Location",
    "title_cat_ChatGPT": "Job Title",
    "seniority_level_5": "Seniority Level",
    "days_online_grouped": "Days Online",
    "job_type": "Job/Contract Type",
    "tech_stack": "Tech Stack"
}

df_long = df_long.rename(columns=filters_dict)

# Create dynamic filters class
dynamic_filters = DynamicFilters(df_long, filters=filters_dict.values())

# Update dataframes
df_long_filtered = pd.DataFrame(dynamic_filters.filter_df())
df_long_filtered_ids = df_long_filtered["id"].unique()
df = df_raw.loc[df_long_filtered_ids]

n_rows_filtered = len(df)


#### DATA TABLE ####
####################

# Define data output shown in dashboard (tab "Data")
data_table_columns = ["company_clean", 
                      "title", 
                      "location_clean",
                      "date_posted"]
data_table_df = df.filter(data_table_columns)
data_table_df = data_table_df.sort_values(by=["location_clean", "company_clean", "title"])

data_table_column_styler = {
    "company_clean": st.column_config.Column(label="Company", width="medium"),
    "title": st.column_config.Column(label="Job title", width="large"), 
    "location_clean": st.column_config.Column(label="Location", width="small"),
    "date_posted": st.column_config.Column(label="Date posted", width="small"),
}


####  LOCATION GEODATA/MAP  ####
################################

### PREPARE DATA

# Generate aggregated dataframe with coordinates and count
aggregation_functions = {"location_lat": "min", 
                         "location_long": "min", 
                         "location_clean": "count",
                         "location_count_initial": "min",
                         "location_size_initial": "min"}
df_location_agg = df.groupby("location_clean").agg(aggregation_functions)
df_location_agg = df_location_agg.rename(columns={"location_clean": "location_count"})
df_location_agg["location"] = df_location_agg.index.to_list()

# Make bubbles representing cities with more than 10 listings more transparent
def set_alpha(count):
    if count > 10: return [255,75,75,160]
    return [255,75,75,200]
df_location_agg["location_color"] = df_location_agg["location_count"].apply(set_alpha)
df_location_agg["location_size"] = df_location_agg["location_size_initial"]

# Highlight city if only 1 is selected and count is low
if len(df_location_agg) == 1 and df_location_agg["location_count"][0] < 10:
    df_location_agg["location_size"] = df_location_agg["location_size_initial"] * 1.5
    df_location_agg["location_color"] = [[255,75,75,245]]

# Update bubble size if other filters aside from location have been selected.
check_filters = ["Job Title", "Seniority Level", "Days Online"]
update_bubble_size_on = any(len(st.session_state["filters"][cf]) > 0 for cf in check_filters)

# Rescale size of bubbles if more than 1 city is selected
def rescale_size(row, low, high):
    min_count = min(df_location_agg["location_count"])
    max_count = max(df_location_agg["location_count"])
    if min_count == max_count:
        return row["location_size_initial"]
    row_value = row["location_count"]
    scaled = (high - low)*(math.sqrt(row_value) - min_count) / (max_count - min_count) + low
    return scaled

low, high = (6500, 30000)
if len(df_location_agg) > 1 and update_bubble_size_on:
    df_location_agg["location_size"] = df_location_agg \
        .apply(lambda row: rescale_size(row, low, high), axis=1)


### DRAW MAP

# Define map parameters
point_layer = pydeck.Layer(
    "ScatterplotLayer",
    data=df_location_agg,
    id="job-locations",
    get_position=["location_long", "location_lat"],
    get_color="location_color",
    pickable=True,
    auto_highlight=True,
    get_radius="location_size",
)
# Define initial viewstate and geo position (here: Germany)
view_state_lat, view_state_long = (51.1638175, 10.4478313)
view_state = pydeck.ViewState(
    latitude=view_state_lat, 
    longitude=view_state_long, 
    controller=True, 
    zoom=4.25
)
# Create map
chart = pydeck.Deck(
    point_layer,
    initial_view_state=view_state,
    tooltip={"text": "{location}\nJob count: {location_count}"},
    map_style=None,
    height=200,
)


#### TECH STACK ####
####################

tech_stack_table = create_data_table(df_long_filtered, "Tech Stack", "Technology")

tech_stack_fig = px.bar(tech_stack_table, x="Technology", y="Count",
                        hover_data=["Technology", "Count", "Percent"])


#### JOB TITLE ####
###################

job_title_table = create_data_table(df, "title_cat_ChatGPT", "Job Title")

job_title_fig = px.pie(job_title_table,
                       names="Job Title",
                       values="Count",
                       hole=0.35)
job_title_fig.update_traces(textposition='inside', textinfo='percent+label')


#### SENIORITY ####
###################

seniority_table = create_data_table(df, "seniority_level_5", "Seniority")

seniority_order = ['Entry level', 'Associate/Mid-Level', 'Senior', 'Director', 'Postdoc']

seniority_fig = px.pie(seniority_table,
                       names="Seniority", 
                       values="Count",
                       hole=0.35,
                       category_orders={"Seniority": seniority_order})
seniority_fig.update_traces(textposition='inside', textinfo='percent+label')


#### JOB TYPE ####
##################

job_type_table = create_data_table(df_long_filtered, "Job/Contract Type", "Job Type")

job_type_fig = px.bar(job_type_table,
                      x="Job Type", y="Count",
                      hover_data=["Job Type", "Count", "Percent"],
                      )


#### DAYS ONLINE ####
#####################

days_online_table = create_data_table(df, "days_online_grouped", "Days Online")

days_online_fig = px.bar(
    days_online_table,
    x="Days Online", y="Count",
    hover_data=["Days Online", "Count", "Percent"]
)
days_online_order = ["0-7", "8-14", "15-21", "22-28", "29+"]
days_online_fig.update_layout(xaxis={'categoryorder': 'array', 
                                     'categoryarray': days_online_order})


#### NUMBER APPLICANTS ####
###########################

number_applicants_fig = px.histogram(
    df, x="number_applicants", nbins=5
)
number_applicants_fig.update_layout(bargap=0.2)



#### APP LAYOUT ####
####################

st.set_page_config(layout="wide", page_title="Job Market Dashboard")

# SIDEBAR
dynamic_filters.display_filters(location='sidebar')

with st.sidebar:
    st.html(f"<i>{len(df)}/{len(df_raw)} jobs selected</i>")
    st.button("Reset Filters", type="primary", on_click=dynamic_filters.reset_filters)

# CSS STYLING
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            width: 244px !IMPORTANT;
        }
        [data-testid="stSidebarHeader"] {
	        padding: 0;
        }
        [data-testid="stHeader"] {
            height: 0;
        }
        [data-testid="stMainBlockContainer"] {
            padding-left: 2rem;
            padding-right: 2rem;
            padding-top: 0;
            padding-bottom: 1rem;
        }
        div.st-emotion-cache-fsammq p {
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)


# DASHBOARD CONTENT
tab1, tab2, tab3 = st.tabs(["Graphs", "Data", "Wordcloud"])

### TAB 1: Technology, Job Type ; title, seniority level, days_online
with tab1:
    cols_tab1 = st.columns((4, 2.5), gap='medium')
    
    # TAB 1 -> COLUMN 1:
    with cols_tab1[0]:
        # TAB 1 -> COLUMN 1 -> CONTAINER 1:
        with st.container(border=True, height=260):
            cols_tab1_subcols = st.columns((1.25, 2.75), gap="medium")
            # TAB 1 -> COLUMN 1 -> CONTAINER 1 -> COLUMN 1:
            with cols_tab1_subcols[0]:
                job_title_fig.update_layout(height=210,
                                            margin=dict(t=30, b=0, l=5, r=5),
                                            showlegend=False,
                                            title={'text': "Job Title",
                                                   'y':0.988, 'x':0.5,
                                                   'xanchor': 'center',
                                                   'yanchor': 'top'})
                st.plotly_chart(job_title_fig, 
                                config={'displayModeBar': False},
                                key="job_title_fig")
                
            # TAB 1 -> COLUMN 1 -> CONTAINER 1 -> COLUMN 2:
            with cols_tab1_subcols[1]:
                tech_stack_fig.update_layout(height=228,
                                            margin=dict(t=20, b=0, l=0, r=0),
                                            yaxis_title=None,
                                            xaxis_title=None,
                                            title={'text': "Tech Stack",
                                                   'y':0.988, 'x':0.5,
                                                   'xanchor': 'center',
                                                   'yanchor': 'top'})
                tech_stack_fig.update_xaxes(tickangle=-45, tickfont=dict(size=10))
                st.plotly_chart(tech_stack_fig,
                                config={'displayModeBar': False},
                                key="tech_stack_fig")

        # TAB 1 -> COLUMN 1 -> CONTAINER 2:
        with st.container(border=True, height=260):
            col02 = st.columns((1.25, 2.75), gap="medium")

            # TAB 1 -> COLUMN 1 -> CONTAINER 2 -> COLUMN 1:
            with col02[0]:
                seniority_fig.update_layout(height=210,
                                            margin=dict(t=30, b=0, l=5, r=5),
                                            showlegend=False,
                                            title={'text': "Level of Seniority",
                                                   'y':0.988, 'x':0.5,
                                                   'xanchor': 'center',
                                                   'yanchor': 'top'})        
                st.plotly_chart(seniority_fig, 
                                config={'displayModeBar': False},
                                key="seniority_fig")

            # TAB 1 -> COLUMN 1 -> CONTAINER 2 -> COLUMN 2:
            with col02[1]:
                job_type_fig.update_layout(height=228,
                                        margin=dict(t=20, b=0, l=0, r=0),
                                        yaxis_title=None,
                                        xaxis_title=None,
                                        title={'text': "Job Type",
                                               'y':0.988, 'x':0.5,
                                               'xanchor': 'center',
                                               'yanchor': 'top'})
                job_type_fig.update_xaxes(tickangle=-45, tickfont=dict(size=10))
                st.plotly_chart(job_type_fig,
                                config={'displayModeBar': False},
                                key="job_type_fig")    
                
        # TAB 1 -> COLUMN 1 -> CONTAINER 3:
        with st.container(border=True, height=260):
            col03 = st.columns((2, 2), gap="medium")

            # TAB 1 -> COLUMN 1 -> CONTAINER 3 -> COLUMN 1:
            with col03[0]:
                days_online_fig.update_layout(height=228,
                                            margin=dict(t=20, b=0, l=0, r=0),
                                            yaxis_title=None,
                                            xaxis_title=None,
                                            title={'text': "Number of Days Online",
                                                   'y':0.988, 'x':0.5,
                                                   'xanchor': 'center',
                                                   'yanchor': 'top'})
                st.plotly_chart(days_online_fig, 
                                config={'displayModeBar': False},
                                key="days_online_fig")
                
            # TAB 1 -> COLUMN 1 -> CONTAINER 3 -> COLUMN 2:
            with col03[1]:
                number_applicants_fig.update_layout(height=228,
                                                    margin=dict(t=20, b=0, l=0, r=0),
                                                    yaxis_title=None,
                                                    xaxis_title=None,
                                                    title={'text': "Number of Applicants",
                                                           'y':0.988, 'x':0.5,
                                                           'xanchor': 'center',
                                                           'yanchor': 'top'})
                st.plotly_chart(number_applicants_fig, 
                                config={'displayModeBar': False},
                                key="number_applicants_fig")


    # TAB 1 -> COLUMN 2:
    with cols_tab1[1]:
        with st.container(border=True, height=460):
            st.pydeck_chart(chart, height=428)

        with st.expander("About this dashboard", expanded=True):
            st.write("""
                - **Data**: Collected on 3 different job search sites. 
                     - Keywords: "Data Scientist"
                     - Location: "Germany"
                     - Accessed: 09.12.2024 - 13.12.2024
                - **Duplicates**: The original dataset contained 1625 postings across all platforms. 193 listings were flagged as duplicates and have been dropped.
                - **Job Titles**: Original job titles were categorized using ChatGPT.
                - **Job Descriptions**: All personal data and contact details have been removed.
                """)



# TAB 2: FILTERED DATAFRAME
with tab2:
    st.dataframe(data_table_df, 
                 use_container_width=True, 
                 column_config=data_table_column_styler)



# TAB 3: WORDCLOUD
with tab3:
    cols_tab3 = st.columns((1.5, 6), gap='small')
    # TAB 3 -> COLUMN 1:
    with cols_tab3[0]:
        st.write("Click 'Generate Wordcloud' to create the wordcloud.")
        st.write("""Note that if filters are changed, the wordcloud will be cleared. 
                 In order to reflect changes to the filtered data, please generate the 
                 wordcloud again, or activate 'Auto update wordcloud'.""")

        # Create wordcloud once
        if 'generate_wordcloud' not in st.session_state:
            st.session_state.generate_wordcloud = False
        def generate_wordcloud():
            st.session_state.generate_wordcloud = True

        st.button("Generate Wordcloud", type="primary", on_click=generate_wordcloud)

        # Auto-update option
        if 'auto_update_wordcloud' not in st.session_state:
            st.session_state.auto_update_wordcloud = False
        def auto_update_wordcloud():
            st.session_state.auto_update_wordcloud = not st.session_state.auto_update_wordcloud

        st.toggle("Auto update wordcloud", 
                  value=st.session_state.auto_update_wordcloud, 
                  on_change=auto_update_wordcloud)

    # TAB 3 -> COLUMN 2:
    with cols_tab3[1]:
        with st.container(border=True, height=400):

            @st.cache_data
            def create_wordcloud(text_column):
                stopwords = set(STOPWORDS)
                stopwords.update(["und", "oder", "der", "die", "das", "den", "dem", "des", "dass",
                                "zu", "zur", "mit", "auf", "aus", "um", "in", "im", "über", "wie", "sowie",
                                "bei", "von", "für", "durch", "auch", "dabei", "wo", "als", "nach",
                                "Du", "Sie", "wir", "Deine", "Ihre", "dir", "sich", "dich", "es",
                                "uns", "unsere", "unser", "unseren", "unserer", "us",
                                "ist", "bist", "sind", "hast", "haben", "will",
                                "einem", "einer", "einen", "ein", "eine", "eines", "one", 
                                "re", "etc", "un", "de", "al",
                                "c", "e", "g", "s", "u", "ll", "w", "d", "m", "w", "z", "B"])
                
                wc = WordCloud(
                    stopwords=stopwords,
                    background_color = 'white',
                    width = 2000,
                    height = 950,
                    min_font_size=10
                    )
            
                text = " ".join(text_column)

                wordcloud = wc.generate(text)
                fig, ax = plt.subplots()
                ax.imshow(wordcloud)
                plt.axis("off")
                return fig            

            if st.session_state.generate_wordcloud and not st.session_state.auto_update_wordcloud:
                wordcloud = create_wordcloud(df["job_description_anonymized"])
                st.pyplot(wordcloud)
                st.session_state.generate_wordcloud = False
            
            if st.session_state.auto_update_wordcloud:
                wordcloud = create_wordcloud(df["job_description_anonymized"])
                st.pyplot(wordcloud)
    