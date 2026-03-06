"""
LIV Golf Player Analytics Dashboard
====================================
A Streamlit application for exploring LIV player skill profiles,
career trajectories, and head-to-head comparisons using historical
PGA Tour strokes gained data.

Run with:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from data_loader import (
    get_data,
    ALL_LIV_PLAYERS,
    LIV_ROSTER,
    PLAYER_TEAM,
    YEARS,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LIV Golf Analytics",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #1a1a2e;
        border-left: 4px solid #c9a227;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 8px;
    }
    .metric-label { color: #888; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { color: #fff; font-size: 28px; font-weight: 700; }
    .metric-delta { font-size: 13px; }
    h1, h2, h3 { color: #c9a227; }
    .stTabs [data-baseweb="tab"] { font-size: 15px; }
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading LIV player data...")
def load():
    return get_data()

(ts_df, profile_df, boards_df, hist_df,
 liv_results_df, liv_val_df,
 liv_event_stats_df, liv_season_stats_df, liv_combined_df) = load()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<p style="font-size:28px;font-weight:800;color:#c9a227;'
        'letter-spacing:3px;margin:0 0 4px 0;">LIV GOLF</p>'
        '<p style="font-size:11px;color:#888;letter-spacing:2px;margin:0;">ANALYTICS DASHBOARD</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown("### Navigation")
    page = st.radio(
        "",
        ["Field Overview", "Player Profile", "Head-to-Head", "Team Analysis"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("**PGA data**: SG stats (2015–2025)")
    st.markdown("**LIV data**: Event results & estimated SG (2022–2025)")
    st.markdown("**Players**: All current LIV Golf roster members")
    st.markdown("**Source**: ESPN API + PGA Tour GraphQL + livgolf.com")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: FIELD OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "Field Overview":
    st.title("LIV Golf — Field Analytics Overview")
    st.markdown("2025 model-predicted Strokes Gained rankings for all LIV Golf players.")

    # ── Build 2025 predicted SG table ─────────────────────────────────────────
    val_2025 = liv_val_df[liv_val_df['season'] == 2025].copy()

    # Merge peak SG from profile_df for context
    peak_sg = profile_df[['playerName', 'peak_sg_total']].copy()
    val_2025 = val_2025.merge(peak_sg, on='playerName', how='left')

    # ── Top-line metrics ───────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    elite = (val_2025['est_sg_total'] > 1.0).sum()
    col1.metric("Players (2025 Model)", len(val_2025))
    col2.metric("Elite Tier (Est. SG > 1.0)", int(elite))
    col3.metric("Avg Field Est. SG", f"{val_2025['est_sg_total'].mean():.3f}")
    col4.metric("Field SG Std Dev", f"{val_2025['est_sg_total'].std():.3f}")
    col5.metric("Top Player Est. SG", f"{val_2025['est_sg_total'].max():.3f}")

    st.markdown("---")

    # ── Skill rankings table ───────────────────────────────────────────────────
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.subheader("Player Skill Rankings — 2025 Model Predictions")
        disp = val_2025[['playerName', 'team', 'est_sg_total', 'est_sg_ott',
                          'est_sg_app', 'est_sg_atg', 'peak_sg_total']].rename(columns={
            'playerName':    'Player',
            'team':          'Team',
            'est_sg_total':  'Est. SG Total',
            'est_sg_ott':    'Est. SG OTT',
            'est_sg_app':    'Est. SG App',
            'est_sg_atg':    'Est. SG ATG',
            'peak_sg_total': 'Peak SG (PGA)',
        })

        sort_by = st.selectbox(
            "Sort by",
            ['Est. SG Total', 'Est. SG OTT', 'Est. SG App', 'Est. SG ATG', 'Peak SG (PGA)'],
            key='field_sort',
        )
        disp = disp.sort_values(sort_by, ascending=False).reset_index(drop=True)
        disp.index = disp.index + 1

        st.dataframe(
            disp.style
                .format({
                    'Est. SG Total': '{:.3f}',
                    'Est. SG OTT':  lambda x: f'{x:.3f}' if pd.notna(x) else '—',
                    'Est. SG App':  lambda x: f'{x:.3f}' if pd.notna(x) else '—',
                    'Est. SG ATG':  lambda x: f'{x:.3f}' if pd.notna(x) else '—',
                    'Peak SG (PGA)': lambda x: f'{x:.3f}' if pd.notna(x) else '—',
                })
                .background_gradient(subset=['Est. SG Total'], cmap='RdYlGn',
                                      vmin=-0.5, vmax=2.0),
            height=500,
            use_container_width=True,
        )

    with col_b:
        st.subheader("Est. SG Total Distribution")
        fig = px.histogram(
            val_2025,
            x='est_sg_total',
            nbins=20,
            color_discrete_sequence=['#c9a227'],
            labels={'est_sg_total': 'Est. SG Total (2025)'},
            title="LIV Field — Est. SG Distribution (2025)",
        )
        fig.update_layout(
            plot_bgcolor='#0e0e1a',
            paper_bgcolor='#0e0e1a',
            font_color='white',
            showlegend=False,
            height=300,
        )
        fig.add_vline(x=0, line_dash='dash', line_color='white', opacity=0.5,
                      annotation_text='Tour Avg', annotation_position='top right')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Skill Category Breakdown")
        sg_cats   = ['est_sg_ott', 'est_sg_app', 'est_sg_atg']
        cat_labels = ['Off Tee', 'Approach', 'Around Green']
        avgs = [val_2025[c].dropna().mean() for c in sg_cats]

        fig2 = go.Figure(go.Bar(
            x=cat_labels,
            y=avgs,
            marker_color=['#3498db', '#e74c3c', '#2ecc71'],
            text=[f'{v:.3f}' for v in avgs],
            textposition='outside',
        ))
        fig2.update_layout(
            plot_bgcolor='#0e0e1a', paper_bgcolor='#0e0e1a',
            font_color='white', height=280,
            title='LIV Field Avg Est. SG by Category (2025)',
            yaxis=dict(title='Estimated Strokes Gained'),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Team comparison bar chart ──────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Team Skill Comparison — 2025 Model Predictions")

    team_sg = (
        val_2025.groupby('team')['est_sg_total']
        .agg(['mean', 'min', 'max', 'count'])
        .reset_index()
        .rename(columns={'mean': 'avg_sg', 'min': 'min_sg', 'max': 'max_sg', 'count': 'n_players'})
        .sort_values('avg_sg', ascending=False)
    )

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=team_sg['team'],
        y=team_sg['avg_sg'],
        name='Team Avg Est. SG',
        marker_color='#c9a227',
        error_y=dict(
            type='data',
            symmetric=False,
            array=team_sg['max_sg'] - team_sg['avg_sg'],
            arrayminus=team_sg['avg_sg'] - team_sg['min_sg'],
            color='rgba(255,255,255,0.4)',
        ),
        text=[f'{v:.3f}' for v in team_sg['avg_sg']],
        textposition='outside',
    ))
    fig3.update_layout(
        plot_bgcolor='#0e0e1a', paper_bgcolor='#0e0e1a',
        font_color='white', height=400,
        xaxis_tickangle=-35,
        title='Average Est. SG Total by LIV Team — 2025 (error bars = roster range)',
        yaxis=dict(title='Estimated Strokes Gained Total'),
        showlegend=False,
    )
    st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: PLAYER PROFILE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Player Profile":
    st.title("Player Profile")

    # Player selector
    players_available = sorted(profile_df['playerName'].unique())
    selected = st.selectbox("Select Player", players_available, index=0)

    player_ts = ts_df[ts_df['playerName'] == selected].sort_values('year')
    player_profile = profile_df[profile_df['playerName'] == selected]

    if player_ts.empty or player_profile.empty:
        st.warning(f"No PGA Tour SG data found for {selected}.")
        st.stop()

    prof = player_profile.iloc[0]

    # ── Header metrics ─────────────────────────────────────────────────────────
    st.markdown(f"### {selected}")
    st.markdown(f"**Team**: {prof['team']}  |  **Last PGA Tour Season**: {prof['last_active_yr']}  |  **Peak Year**: {prof['peak_year']}")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Recent SG Total", f"{prof['recent_sg_total']:.3f}", help="Avg over last 3 PGA seasons")
    m2.metric("Career Best SG", f"{prof['peak_sg_total']:.3f}")
    m3.metric("SG Off the Tee", f"{prof['sg_ott']:.3f}" if pd.notna(prof['sg_ott']) else "—")
    m4.metric("SG Approach", f"{prof['sg_app']:.3f}" if pd.notna(prof['sg_app']) else "—")
    m5.metric("SG Around Green", f"{prof['sg_atg']:.3f}" if pd.notna(prof['sg_atg']) else "—")

    st.markdown("---")

    col1, col2 = st.columns([3, 2])

    with col1:
        # ── Career SG Trajectory ───────────────────────────────────────────────
        st.subheader("Career SG Trajectory")

        actual_ts = player_ts[player_ts['data_source'] == 'actual']
        est_ts    = player_ts[player_ts['data_source'] == 'estimated']

        SG_SERIES = [
            ('sg_total', 'SG Total',        '#c9a227', 3),
            ('sg_ott',   'SG Off Tee',      '#3498db', 2),
            ('sg_app',   'SG Approach',     '#e74c3c', 2),
            ('sg_atg',   'SG Around Green', '#2ecc71', 2),
        ]

        fig = go.Figure()

        # ── Actual PGA traces — solid lines ───────────────────────────────────
        for col, label, color, width in SG_SERIES:
            if actual_ts[col].notna().any():
                fig.add_trace(go.Scatter(
                    x=actual_ts['year'], y=actual_ts[col],
                    name=label, mode='lines+markers',
                    line=dict(color=color, width=width),
                    marker=dict(size=7 if col == 'sg_total' else 5),
                    legendgroup=label,
                ))

        # ── LIV era vertical divider — always at 2022 if player has est data ─
        last_actual_yr = int(actual_ts['year'].max()) if not actual_ts.empty else 2015
        liv_start = max(last_actual_yr + 1, 2022)

        if not est_ts.empty:
            fig.add_vrect(
                x0=liv_start - 0.5, x1=est_ts['year'].max() + 0.5,
                fillcolor='rgba(201,162,39,0.06)',
                line_width=0,
                annotation_text='◀ PGA Tour  |  LIV Golf (Est.) ▶',
                annotation_position='top left',
                annotation_font=dict(color='#c9a227', size=11),
            )
            # Vertical rule at the boundary
            fig.add_vline(
                x=liv_start - 0.5,
                line_dash='dash', line_color='rgba(201,162,39,0.5)', line_width=1,
            )

            # ── Estimated LIV-era traces — dashed, same colors ────────────────
            for col, label, color, width in SG_SERIES:
                if est_ts[col].notna().any():
                    # Bridge connector from last actual to first estimated
                    if actual_ts[col].notna().any():
                        bridge_x = [actual_ts.loc[actual_ts[col].notna(), 'year'].iloc[-1],
                                     est_ts.loc[est_ts[col].notna(), 'year'].iloc[0]]
                        bridge_y = [actual_ts.loc[actual_ts[col].notna(), col].iloc[-1],
                                     est_ts.loc[est_ts[col].notna(), col].iloc[0]]
                        fig.add_trace(go.Scatter(
                            x=bridge_x, y=bridge_y,
                            mode='lines', showlegend=False,
                            line=dict(color=f'rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:],16)},0.3)',
                                      width=1, dash='dot'),
                            legendgroup=label,
                        ))
                    fig.add_trace(go.Scatter(
                        x=est_ts['year'], y=est_ts[col],
                        name=f'{label} (est.)', mode='lines+markers',
                        line=dict(color=color, width=width, dash='dash'),
                        marker=dict(size=7 if col == 'sg_total' else 5, symbol='circle-open'),
                        opacity=0.8,
                        legendgroup=label,
                    ))

        fig.add_hline(y=0, line_dash='dot', line_color='white', opacity=0.2)

        fig.update_layout(
            plot_bgcolor='#0e0e1a', paper_bgcolor='#0e0e1a',
            font_color='white', height=420,
            xaxis=dict(title='Year', dtick=1),
            yaxis=dict(title='Strokes Gained'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            hovermode='x unified',
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # ── Skill Radar Chart ──────────────────────────────────────────────────
        st.subheader("Skill Radar")

        categories = ['SG Total', 'SG Off Tee', 'SG Approach', 'SG Around\nGreen']
        values_raw = [
            prof['recent_sg_total'],
            prof['sg_ott'] if pd.notna(prof['sg_ott']) else 0,
            prof['sg_app'] if pd.notna(prof['sg_app']) else 0,
            prof['sg_atg'] if pd.notna(prof['sg_atg']) else 0,
        ]

        # Normalize to 0-100 scale relative to LIV field
        def normalize_sg(val, col):
            col_data = profile_df[col].dropna()
            pct = (col_data < val).mean() * 100
            return round(pct, 1)

        normalized = [
            normalize_sg(prof['recent_sg_total'], 'recent_sg_total'),
            normalize_sg(prof['sg_ott'], 'sg_ott') if pd.notna(prof['sg_ott']) else 50,
            normalize_sg(prof['sg_app'], 'sg_app') if pd.notna(prof['sg_app']) else 50,
            normalize_sg(prof['sg_atg'], 'sg_atg') if pd.notna(prof['sg_atg']) else 50,
        ]

        radar_cats = categories + [categories[0]]
        radar_vals = normalized + [normalized[0]]

        fig_radar = go.Figure(go.Scatterpolar(
            r=radar_vals,
            theta=radar_cats,
            fill='toself',
            fillcolor='rgba(201,162,39,0.25)',
            line=dict(color='#c9a227', width=2),
            name=selected,
        ))

        # Add field average line
        field_avg_norm = [50, 50, 50, 50, 50]
        fig_radar.add_trace(go.Scatterpolar(
            r=field_avg_norm,
            theta=radar_cats,
            mode='lines',
            line=dict(color='rgba(255,255,255,0.3)', dash='dot'),
            name='Field Average',
        ))

        fig_radar.update_layout(
            polar=dict(
                bgcolor='#0e0e1a',
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False,
                                gridcolor='rgba(255,255,255,0.15)'),
                angularaxis=dict(gridcolor='rgba(255,255,255,0.15)', color='white'),
            ),
            paper_bgcolor='#0e0e1a',
            font_color='white',
            height=360,
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=-0.15),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        # ── Raw SG numbers ─────────────────────────────────────────────────────
        st.markdown("**Skill Breakdown (recent 3-yr avg)**")
        sg_breakdown = {
            'SG Total':        prof['recent_sg_total'],
            'SG Off Tee':      prof['sg_ott'],
            'SG Approach':     prof['sg_app'],
            'SG Around Green': prof['sg_atg'],
        }
        for label, val in sg_breakdown.items():
            if pd.notna(val):
                color = '#2ecc71' if val > 0 else '#e74c3c'
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;margin:4px 0'>"
                    f"<span style='color:#aaa'>{label}</span>"
                    f"<span style='color:{color};font-weight:700'>{val:+.3f}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── LIV Golf Results ───────────────────────────────────────────────────────
    if not liv_results_df.empty:
        lname_lower = selected.split()[-1].lower()
        # Exact match first (canonicalized names); fall back to last-name for edge cases
        player_liv = liv_results_df[liv_results_df['playerName'] == selected].copy()
        if player_liv.empty:
            player_liv = liv_results_df[
                liv_results_df['playerName'].str.lower().str.contains(lname_lower, na=False)
            ].copy()

        if not player_liv.empty:
            st.markdown("---")
            st.subheader("LIV Golf Results")

            # Parse numeric position
            player_liv['pos_num'] = player_liv['position'].apply(
                lambda x: int(str(x).replace('T', ''))
                if str(x).replace('T', '').isdigit() else None
            )
            pos_valid = player_liv[player_liv['pos_num'].notna()].copy()

            col_liv1, col_liv2 = st.columns([2, 1])

            with col_liv1:
                if not pos_valid.empty:
                    fig_liv = go.Figure()
                    seasons_liv = sorted(pos_valid['year'].unique())
                    colors_liv = px.colors.sequential.Oranges
                    color_map_liv = {
                        s: colors_liv[max(1, int((i + 1) * (len(colors_liv) - 1) / max(len(seasons_liv), 1)))]
                        for i, s in enumerate(seasons_liv)
                    }
                    for yr in seasons_liv:
                        yr_data = pos_valid[pos_valid['year'] == yr]
                        color = color_map_liv[yr]
                        # Box trace
                        fig_liv.add_trace(go.Box(
                            y=yr_data['pos_num'],
                            name=str(yr),
                            marker_color=color,
                            line_color=color,
                            opacity=0.85,
                            boxpoints='all',
                            jitter=0.3,
                            pointpos=0,
                            customdata=yr_data[['event_name', 'total_to_par']].values,
                            hovertemplate=(
                                '<b>%{customdata[0]}</b><br>'
                                'Position: %{y}<br>'
                                'To Par: %{customdata[1]}<extra></extra>'
                            ),
                        ))
                    fig_liv.update_yaxes(autorange='reversed', title='Finish Position')
                    fig_liv.update_layout(
                        plot_bgcolor='#0e0e1a', paper_bgcolor='#0e0e1a',
                        font_color='white', height=340,
                        xaxis=dict(title='Season'),
                        showlegend=False,
                        title=f'{selected} — LIV Finish Positions by Season',
                    )
                    st.plotly_chart(fig_liv, use_container_width=True)

            with col_liv2:
                total_liv = len(player_liv)
                liv_wins = (pos_valid['pos_num'] == 1).sum() if not pos_valid.empty else 0
                liv_top5 = (pos_valid['pos_num'] <= 5).sum() if not pos_valid.empty else 0
                avg_finish = pos_valid['pos_num'].mean() if not pos_valid.empty else None

                st.metric("LIV Events", total_liv)
                st.metric("Wins", int(liv_wins))
                st.metric("Top 5s", int(liv_top5))
                if avg_finish is not None:
                    st.metric("Avg Finish", f"{avg_finish:.1f}")

            # ── Augmented event log with raw stats ────────────────────────────
            with st.expander("Full LIV Event Log"):
                player_combined = liv_combined_df[liv_combined_df['playerName'] == selected].copy()
                if player_combined.empty:
                    player_combined = liv_combined_df[
                        liv_combined_df['playerName'].str.lower().str.contains(lname_lower, na=False)
                    ].copy()
                stat_cols = ['drive_distance', 'gir_pct', 'fairway_pct',
                             'scrambling_pct', 'putting_avg', 'birdies_per_round']
                base_cols = [c for c in ['year', 'event_name', 'position', 'total_to_par', 'R1', 'R2', 'R3']
                             if c in player_combined.columns]
                avail_stat_cols = [c for c in stat_cols if c in player_combined.columns]
                log_df = (player_combined[base_cols + avail_stat_cols]
                          .sort_values(['year', 'event_name'])
                          .reset_index(drop=True))
                numeric_stat_cols = [c for c in avail_stat_cols if log_df[c].notna().any()]
                styled = log_df.style
                if numeric_stat_cols:
                    styled = styled.background_gradient(subset=numeric_stat_cols, cmap='RdYlGn')
                st.dataframe(styled, use_container_width=True, hide_index=True)

            # ── Per-event stat trend charts ────────────────────────────────────
            if not liv_combined_df.empty:
                player_ev = liv_combined_df[liv_combined_df['playerName'] == selected].copy()
                if player_ev.empty:
                    player_ev = liv_combined_df[
                        liv_combined_df['playerName'].str.lower().str.contains(lname_lower, na=False)
                    ].copy()

                if not player_ev.empty:
                    st.markdown("---")
                    st.subheader("LIV Performance Stats — Event Trends")

                    # Sort by season then event_slug for a chronological x-axis
                    player_ev = player_ev.sort_values(['year', 'event_slug']).reset_index(drop=True)
                    # Strip the 4-digit year from event_name (e.g. "Adelaide 2023" → "Adelaide")
                    # then append a 2-digit year suffix → "Adelaide '23"
                    # This keeps labels short and unique across seasons.
                    _loc = (player_ev['event_name']
                            .str.replace(r'\s*\d{4}$', '', regex=True)
                            .str.strip())
                    player_ev['event_label'] = _loc + " '" + player_ev['year'].astype(str).str[-2:]

                    STAT_TABS = [
                        ('Drive Distance', 'drive_distance'),
                        ('GIR %',          'gir_pct'),
                        ('Fairway %',      'fairway_pct'),
                        ('Scrambling %',   'scrambling_pct'),
                        ('Putting Avg',    'putting_avg'),
                        ('Birdies/Rd',     'birdies_per_round'),
                    ]

                    # Field averages per season for each stat
                    field_avgs = {}
                    for _, stat_col in STAT_TABS:
                        if stat_col in liv_combined_df.columns:
                            field_avgs[stat_col] = (
                                liv_combined_df.groupby('year')[stat_col].mean().to_dict()
                            )

                    tab_labels = [t[0] for t in STAT_TABS]
                    tabs = st.tabs(tab_labels)

                    for tab, (tab_label, stat_col) in zip(tabs, STAT_TABS):
                        with tab:
                            if stat_col not in player_ev.columns or player_ev[stat_col].isna().all():
                                st.info(f"No {tab_label} data available.")
                                continue

                            ev_plot = player_ev[player_ev[stat_col].notna()].copy()
                            fig_ev = go.Figure()

                            # Main stat line, color by season
                            seasons = sorted(ev_plot['year'].unique())
                            colors = px.colors.sequential.Oranges
                            color_map = {s: colors[max(1, int((i+1) * (len(colors)-1) / max(len(seasons),1)))]
                                         for i, s in enumerate(seasons)}

                            for season_yr in seasons:
                                mask = ev_plot['year'] == season_yr
                                fig_ev.add_trace(go.Scatter(
                                    x=ev_plot.loc[mask, 'event_label'],
                                    y=ev_plot.loc[mask, stat_col],
                                    mode='lines+markers',
                                    name=str(season_yr),
                                    line=dict(color=color_map[season_yr], width=2),
                                    marker=dict(size=7),
                                ))

                            # Field average dashed lines per season
                            if stat_col in field_avgs:
                                for season_yr in seasons:
                                    avg_val = field_avgs[stat_col].get(season_yr)
                                    if avg_val is not None:
                                        season_mask = ev_plot['year'] == season_yr
                                        x_vals = ev_plot.loc[season_mask, 'event_label'].tolist()
                                        if x_vals:
                                            fig_ev.add_trace(go.Scatter(
                                                x=x_vals,
                                                y=[avg_val] * len(x_vals),
                                                mode='lines',
                                                name=f'Field Avg {season_yr}',
                                                line=dict(color=color_map[season_yr], width=1, dash='dash'),
                                                opacity=0.5,
                                                showlegend=False,
                                            ))

                            fig_ev.update_layout(
                                plot_bgcolor='#0e0e1a', paper_bgcolor='#0e0e1a',
                                font_color='white', height=340,
                                xaxis=dict(tickangle=-35),
                                yaxis=dict(title=tab_label),
                                legend=dict(orientation='h', yanchor='bottom', y=1.02),
                                hovermode='x unified',
                            )
                            st.plotly_chart(fig_ev, use_container_width=True)

    # ── Estimated SG from LIV model ────────────────────────────────────────────
    if not liv_val_df.empty:
        player_val = liv_val_df[liv_val_df['playerName'] == selected].copy()
        if not player_val.empty:
            st.markdown("---")
            st.subheader("LIV Era — XGBoost Estimated SG by Season")
            st.caption(
                "SG values estimated from LIV raw stats (driving distance, GIR%, fairway%, "
                "scrambling%, putting avg, birdies/round) using an XGBoost model trained on "
                "PGA Tour player-seasons (2010–2025). Quantile-matching aligns LIV stat "
                "distributions to PGA Tour scale before prediction."
            )

            val_cols = ['season', 'est_sg_total', 'est_sg_ott', 'est_sg_app',
                        'est_sg_atg', 'est_sg_putt', 'events_played', 'avg_position', 'wins']
            avail = [c for c in val_cols if c in player_val.columns]
            est_display = (player_val[avail]
                           .sort_values('season')
                           .reset_index(drop=True))
            rename_map = {
                'season':       'Season',
                'est_sg_total': 'Est. SG Total',
                'est_sg_ott':   'Est. SG OTT',
                'est_sg_app':   'Est. SG App',
                'est_sg_atg':   'Est. SG ATG',
                'est_sg_putt':  'Est. SG Putt',
                'events_played':'Events',
                'avg_position': 'Avg Finish',
                'wins':         'Wins',
            }
            est_display = est_display.rename(columns=rename_map)

            sg_display_cols = [c for c in ['Est. SG Total', 'Est. SG OTT', 'Est. SG App',
                                            'Est. SG ATG', 'Est. SG Putt'] if c in est_display.columns]
            fmt = {c: lambda x: f'{x:+.3f}' if pd.notna(x) else '—' for c in sg_display_cols}
            if 'Avg Finish' in est_display.columns:
                fmt['Avg Finish'] = lambda x: f'{x:.1f}' if pd.notna(x) else '—'
            if 'Events' in est_display.columns:
                fmt['Events'] = lambda x: f'{int(x)}' if pd.notna(x) else '—'

            st.dataframe(
                est_display.style
                    .format(fmt)
                    .background_gradient(subset=['Est. SG Total'], cmap='RdYlGn', vmin=-1.0, vmax=2.0),
                use_container_width=True,
                hide_index=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: HEAD-TO-HEAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Head-to-Head":
    st.title("Head-to-Head Comparison")

    # ── Player selector — all players with 2025 model data ────────────────────
    val_2025_h2h = liv_val_df[liv_val_df['season'] == 2025].copy()
    available = sorted(val_2025_h2h['playerName'].unique())

    col_sel1, col_sel2 = st.columns(2)
    p1 = col_sel1.selectbox("Player 1", available, index=0, key='p1')
    p2 = col_sel2.selectbox("Player 2", available,
                             index=min(1, len(available) - 1), key='p2')

    if p1 == p2:
        st.warning("Select two different players.")
        st.stop()

    # ── Per-player data helpers ────────────────────────────────────────────────
    def _val2025(name):
        rows = val_2025_h2h[val_2025_h2h['playerName'] == name]
        return rows.iloc[0] if not rows.empty else None

    def _prof(name):
        rows = profile_df[profile_df['playerName'] == name]
        return rows.iloc[0] if not rows.empty else None

    p1_val  = _val2025(p1)
    p2_val  = _val2025(p2)
    p1_prof = _prof(p1)
    p2_prof = _prof(p2)
    p1_ts   = ts_df[ts_df['playerName'] == p1].sort_values('year')
    p2_ts   = ts_df[ts_df['playerName'] == p2].sort_values('year')

    # ── Normalize 2025 model values against the 2025 field ────────────────────
    def _norm_2025(val, col):
        if pd.isna(val):
            return 50.0
        field = val_2025_h2h[col].dropna()
        return round((field < val).mean() * 100, 1)

    # ── Radar comparison ───────────────────────────────────────────────────────
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        cats = ['Est. SG Total', 'Est. SG OTT', 'Est. SG App', 'Est. SG ATG']
        cats_loop = cats + [cats[0]]
        sg_cols_radar = ['est_sg_total', 'est_sg_ott', 'est_sg_app', 'est_sg_atg']

        def player_radar_vals(val_row):
            if val_row is None:
                return [50, 50, 50, 50]
            return [_norm_2025(val_row.get(c), c) for c in sg_cols_radar]

        p1_vals = player_radar_vals(p1_val)
        p2_vals = player_radar_vals(p2_val)

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=p1_vals + [p1_vals[0]], theta=cats_loop,
            fill='toself', fillcolor='rgba(52,152,219,0.2)',
            line=dict(color='#3498db', width=2), name=p1,
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=p2_vals + [p2_vals[0]], theta=cats_loop,
            fill='toself', fillcolor='rgba(201,162,39,0.2)',
            line=dict(color='#c9a227', width=2), name=p2,
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor='#0e0e1a',
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False,
                                gridcolor='rgba(255,255,255,0.15)'),
                angularaxis=dict(gridcolor='rgba(255,255,255,0.15)', color='white'),
            ),
            paper_bgcolor='#0e0e1a', font_color='white',
            height=400, title='2025 Estimated SG Radar (percentile vs LIV field)',
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_r2:
        categories = ['SG Total', 'Off Tee', 'Approach', 'Around Green', 'Putting']
        sg_bar_cols = ['est_sg_total', 'est_sg_ott', 'est_sg_app', 'est_sg_atg', 'est_sg_putt']

        def _bar_vals(val_row):
            if val_row is None:
                return [0] * len(sg_bar_cols)
            return [float(val_row.get(c, 0) or 0) for c in sg_bar_cols]

        p1_raw = _bar_vals(p1_val)
        p2_raw = _bar_vals(p2_val)

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name=p1, x=categories, y=p1_raw,
            marker_color='#3498db',
            text=[f'{v:+.3f}' for v in p1_raw], textposition='outside',
        ))
        fig_bar.add_trace(go.Bar(
            name=p2, x=categories, y=p2_raw,
            marker_color='#c9a227',
            text=[f'{v:+.3f}' for v in p2_raw], textposition='outside',
        ))
        fig_bar.add_hline(y=0, line_color='rgba(255,255,255,0.4)', line_dash='dash')
        fig_bar.update_layout(
            barmode='group',
            plot_bgcolor='#0e0e1a', paper_bgcolor='#0e0e1a',
            font_color='white', height=400,
            title='2025 Est. SG — Raw Values (tour average = 0)',
            yaxis=dict(title='Estimated Strokes Gained'),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── SG Total over time ─────────────────────────────────────────────────────
    st.subheader("Career SG Trajectory — Head-to-Head")
    st.caption("Solid = PGA Tour actual  |  Dashed = LIV era XGBoost estimate")

    fig_trend = go.Figure()

    for player_name, ts, color in [(p1, p1_ts, '#3498db'), (p2, p2_ts, '#c9a227')]:
        act = ts[ts['data_source'] == 'actual']
        est = ts[ts['data_source'] == 'estimated']
        if not act.empty:
            fig_trend.add_trace(go.Scatter(
                x=act['year'], y=act['sg_total'],
                name=player_name, mode='lines+markers',
                line=dict(color=color, width=3), marker=dict(size=8),
            ))
        if not est.empty and est['sg_total'].notna().any():
            if not act.empty:
                fig_trend.add_trace(go.Scatter(
                    x=[act['year'].iloc[-1], est['year'].iloc[0]],
                    y=[act['sg_total'].iloc[-1], est['sg_total'].iloc[0]],
                    mode='lines', showlegend=False,
                    line=dict(color=color, width=1, dash='dot'), opacity=0.4,
                ))
            fig_trend.add_trace(go.Scatter(
                x=est['year'], y=est['sg_total'],
                name=f'{player_name} (est.)', mode='lines+markers',
                line=dict(color=color, width=2, dash='dash'),
                marker=dict(size=7, symbol='circle-open'), opacity=0.8,
            ))

    fig_trend.add_hline(y=0, line_dash='dot', line_color='white', opacity=0.2)
    fig_trend.add_vrect(x0=2021.5, x1=2025.5,
                        fillcolor='rgba(255,255,255,0.03)', line_width=0,
                        annotation_text='LIV Era', annotation_position='top right',
                        annotation_font=dict(color='rgba(255,255,255,0.4)', size=10))
    fig_trend.update_layout(
        plot_bgcolor='#0e0e1a', paper_bgcolor='#0e0e1a',
        font_color='white', height=380,
        xaxis=dict(title='Year', dtick=1),
        yaxis=dict(title='SG Total'),
        hovermode='x unified',
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # ── Stat-by-stat comparison table ─────────────────────────────────────────
    st.subheader("Statistical Comparison")

    def _fmt(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return '—'
        if isinstance(v, float):
            return f'{v:.3f}'
        return str(v)

    def _edge(v1, v2, higher_is_better=True):
        try:
            v1, v2 = float(v1), float(v2)
        except (TypeError, ValueError):
            return '—'
        if pd.isna(v1) or pd.isna(v2):
            return '—'
        if higher_is_better:
            return p1 if v1 > v2 else (p2 if v2 > v1 else 'Even')
        return p1 if v1 < v2 else (p2 if v2 < v1 else 'Even')

    def _get(row, col):
        if row is None:
            return None
        v = row.get(col)
        return None if (v is not None and isinstance(v, float) and pd.isna(v)) else v

    stat_rows = []

    # 2025 model predictions
    for label, col, hi in [
        ('Est. SG Total (2025)', 'est_sg_total', True),
        ('Est. SG Off Tee',      'est_sg_ott',   True),
        ('Est. SG Approach',     'est_sg_app',   True),
        ('Est. SG Around Green', 'est_sg_atg',   True),
        ('Est. SG Putting',      'est_sg_putt',  True),
    ]:
        v1, v2 = _get(p1_val, col), _get(p2_val, col)
        stat_rows.append({'Statistic': label, p1: _fmt(v1), p2: _fmt(v2),
                          'Edge': _edge(v1, v2, hi)})

    # LIV event record (from val_df — model-derived season aggregates)
    for label, col, hi in [
        ('LIV Events Played', 'events_played', False),
        ('LIV Avg Finish',    'avg_position',  False),
        ('LIV Wins',          'wins',          True),
        ('LIV Top 10s',       'top10s',        True),
    ]:
        v1, v2 = _get(p1_val, col), _get(p2_val, col)
        stat_rows.append({'Statistic': label, p1: _fmt(v1), p2: _fmt(v2),
                          'Edge': _edge(v1, v2, hi)})

    # Historical PGA bests (profile_df, may be None for LIV-only players)
    for label, col, hi in [
        ('Peak SG Total (PGA)', 'peak_sg_total', True),
        ('Career Avg SG (PGA)', 'career_avg_sg', True),
        ('Peak Year',           'peak_year',     True),
    ]:
        v1, v2 = _get(p1_prof, col), _get(p2_prof, col)
        stat_rows.append({'Statistic': label, p1: _fmt(v1), p2: _fmt(v2),
                          'Edge': _edge(v1, v2, hi)})

    cmp_df = pd.DataFrame(stat_rows)
    st.dataframe(cmp_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: TEAM ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Team Analysis":
    st.title("LIV Team Skill Analysis")
    st.markdown("Team-level skill composition and balance metrics for all LIV Golf teams.")

    # ── Base data: 2025 model predictions ──────────────────────────────────────
    val_2025_team = liv_val_df[liv_val_df['season'] == 2025].copy()
    SG_COLS  = ['est_sg_total', 'est_sg_ott', 'est_sg_app', 'est_sg_atg', 'est_sg_putt']
    SG_LABELS = ['SG Total', 'SG Off Tee', 'SG Approach', 'SG Around Green', 'SG Putting']

    # ── Team selector ──────────────────────────────────────────────────────────
    teams_with_data = (val_2025_team[val_2025_team['team'].notna() & (val_2025_team['team'] != '')]
                       ['team'].unique())
    selected_team = st.selectbox("Select Team", sorted(teams_with_data))

    team_players = val_2025_team[val_2025_team['team'] == selected_team]

    # ── Team overview metrics ──────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Roster Size", len(team_players))
    m2.metric("Team Avg SG Total (2025 Est.)", f"{team_players['est_sg_total'].mean():.3f}")
    m3.metric("Best Player SG", f"{team_players['est_sg_total'].max():.3f}")
    m4.metric("SG Variance", f"{team_players['est_sg_total'].std():.3f}",
              help="Lower = more balanced team, higher = star-heavy team")

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        # ── Team skill heatmap ─────────────────────────────────────────────────
        st.subheader("Team Skill Heatmap")

        heatmap_data = team_players[['playerName'] + SG_COLS].dropna(subset=['est_sg_total'])
        heatmap_data = heatmap_data.set_index('playerName')
        heatmap_data.columns = SG_LABELS

        # Normalize each column relative to full 2025 LIV field
        norm_data = heatmap_data.copy()
        for col, sg_col in zip(SG_LABELS, SG_COLS):
            field_vals = val_2025_team[sg_col].dropna()
            norm_data[col] = heatmap_data[col].apply(
                lambda x: (field_vals < x).mean() * 100 if pd.notna(x) else 50
            )

        fig_heat = px.imshow(
            norm_data,
            color_continuous_scale='RdYlGn',
            zmin=0, zmax=100,
            text_auto='.0f',
            title=f'{selected_team} — Skill Percentiles vs 2025 LIV Field (XGBoost Est.)',
            aspect='auto',
        )
        fig_heat.update_layout(
            paper_bgcolor='#0e0e1a', font_color='white', height=300,
            coloraxis_colorbar=dict(title='Percentile'),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # ── Player detail table ────────────────────────────────────────────────
        st.subheader("Roster Detail")
        roster_display = team_players[['playerName'] + SG_COLS +
                                       ['events_played', 'avg_position', 'wins']].copy()
        roster_display.columns = (['Player'] + SG_LABELS +
                                   ['Events', 'Avg Pos', 'Wins'])
        roster_display = roster_display.sort_values('SG Total', ascending=False).reset_index(drop=True)
        roster_display.index = roster_display.index + 1
        def _fmt_sg(x):  return f'{x:.3f}' if pd.notna(x) else '—'
        def _fmt_int(x): return f'{int(x)}' if pd.notna(x) else '—'
        def _fmt_f1(x):  return f'{x:.1f}' if pd.notna(x) else '—'
        fmt = {lbl: _fmt_sg for lbl in SG_LABELS}
        fmt['Events']  = _fmt_int
        fmt['Avg Pos'] = _fmt_f1
        fmt['Wins']    = _fmt_int
        st.dataframe(
            roster_display.style.format(fmt)
            .background_gradient(subset=['SG Total'], cmap='RdYlGn', vmin=-0.5, vmax=1.5),
            use_container_width=True,
        )
        st.caption("SG values are 2025 season estimates from XGBoost model.")

    with col2:
        # ── Skill balance radar ────────────────────────────────────────────────
        st.subheader("Team Balance Radar")

        radar_cats = SG_LABELS
        radar_vals = []
        for sg_col in SG_COLS:
            val_mean = team_players[sg_col].mean()
            if pd.notna(val_mean):
                field_vals = val_2025_team[sg_col].dropna()
                radar_vals.append(round((field_vals < val_mean).mean() * 100, 1))
            else:
                radar_vals.append(50.0)

        radar_cats_loop = radar_cats + [radar_cats[0]]
        radar_vals_loop = radar_vals + [radar_vals[0]]

        fig_r = go.Figure(go.Scatterpolar(
            r=radar_vals_loop, theta=radar_cats_loop,
            fill='toself', fillcolor='rgba(201,162,39,0.2)',
            line=dict(color='#c9a227', width=2), name=selected_team,
        ))
        fig_r.add_trace(go.Scatterpolar(
            r=[50, 50, 50, 50, 50, 50], theta=radar_cats_loop,
            mode='lines', line=dict(color='rgba(255,255,255,0.3)', dash='dot'),
            name='Median Team',
        ))
        fig_r.update_layout(
            polar=dict(
                bgcolor='#0e0e1a',
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False,
                                gridcolor='rgba(255,255,255,0.15)'),
                angularaxis=dict(gridcolor='rgba(255,255,255,0.15)', color='white'),
            ),
            paper_bgcolor='#0e0e1a', font_color='white',
            height=350, title=f'{selected_team}\nSkill Balance',
        )
        st.plotly_chart(fig_r, use_container_width=True)

        # ── Skill strengths / weaknesses ───────────────────────────────────────
        st.markdown("**Team Skill Summary**")
        for label, pct in zip(radar_cats, radar_vals):
            color = '#2ecc71' if pct > 60 else ('#e74c3c' if pct < 40 else '#f39c12')
            badge = '▲ Strength' if pct > 60 else ('▼ Gap' if pct < 40 else '= Average')
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;margin:4px 0'>"
                f"<span style='color:#aaa;font-size:13px'>{label}</span>"
                f"<span style='color:{color};font-size:13px'>{badge} ({pct:.0f}th %ile)</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── LIV Raw Stats section ──────────────────────────────────────────────────
    if not liv_season_stats_df.empty:
        st.markdown("---")
        st.subheader("LIV Raw Stats")

        RAW_STAT_COLS = ['drive_distance', 'gir_pct', 'fairway_pct',
                         'scrambling_pct', 'putting_avg', 'birdies_per_round']
        RAW_STAT_LABELS = ['Drive Dist', 'GIR %', 'Fairway %',
                           'Scrambling %', 'Putting Avg', 'Birdies/Rd']

        # ── A. Team stat averages bar chart ───────────────────────────────────
        team_season_stats = liv_season_stats_df[
            liv_season_stats_df['team'] == selected_team
        ].copy()

        avail_raw = [c for c in RAW_STAT_COLS if c in team_season_stats.columns]
        if not team_season_stats.empty and avail_raw:
            st.markdown("**Season-by-Season Averages**")
            seasons_avail = sorted(team_season_stats['season'].unique())
            stat_colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']

            fig_bar = go.Figure()
            for stat_col, stat_label, color in zip(avail_raw,
                                                    [RAW_STAT_LABELS[RAW_STAT_COLS.index(c)] for c in avail_raw],
                                                    stat_colors):
                season_avgs = (team_season_stats.groupby('season')[stat_col]
                               .mean().reindex(seasons_avail))
                fig_bar.add_trace(go.Bar(
                    x=[str(s) for s in seasons_avail],
                    y=season_avgs.values,
                    name=stat_label,
                    marker_color=color,
                ))
            fig_bar.update_layout(
                barmode='group',
                plot_bgcolor='#0e0e1a', paper_bgcolor='#0e0e1a',
                font_color='white', height=320,
                xaxis=dict(title='Season'),
                yaxis=dict(title='Average Value'),
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
                title=f'{selected_team} — Avg Raw Stats by Season',
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # ── B. Team vs. field heatmap (most recent season) ────────────────────
        most_recent_season = liv_season_stats_df['season'].max()
        recent_stats = liv_season_stats_df[
            liv_season_stats_df['season'] == most_recent_season
        ].copy()

        avail_heat = [c for c in RAW_STAT_COLS if c in recent_stats.columns]
        if not recent_stats.empty and avail_heat:
            # Group by team, compute mean per stat
            team_field = (recent_stats.groupby('team')[avail_heat]
                          .mean()
                          .reset_index())

            # Normalize to field percentile for each stat
            norm_field = team_field[['team']].copy()
            for col in avail_heat:
                field_vals = team_field[col].dropna()
                norm_field[col] = team_field[col].apply(
                    lambda x: round((field_vals < x).mean() * 100, 1) if pd.notna(x) else 50.0
                )

            norm_field = norm_field.set_index('team')
            norm_field.columns = [RAW_STAT_LABELS[RAW_STAT_COLS.index(c)] for c in avail_heat]

            fig_hm = px.imshow(
                norm_field,
                color_continuous_scale='RdYlGn',
                zmin=0, zmax=100,
                aspect='auto',
                title=f'All Teams — Raw Stat Percentiles vs LIV Field ({most_recent_season})',
            )
            fig_hm.update_layout(
                paper_bgcolor='#0e0e1a', font_color='white', height=420,
                coloraxis_colorbar=dict(title='Percentile'),
            )
            # Highlight selected team row
            team_names = norm_field.index.tolist()
            if selected_team in team_names:
                row_idx = team_names.index(selected_team)
                fig_hm.add_shape(
                    type='rect',
                    x0=-0.5, x1=len(avail_heat) - 0.5,
                    y0=row_idx - 0.5, y1=row_idx + 0.5,
                    line=dict(color='#c9a227', width=2),
                )
            st.plotly_chart(fig_hm, use_container_width=True)
            st.caption(f"Selected team ({selected_team}) highlighted in gold. Season: {most_recent_season}.")

    # ── All-teams SG comparison heatmap (2025 model predictions) ──────────────
    st.markdown("---")
    st.subheader("All-Teams Estimated SG Comparison (2025)")

    teams_sg = (val_2025_team[val_2025_team['team'].notna() & (val_2025_team['team'] != '')]
                .groupby('team')[SG_COLS].mean().reset_index())

    norm_teams_sg = teams_sg[['team']].copy()
    for sg_col in SG_COLS:
        field_vals = teams_sg[sg_col].dropna()
        norm_teams_sg[sg_col] = teams_sg[sg_col].apply(
            lambda x: round((field_vals < x).mean() * 100, 1) if pd.notna(x) else 50.0
        )
    norm_teams_sg = norm_teams_sg.set_index('team')
    norm_teams_sg.columns = SG_LABELS

    fig_sg_all = px.imshow(
        norm_teams_sg,
        color_continuous_scale='RdYlGn',
        zmin=0, zmax=100,
        text_auto='.0f',
        aspect='auto',
        title='All Teams — Estimated SG Percentiles (2025, XGBoost)',
    )
    fig_sg_all.update_layout(
        paper_bgcolor='#0e0e1a', font_color='white', height=420,
        coloraxis_colorbar=dict(title='Percentile'),
    )
    team_names_sg = norm_teams_sg.index.tolist()
    if selected_team in team_names_sg:
        row_idx_sg = team_names_sg.index(selected_team)
        fig_sg_all.add_shape(
            type='rect',
            x0=-0.5, x1=len(SG_COLS) - 0.5,
            y0=row_idx_sg - 0.5, y1=row_idx_sg + 0.5,
            line=dict(color='#c9a227', width=2),
        )
    st.plotly_chart(fig_sg_all, use_container_width=True)
    st.caption(f"Selected team ({selected_team}) highlighted in gold. Values are team-average XGBoost SG estimates for 2025.")
