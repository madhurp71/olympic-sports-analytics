from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Olympic Insights", page_icon="🏅", layout="wide")
NAVY, GOLD, BLUE = "#101C33", "#F5C451", "#3977C3"
st.markdown(f"""
<style>
.stApp{{background:linear-gradient(180deg,#f7f9fc,#edf2f8);color:#1c2940}}
[data-testid="stSidebar"]{{background:linear-gradient(180deg,{NAVY},#233d61)}}
[data-testid="stSidebar"] *{{color:#f4f7fc}}
.hero{{background:linear-gradient(115deg,{NAVY},#31567d);padding:1.5rem 1.8rem;border-radius:18px;color:white;border-bottom:5px solid {GOLD};margin-bottom:1rem}}
.hero h1{{color:white;margin:0}} .hero p{{color:#dce6f4;margin:.4rem 0 0}}
div[data-testid="stMetric"]{{background:white;border:1px solid #dfe6ef;padding:14px;border-radius:14px}}
.stTabs [data-baseweb="tab"]{{background:#e6ecf4;border-radius:9px 9px 0 0;padding:9px}}
.stTabs [aria-selected="true"]{{background:white!important;border-top:3px solid {GOLD}}}
</style>""", unsafe_allow_html=True)

HERE = Path(__file__).resolve().parent
ATHLETE_FILE, NOC_FILE = HERE / "athlete_events.csv", HERE / "noc_regions.csv"

@st.cache_data
def load_data(path, noc_path):
    raw = pd.read_csv(path)
    meta = {"source_rows": len(raw), "source_columns": len(raw.columns),
            "duplicate_rows": int(raw.duplicated().sum())}
    data = raw.drop_duplicates().copy()
    for col in ["ID", "Year", "Age", "Height", "Weight"]:
        if col in data: data[col] = pd.to_numeric(data[col], errors="coerce")
    if Path(noc_path).exists():
        try:
            noc = pd.read_csv(noc_path)
            if {"NOC", "region"}.issubset(noc.columns):
                data = data.merge(noc[["NOC","region"]].drop_duplicates("NOC"), on="NOC", how="left")
                data["Country"] = data["region"].fillna(data["Team"])
            else: data["Country"] = data["Team"]
        except Exception: data["Country"] = data["Team"]
    else: data["Country"] = data["Team"]
    return data, meta

if not ATHLETE_FILE.exists():
    st.error("Cannot find athlete_events.csv. Put app.py and the CSV files in the same folder.")
    st.code("python -m streamlit run app.py")
    st.stop()
try:
    df, meta = load_data(str(ATHLETE_FILE), str(NOC_FILE))
except Exception as e:
    st.error(f"Could not read the CSV: {e}")
    st.stop()

st.markdown("""<div class="hero"><h1>🏅 OLYMPIC INSIGHTS</h1>
<p>Sports Performance Analytics · Exploring Olympic history from 1896–2016</p></div>""", unsafe_allow_html=True)
st.info("**Objective:** Explore how participation and medal-winning records vary by year, sport, country, sex and athlete demographics. These are descriptive patterns, not proof of cause and effect.")

# Sidebar: interactive filters
st.sidebar.title("🎛️ Dashboard controls")
st.sidebar.caption("Change filters to update all relevant charts.")
years = sorted(int(y) for y in df.Year.dropna().unique())
yr = st.sidebar.slider("Olympic year range", min(years), max(years), (min(years), max(years)))
seasons = sorted(df.Season.dropna().unique().tolist())
sel_seasons = st.sidebar.multiselect("Season", seasons, default=seasons)
sexes = sorted(df.Sex.dropna().unique().tolist())
sel_sexes = st.sidebar.multiselect("Sex", sexes, default=sexes)
sports = sorted(df.Sport.dropna().unique().tolist())
sel_sports = st.sidebar.multiselect("Sports", sports, default=sports)
countries = sorted(df.Country.dropna().astype(str).unique().tolist())
sel_countries = st.sidebar.multiselect("Countries / regions", countries, default=countries)
medal_options = ["Gold","Silver","Bronze","No recorded medal"]
sel_medals = st.sidebar.multiselect("Medal category", medal_options, default=medal_options)
st.sidebar.caption("Source: Kaggle 120 Years of Olympic History; dataset ends in 2016.")

