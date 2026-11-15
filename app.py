import json
import base64
import html
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from engine import budget_breakdown
ROOT = Path(__file__).parent
st.set_page_config(page_title='MyMongol · Mongolia', page_icon='🌿', layout='wide')


translations=json.loads((ROOT/'data/translations.json').read_text(encoding='utf-8'))
brand_col, nav_col, lang_col = st.columns([1.5,4.5,1.7], vertical_alignment='center')
with brand_col:
    st.markdown('<div class="steppe-brand"><svg width="36" height="28" viewBox="0 0 60 42" fill="none" aria-hidden="true"><path d="M3 36 20 14 27 23 35 5 57 36 43 28 35 18 28 29 20 24 3 36Z" stroke="#b99556" stroke-width="3" stroke-linejoin="round"/></svg><span>MyMongol</span></div>', unsafe_allow_html=True)
with lang_col:
    language=st.segmented_control('Language / Хэл',['English','Монгол'],default='English',key='language',label_visibility='collapsed') or 'English'
with nav_col:
    page=st.segmented_control('Navigation',['Discover','Destination details','My plan','About the data'],key='navigation',default='Discover',label_visibility='collapsed',format_func=lambda v:translations.get(v,v) if language=='Монгол' else v) or 'Discover'

def T(value):
    if language=='Монгол' and isinstance(value,str):return translations.get(value,value)
    return str(value)

def display_table(frame, columns):
    table = frame[columns].copy()
    if language == 'Монгол':
        if 'Place' in columns:
            table['Place'] = frame['Газрын нэр']
        for column in columns:
            if column not in ['Place', 'Match (%)']:
                table[column] = table[column].map(lambda value: ', '.join(T(part.strip()) for part in str(value).split(',')))
        table = table.rename(columns={column:T(column) for column in columns})
    return table

@st.cache_data
def load(path_stamp):
    mn = pd.read_excel(ROOT / 'data/mongolia_trip.xlsx', sheet_name='Монгол').dropna(how='all')
    en = pd.read_excel(ROOT / 'data/mongolia_trip.xlsx', sheet_name='English').dropna(how='all')
    if en.ID.duplicated().any() or mn['№'].duplicated().any():
        raise ValueError('Duplicate destination IDs')
    data = en.merge(mn[['№', 'Газрын нэр']], left_on='ID', right_on='№', validate='one_to_one')
    points=pd.read_csv(ROOT/'data/map_locations.csv')
    data=data.merge(points[['ID','Latitude','Longitude','Pin type','Fallback area']],on='ID',how='left',validate='one_to_one')
    data['tags'] = data['Interest tags'].apply(lambda x: [v.strip() for v in x.split(',')])
    return data

def months(text):
    mapping = {'Jun–Sep': [6, 7, 8, 9], 'Jul–Aug': [7, 8], 'May–Sep': [5, 6, 7, 8, 9], 'Year-round': list(range(1, 13)), 'Jun–Sep; Feb–Mar (ice)': [2, 3, 6, 7, 8, 9], 'May–Jun; Sep': [5, 6, 9], 'Unknown': []}
    if text not in mapping:
        raise ValueError('Unknown month label: ' + text)
    return mapping[text]
try:
    data = load(((ROOT / 'data/mongolia_trip.xlsx').stat().st_mtime, (ROOT / 'data/map_locations.csv').stat().st_mtime))
except Exception as e:
    st.error(f'Could not load dataset: {e}')
    st.stop()
def show_map(places, single=False):
    points=places.dropna(subset=['Latitude','Longitude']).copy()
    points=points[points.Latitude.between(-90,90)&points.Longitude.between(-180,180)]
    missing=places[places[['Latitude','Longitude']].isna().any(axis=1)]
    if not missing.empty:
        with st.expander('Байршил нь тодорхойгүй газрууд' if language=='Монгол' else 'Places still awaiting coordinates'):
            st.dataframe(missing[['Газрын нэр','Province']],hide_index=True)
    if points.empty:
        st.info('Эдгээр газрын координат хараахан нэмээгүй.' if language=='Монгол' else 'Coordinates have not been added for these places yet.')
        return
    points['Label']=points['Газрын нэр'] if language=='Монгол' else points['Place']
    fallback=points['Pin type'].eq('Soum centre')
    points['Location accuracy']=fallback.map({True:'Ойролцоо байршил — сумын төв' if language=='Монгол' else 'Approximate location — soum centre',False:'Газрын ойролцоо байршил' if language=='Монгол' else 'Landmark / area location'})
    center={'lat':float(points.Latitude.mean()),'lon':float(points.Longitude.mean())} if single else {'lat':47.5,'lon':103}
    fig=px.scatter_map(points,lat='Latitude',lon='Longitude',hover_name='Label',hover_data={'Latitude':False,'Longitude':False,'Province':False,'Fallback area':False},color='Location accuracy',color_discrete_map={'Approximate location — soum centre':'#D58B32','Ойролцоо байршил — сумын төв':'#D58B32','Landmark / area location':'#246554','Газрын ойролцоо байршил':'#246554'},zoom=9 if single else 3.6,center=center,map_style='open-street-map',height=470)
    fig.update_traces(marker={'size':14})
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
    st.plotly_chart(fig,width='stretch')