f = df[df.Year.between(*yr) & df.Season.isin(sel_seasons) & df.Sex.isin(sel_sexes)
       & df.Sport.isin(sel_sports) & df.Country.astype(str).isin(sel_countries)].copy()
if "No recorded medal" not in sel_medals:
    f = f[f.Medal.isin(sel_medals)]
elif len(sel_medals) < 4:
    chosen = [m for m in sel_medals if m in ["Gold","Silver","Bronze"]]
    f = f[f.Medal.isin(chosen) | f.Medal.isna()]
if f.empty:
    st.warning("No records match these filters. Select more years, sports or countries.")
    st.stop()
medals = f[f.Medal.isin(["Gold","Silver","Bronze"])].copy()

a,b,c,d = st.columns(4)
a.metric("Athlete-event records", f"{len(f):,}", help="A row is an athlete-event record, not necessarily a unique person.")
b.metric("Unique athlete IDs", f"{f.ID.nunique():,}")
c.metric("Sports represented", f"{f.Sport.nunique():,}")
d.metric("Medal-winning records", f"{len(medals):,}", help="Rows with Gold, Silver or Bronze recorded.")
st.download_button("⬇️ Download filtered CSV", f.drop(columns=["region"],errors="ignore").to_csv(index=False).encode("utf-8"),
                   "olympic_filtered_data.csv", "text/csv")

overview, medal_tab, demo, compare, quality = st.tabs(
    ["📊 Overview","🥇 Medal analysis","🧍 Demographics","🌍 Country comparison","🔎 Data quality & critique"])

with overview:
    st.subheader("Participation through time")
    metric = st.radio("Trend metric", ["Athlete-event records","Medal-winning records"], horizontal=True)
    src = medals if metric == "Medal-winning records" else f
    trend = src.groupby(["Year","Season"]).size().reset_index(name="Records")
    fig = px.line(trend,x="Year",y="Records",color="Season",markers=True,title=f"{metric} by Olympic year",
                  template="plotly_white",color_discrete_sequence=[BLUE,GOLD])
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig,use_container_width=True)
    n = st.slider("How many top sports?",5,20,10)
    sport_metric = st.selectbox("Rank sports by",["Athlete-event records","Medal-winning records"])
    sport_src = medals if sport_metric == "Medal-winning records" else f
    top = sport_src.Sport.value_counts().head(n).sort_values().rename_axis("Sport").reset_index(name="Records")
    fig = px.bar(top,x="Records",y="Sport",orientation="h",color="Records",title=f"Top {n} sports",
                 color_continuous_scale=["#c7d7eb",NAVY],template="plotly_white")
    fig.update_layout(yaxis={"categoryorder":"total ascending"},coloraxis_showscale=False)
    st.plotly_chart(fig,use_container_width=True)
    st.subheader("Findings from your current filters")
    if not trend.empty:
        peak = trend.loc[trend.Records.idxmax()]
        st.markdown(f"- Highest count in this selection: **{int(peak.Year)} ({peak.Season})**, with **{int(peak.Records):,}** {metric.lower()}.")
    if not medals.empty:
        st.markdown(f"- Most represented medal-winning sport: **{medals.Sport.value_counts().index[0]}**.")
        st.markdown(f"- Highest medal-winning record count by country/region: **{medals.Country.value_counts().index[0]}**.")
    st.markdown(f"- This selection covers **{f.Sport.nunique()} sports** and **{f.Country.nunique()} countries/regions**.")
    st.markdown("- These are descriptive counts; participation levels and the number of events can affect comparisons.")