if 'saved_ids' not in st.session_state:
    st.session_state.saved_ids = []
photos = json.loads((ROOT / 'data/photos.json').read_text(encoding='utf-8'))
user_photos = json.loads((ROOT / 'data/user_photos.json').read_text(encoding='utf-8'))
photo_names = {'Алтай таван богд': 'altai', 'Увс нуур': 'uvs', 'Тэрхийн цагаан нуур': 'terkhiin', 'Хөвсгөл нуур': 'khuvsgul', 'Эрдэнэ зуу хийд': 'kharkhorin', 'Хустайн байгалийн цогцолборт газар': 'hustai', 'Ёлын ам': 'yolyn', 'Хонгорын элс': 'khongor', 'Баянзаг': 'bayanzag'}
st.markdown('<style>'+(ROOT/'assets/warm_steppe.css').read_text(encoding='utf-8')+'</style>', unsafe_allow_html=True)
hero_bytes = base64.b64encode((ROOT/'assets/warm_steppe_banner.png').read_bytes()).decode('ascii')
hero_background = f'background-image:url(data:image/png;base64,{hero_bytes});'
st.markdown(f'<section class="steppe-hero" style="{hero_background}"><div class="hero-title"><h1>{html.escape(T("Where do you want to go?"))}</h1></div></section>', unsafe_allow_html=True)

def reset_preferences():
    for key, value in {'pref_region': 'All', 'pref_province': 'All', 'pref_month': 0, 'pref_climate': 'Any', 'pref_experience': 'Any', 'pref_interests': [], 'pref_minimum': 0, 'pref_sort': 'Best interest match', 'home_province':'All'}.items():
        st.session_state[key] = value
def select_home_province():
    chosen=st.session_state.get('home_province','All')
    reset_preferences()
    st.session_state.home_province=chosen

with st.sidebar:
    if page == 'Discover':
        st.subheader('Таны сонголт' if language=='Монгол' else 'Preferences')
        interests = st.multiselect(T('Choose your interests'), sorted({t for tags in data.tags for t in tags}), key='pref_interests', placeholder='Нуур, явган аялал, түүх…' if language=='Монгол' else 'Lakes, hiking, history…', help='Places are ranked by the proportion of your selected interests they match.', format_func=T)
        experience = st.selectbox(T('Travel experience'), ['Any', 'Adventure', 'Relax', 'Scenic', 'Culture'], key='pref_experience', format_func=T)
        region = st.selectbox(T('Region'), ['All'] + sorted(data.Region.unique()), key='pref_region', format_func=T)
        available = data if region == 'All' else data[data.Region == region]
        options = ['All'] + sorted(available.Province.unique())
        if st.session_state.get('pref_province', 'All') not in options:
            st.session_state.pref_province = 'All'
        province = st.selectbox(T('Province'), options, key='pref_province', help='Province options follow your selected region.', format_func=T)
        month = st.selectbox(T('Travel month'), list(range(13)), format_func=lambda v: T('Any month') if v==0 else (str(v)+'-р сар' if language=='Монгол' else pd.Timestamp(2026,v,1).strftime('%B')), key='pref_month',help='Your month is kept as a planning preference and does not exclude places.')
        with st.expander(T('Fine-tune your results')):
            climate = st.selectbox(T('Broad climate preference'), ['Any'] + sorted((x for x in data.Climate.unique() if x != 'Unknown')), key='pref_climate', help='A broad dataset label, not weather for your selected month.', format_func=T)
            minimum = st.slider(T('Minimum interest match (%)'), 0, 100, step=10, key='pref_minimum', disabled=not interests, help='Only applies when interests are selected.')
            sort = st.selectbox(T('Sort places'), ['Best interest match', 'Place name', 'Province'], key='pref_sort', format_func=T)
        st.button(T('Reset preferences'), on_click=reset_preferences, width='stretch')
    st.divider()
    st.metric(T('Places in your plan'), len(st.session_state.saved_ids))