with medal_tab:
    st.subheader("Medal-winning records")
    n = st.slider("Number of countries to display",5,25,12)
    cc = medals.Country.value_counts().head(n).sort_values().rename_axis("Country / region").reset_index(name="Records")
    fig = px.bar(cc,x="Records",y="Country / region",orientation="h",color="Records",
                 title=f"Top {n} countries/regions",color_continuous_scale=["#ead9a4","#a87912"],template="plotly_white")
    fig.update_layout(yaxis={"categoryorder":"total ascending"},coloraxis_showscale=False)
    st.plotly_chart(fig,use_container_width=True)
    sex_count = medals.groupby("Sex").size().reset_index(name="Records")
    fig = px.bar(sex_count,x="Sex",y="Records",color="Sex",title="Medal-winning records by sex",
                 color_discrete_map={"M":BLUE,"F":"#D95D5D"},template="plotly_white")
    st.plotly_chart(fig,use_container_width=True)
    mix = medals.Medal.value_counts().reindex(["Gold","Silver","Bronze"]).fillna(0).rename_axis("Medal").reset_index(name="Records")
    fig = px.bar(mix,x="Medal",y="Records",color="Medal",
                 color_discrete_map={"Gold":"#D5A21C","Silver":"#9CA7B5","Bronze":"#A76D43"},
                 title="Gold, silver and bronze records",template="plotly_white")
    st.plotly_chart(fig,use_container_width=True)
    st.caption("These are athlete-event rows with medals recorded, not counts of unique physical medals. Team events can have multiple athlete rows for one medal-winning event.")
with demo:
    st.subheader("Athlete demographics")
    age_data = f.dropna(subset=["Age"])
    fig = px.histogram(age_data,x="Age",nbins=30,marginal="box",title="Age distribution (histogram + box plot)",
                       color_discrete_sequence=[BLUE],template="plotly_white")
    st.plotly_chart(fig,use_container_width=True)
    hw = f.dropna(subset=["Height","Weight"]).copy()
    if len(hw)>5000: hw=hw.sample(5000,random_state=42)
    if not hw.empty:
        fig = px.scatter(hw,x="Height",y="Weight",color="Sex",hover_data=["Name","Sport","Year","Country"],
                         title="Height vs weight (up to 5,000 records)",opacity=.65,template="plotly_white",
                         labels={"Height":"Height (cm)","Weight":"Weight (kg)"})
        st.plotly_chart(fig,use_container_width=True)
    else: st.info("No records with both height and weight for the current selection.")
    ages = f.dropna(subset=["Age"])
    if not ages.empty:
        top_sports = ages.Sport.value_counts().head(12).index
        fig = px.box(ages[ages.Sport.isin(top_sports)],x="Sport",y="Age",color="Sex",
                     title="Age distribution by sport (top 12 selected sports)",points=False,template="plotly_white")
        fig.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig,use_container_width=True)
with compare:
    st.subheader("Compare two countries/regions")
    available = sorted(f.Country.dropna().astype(str).unique())
    if len(available)<2:
        st.info("Select at least two countries/regions in the sidebar.")
    else:
        ca = st.selectbox("Country A",available,index=0)
        cb = st.selectbox("Country B",available,index=1)
        cm = st.radio("Comparison metric",["Medal-winning records","Athlete-event records"],horizontal=True)
        src = medals if cm=="Medal-winning records" else f
        comp = src[src.Country.astype(str).isin([ca,cb])].groupby(["Year","Country"]).size().reset_index(name="Records")
        if not comp.empty:
            fig=px.line(comp,x="Year",y="Records",color="Country",markers=True,title=f"{cm}: {ca} vs {cb}",template="plotly_white")
            st.plotly_chart(fig,use_container_width=True)
        st.subheader("Country-by-year heatmap")
        hn=st.slider("Countries in heatmap",5,25,12)
        if not medals.empty:
            topc=medals.Country.value_counts().head(hn).index
            pivot=medals[medals.Country.isin(topc)].pivot_table(index="Country",columns="Year",values="ID",aggfunc="count",fill_value=0)
            if not pivot.empty:
                fig=px.imshow(pivot,aspect="auto",color_continuous_scale="YlOrBr",
                              labels={"x":"Year","y":"Country / region","color":"Medal-winning records"},
                              title="Medal-winning records by country and year",template="plotly_white")
                st.plotly_chart(fig,use_container_width=True)
with quality:
    st.subheader("Data quality: missing does not mean fake")
    st.markdown("""
**Missing values do not automatically mean the dataset is fake.** They mean a field is not available in this copy of the data. Do not invent ages, heights or weights.

**Medal is different:** a blank medal generally means no Gold, Silver or Bronze is recorded for that athlete-event row. Many participants do not win medals, so blank medal values are expected and are not automatically data errors. Filter to Gold/Silver/Bronze when analysing medal-winning records.
""")
    q1,q2,q3=st.columns(3)
    q1.metric("Rows in source CSV",f"{meta['source_rows']:,}")
    q2.metric("Exact duplicate rows detected",f"{meta['duplicate_rows']:,}")
    q3.metric("Rows in analysis copy",f"{len(df):,}")
    missing=pd.DataFrame({"Column":df.columns,"Missing values":[int(df[col].isna().sum()) for col in df.columns]})
    missing["Missing %"]=(missing["Missing values"]/len(df)*100).round(2)
    missing=missing.sort_values("Missing values",ascending=False)
    nonzero=missing[missing["Missing values"]>0]
    if not nonzero.empty:
        fig=px.bar(nonzero.sort_values("Missing %"),x="Missing %",y="Column",orientation="h",text="Missing %",
                   color="Missing %",color_continuous_scale=["#f3d88c","#d95d5d"],title="Missing values by column (%)",template="plotly_white")
        fig.update_traces(texttemplate="%{text:.2f}%",textposition="outside")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig,use_container_width=True)
    st.dataframe(missing,use_container_width=True,hide_index=True)
    st.subheader("Potential outliers: IQR screening")
    st.caption("Outliers are values to investigate, not automatic mistakes. Do not delete them without a reason.")
    outs=[]
    for col in ["Age","Height","Weight"]:
        vals=df[col].dropna()
        if len(vals):
            q1v,q3v=vals.quantile(.25),vals.quantile(.75)
            iqr=q3v-q1v
            outs.append({"Variable":col,"Lower boundary":round(float(q1v-1.5*iqr),2),
                         "Upper boundary":round(float(q3v+1.5*iqr),2),
                         "Potential outliers":int(((vals<q1v-1.5*iqr)|(vals>q3v+1.5*iqr)).sum())})
    st.dataframe(pd.DataFrame(outs),use_container_width=True,hide_index=True)
    st.subheader("Appropriate vs misleading chart")
    st.write("A fair bar chart uses a zero baseline. A truncated axis can exaggerate differences.")
    mix=medals.Medal.value_counts().reindex(["Gold","Silver","Bronze"]).fillna(0).rename_axis("Medal").reset_index(name="Records")
    if not mix.empty:
        left,right=st.columns(2)
        with left:
            fig=px.bar(mix,x="Medal",y="Records",title="Appropriate: zero baseline",color="Medal",
                       color_discrete_map={"Gold":"#D5A21C","Silver":"#9CA7B5","Bronze":"#A76D43"},template="plotly_white")
            fig.update_yaxes(range=[0,max(1,float(mix.Records.max())*1.12)])
            st.plotly_chart(fig,use_container_width=True)
        with right:
            fig=px.bar(mix,x="Medal",y="Records",title="Misleading: truncated axis",color="Medal",
                       color_discrete_map={"Gold":"#D5A21C","Silver":"#9CA7B5","Bronze":"#A76D43"},template="plotly_white")
            low=max(0,float(mix.Records.min())*.8)
            if mix.Records.max()>low: fig.update_yaxes(range=[low,float(mix.Records.max())*1.05])
            st.plotly_chart(fig,use_container_width=True)
        st.warning("The second chart deliberately truncates the axis to exaggerate visible differences. It is an example of what not to do.")
    st.subheader("AI critique and team decision")
    st.write("**Chart reviewed:** medal-winning records by country. **AI recommendation:** use a sorted horizontal bar chart, label the metric and time period, and start the count axis at zero. This improves readability and avoids exaggerated differences.")
    st.write("**Suggested team decision: ACCEPT after verification.** Confirm the chart counts athlete-event rows with medals, not distinct physical medals. Your team should review the recommendation and change the decision if you disagree.")
    st.subheader("Three actionable recommendations")
    st.markdown("""
1. **Improve data completeness:** report missing age, height and weight; do not invent replacements.
2. **Make fair comparisons:** compare similar years, seasons and event contexts; raw medal counts do not account for participation.
3. **Improve communication:** show the time range, filters, units and metric definition beside every chart.
""")

st.markdown("<p style='text-align:center;color:#65738a;font-size:.8rem;padding:18px'>Olympic Insights · Student analytics project · Kaggle 120 Years of Olympic History · Descriptive analysis, not causal inference</p>",unsafe_allow_html=True)