if page == 'Discover':
    query = ''
    home_province=st.pills(T('Choose a province'),['All']+sorted(data.Province.unique()),default='All',format_func=lambda v:T('All provinces') if v=='All' else T(v),key='home_province',label_visibility='collapsed',on_change=select_home_province) or 'All'
    r = data.copy()
    if home_province!='All':r=r[r.Province==home_province]
    if query:
        r = r[r[['Place', 'Газрын нэр', 'Province']].agg(' '.join, axis=1).str.contains(query, case=False, regex=False)]
    if region != 'All':
        r = r[r.Region == region]
    if province != 'All':
        r = r[r.Province == province]
    if climate != 'Any':
        r = r[r.Climate == climate]
    if experience != 'Any':
        r = r[r['Experience types'].apply(lambda s: experience in [t.strip() for t in s.split(',')])]
    r['matched'] = r.tags.apply(lambda tags: [t for t in interests if t in tags])
    r['Match (%)'] = r.matched.apply(lambda tags: round(100 * len(tags) / len(interests)) if interests else 0)
    r = r.sort_values(['Match (%)', 'Place'], ascending=[False, True])
    if interests:
        r = r[(r['Match (%)'] > 0) & (r['Match (%)'] >= minimum)]
    if sort == 'Place name':
        r = r.sort_values('Place')
    elif sort == 'Province':
        r = r.sort_values(['Province', 'Place'])
    choices = [x for x in [region if region != 'All' else '', province if province != 'All' else '', pd.Timestamp(2026, month, 1).strftime('%B') if month else '', experience if experience != 'Any' else ''] if x]
    if r.empty:
        st.info(T('Try removing a filter or choosing another month.'))
    cards, map_tab, compare = st.tabs([T('Places'), T('Map'), T('Compare & download')])
    with cards:
        limit = 100
        for i, row in enumerate(r.head(limit).to_dict('records')):
            if i % 3 == 0:
                cols = st.columns(3, gap='medium')
            with cols[i % 3], st.container(border=True):
                photo = photo_names.get(row['Газрын нэр'])
                uploaded = user_photos.get(str(int(row['ID'])))
                if uploaded:
                    st.image(str(ROOT / uploaded['file']), width='stretch')
                elif photo:
                    st.image(str(ROOT / photos[photo]['file']), width='stretch')
                    st.caption('Photo: ' + photos[photo]['artist'] + ' · ' + photos[photo]['license'])
                    st.markdown(f"[Photo credit]({photos[photo]['source']})")
                else:
                    st.caption(T('Photo not added yet'))
                st.markdown('<h3 class="destination-title">'+html.escape(T(row['Place']))+'</h3>', unsafe_allow_html=True)
                st.caption('⌖ '+T(row['Province']))
                st.markdown('<div class="interest-chips">'+''.join('<span>'+html.escape(T(v))+'</span>' for v in row['tags'][:3])+'</div>',unsafe_allow_html=True)
                if interests:
                    st.write((f"Сонирхол таарсан: {row['Match (%)']}% · " if language=='Монгол' else f"Interest match: {row['Match (%)']}% · ") + (', '.join(T(v) for v in row['matched']) or ('Таарсан сонирхол алга' if language=='Монгол' else 'No selected interests matched')))
                explore_col, save_col = st.columns([1.5,1], gap='small')
                explore_col.button('Дэлгэрэнгүй' if language=='Монгол' else 'Explore →', type='primary', width='stretch', key=f"details_{int(row['ID'])}", on_click=lambda v: st.session_state.update(detail_id=v, navigation='Destination details'), args=(int(row['ID']),))
                id = int(row['ID'])
                saved = id in st.session_state.saved_ids
                if save_col.button(('Хасах' if saved else 'Хадгалах') if language=='Монгол' else ('Remove' if saved else 'Save'), width='stretch', key=f'save_{id}'):
                    if saved:
                        st.session_state.saved_ids.remove(id)
                    else:
                        st.session_state.saved_ids.append(id)
                    st.rerun()
    with map_tab:
        show_map(r)
    with compare:
        comparison = display_table(r, ['Place', 'Province', 'Region', 'Best season', 'Experience types', 'Match (%)'])
        st.dataframe(comparison, hide_index=True)
        counts = comparison.groupby(T('Region')).size().reset_index(name=T('Places'))
        st.plotly_chart(px.bar(counts, x=T('Region'), y=T('Places'), title=T('Matching places by region')), width='stretch')
        if interests and (not r.empty):
            st.plotly_chart(px.bar(comparison.head(15), x=T('Place'), y=T('Match (%)'), title=T('Interest overlap · first 15 results'), range_y=[0, 100]), width='stretch')
        st.download_button(T('Download results CSV'), comparison.to_csv(index=False).encode('utf-8-sig'), 'recommendations.csv', 'text/csv')
elif page == 'Destination details':
    ids = data.ID.astype(int).tolist()
    selected = st.selectbox(T('Choose a destination'), ids, index=ids.index(st.session_state.get('detail_id', ids[0])), format_func=lambda id: T(data.loc[data.ID == id, 'Place'].iloc[0]))
    row = data[data.ID == selected].iloc[0]
    st.header(T(row['Place']))
    st.caption(row['Газрын нэр']+' · '+T(row['Province']))
    photo = user_photos.get(str(selected))
    if photo:
        st.image(str(ROOT / photo['file']), width='stretch')
    st.write(('**Тохиромжтой сарууд:** ' if language=='Монгол' else '**Suggested months:** ')+T(row['Best season']))
    st.write(('**Аяллын төрөл:** ' if language=='Монгол' else '**Experiences:** ')+', '.join(T(v.strip()) for v in row['Experience types'].split(',')))
    st.write(('**Сонирхол:** ' if language=='Монгол' else '**Interests:** ')+', '.join(T(v) for v in row['tags']))
    st.subheader(T('Map'))
    show_map(data[data.ID==selected],single=True)
    st.subheader(T('About this place'))
    soum=row.get('Soum')
    distance=row.get('Distance from Ulaanbaatar (km)')
    st.write(('**Байршил:** ' if language=='Монгол' else '**Location:** ')+T(row['Province'])+(' аймаг' if language=='Монгол' else ' Province')+((', '+str(soum)+' сум') if language=='Монгол' and pd.notna(soum) else (', '+str(soum)+' Soum' if pd.notna(soum) else '')))
    if pd.notna(distance):
        st.write(('**Улаанбаатараас ойролцоогоор:** ' if language=='Монгол' else '**Approximate distance from Ulaanbaatar:** ')+f'{distance:,.0f} '+('км' if language=='Монгол' else 'km'))
    else:st.caption('Улаанбаатараас зай хараахан баталгаажаагүй.' if language=='Монгол' else 'Distance from Ulaanbaatar has not been verified yet.')

    if st.button(T('Add to my plan'), key='detail_save'):
        if selected not in st.session_state.saved_ids:
            st.session_state.saved_ids.append(selected)
        st.success(T('Saved to My plan.'))
elif page == 'My plan':
    st.subheader(T('Your saved places'))
    saved = data[data.ID.isin(st.session_state.saved_ids)]
    st.dataframe(display_table(saved, ['Place', 'Province', 'Best season']), hide_index=True)
    st.subheader(T('Map'))
    if not saved.empty:show_map(saved)
    if saved.empty:
        st.info(T('Add places from Discover to begin.'))
    notes = st.text_area(T('Trip notes'), key='notes')
    a, b, c = st.columns(3)
    people = a.number_input(T('People'), 1, 50, 2)
    days = b.number_input(T('Days'), 1, 60, 3)
    nights = c.number_input(T('Accommodation nights'), 0, 60, 2)
    st.caption('Зардлаа төгрөгөөр оруулна уу.' if language=='Монгол' else 'Enter your expenses in MNT.')
    inputs = [st.number_input(T(label), min_value=0.0, step=1000.0) for label in ['Transport · group total', 'Accommodation · group per night', 'Food · person per day', 'Activities · person for trip', 'Other · group total']]
    if nights > days:
        st.warning(T('Accommodation nights must not exceed trip days.'))
    else:
        costs = budget_breakdown(people, days, nights, *inputs, 0)
        costs = costs[costs.Category != 'Reserve'].copy()
        costs['Category'] = costs.Category.map(T)
        st.metric(T('Entered group estimate'), f'{costs.MNT.sum():,.0f} MNT')
        if costs.MNT.sum():
            st.plotly_chart(px.pie(costs, names='Category', values='MNT', labels={'Category':T('Category')}, hole=0.5), width='stretch')
        st.download_button(T('Download budget CSV'), costs.to_csv(index=False).encode('utf-8-sig'), 'budget.csv', 'text/csv')
    st.download_button(T('Download saved places'), saved.drop(columns=['tags']).to_csv(index=False).encode('utf-8-sig'), 'my_places.csv', 'text/csv')
    st.download_button(T('Download notes'), notes, 'my_trip_notes.txt')
else:
    st.write('MyMongol нь Монголын 21 аймгийн 100 газраас сонирхолдоо тохирох газрыг сонгож, аяллаа төлөвлөхөд тусална.' if language=='Монгол' else 'MyMongol helps you discover 100 destinations across Mongolia’s 21 provinces and plan your trip.')
    st.download_button(T('Download the Excel dataset'), (ROOT / 'data/mongolia_trip.xlsx').read_bytes(), 'mongolia_trip.xlsx')
