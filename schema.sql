--
-- PostgreSQL database dump
--

\restrict SseWkT1U5wleYFqVUKgIngzytXkG8xC4NSOiahdAG6sh1b9zw6d0Ucca3MLYPhM

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: nfl_betting_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nfl_betting_snapshots (
    snapshot_id bigint NOT NULL,
    game_id text NOT NULL,
    provider_id text,
    provider_name text,
    away_team_id text,
    home_team_id text,
    away_moneyline integer,
    home_moneyline integer,
    away_spread numeric(5,2),
    home_spread numeric(5,2),
    away_spread_odds integer,
    home_spread_odds integer,
    total numeric(5,2),
    over_odds integer,
    under_odds integer,
    opening_away_moneyline integer,
    opening_home_moneyline integer,
    opening_away_spread numeric(5,2),
    opening_home_spread numeric(5,2),
    opening_total numeric(5,2),
    captured_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: nfl_betting_snapshots_snapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.nfl_betting_snapshots_snapshot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: nfl_betting_snapshots_snapshot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.nfl_betting_snapshots_snapshot_id_seq OWNED BY public.nfl_betting_snapshots.snapshot_id;


--
-- Name: nfl_depth_chart; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nfl_depth_chart (
    team_id text NOT NULL,
    unit text,
    position_slot text NOT NULL,
    "position" text,
    player_id text NOT NULL,
    player_name text,
    depth_order integer,
    position_group text
);


--
-- Name: nfl_games; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nfl_games (
    game_id text NOT NULL,
    game_date timestamp with time zone,
    home_team text,
    away_team text,
    venue text,
    season integer,
    week integer,
    home_logo text,
    away_logo text,
    home_record text,
    away_record text,
    home_home_record text,
    home_road_record text,
    away_home_record text,
    away_road_record text,
    home_team_id text,
    away_team_id text,
    home_score integer,
    away_score integer,
    game_state text,
    game_status text,
    completed boolean,
    venue_id text,
    venue_city text,
    venue_state text,
    venue_zip text,
    venue_country text,
    venue_latitude numeric,
    venue_longitude numeric,
    venue_timezone text,
    venue_type text
);


--
-- Name: nfl_injuries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nfl_injuries (
    game_id text NOT NULL,
    team_id text NOT NULL,
    player_id text NOT NULL,
    player_name text,
    jersey text,
    "position" text,
    headshot text,
    status text,
    injury_type text,
    injury_location text,
    injury_detail text,
    injury_side text,
    injury_date timestamp without time zone,
    return_date date,
    captured_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    snapshot_id bigint
);


--
-- Name: nfl_injury_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nfl_injury_snapshots (
    snapshot_id bigint NOT NULL,
    game_id text NOT NULL,
    team_id text NOT NULL,
    captured_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: nfl_injury_snapshots_snapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.nfl_injury_snapshots_snapshot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: nfl_injury_snapshots_snapshot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.nfl_injury_snapshots_snapshot_id_seq OWNED BY public.nfl_injury_snapshots.snapshot_id;


--
-- Name: nfl_player_game_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nfl_player_game_stats (
    game_id text NOT NULL,
    team_id text,
    team_name text,
    player_id text NOT NULL,
    player_name text,
    jersey text,
    headshot text,
    completions_attempts text,
    passing_yards integer,
    yards_per_pass_attempt numeric,
    passing_touchdowns integer,
    passing_interceptions integer,
    sacks_sack_yards_lost text,
    qbr numeric,
    passer_rating numeric,
    rushing_attempts integer,
    rushing_yards integer,
    yards_per_rush_attempt numeric,
    rushing_touchdowns integer,
    long_rushing integer,
    receptions integer,
    receiving_yards integer,
    yards_per_reception numeric,
    receiving_touchdowns integer,
    long_reception integer,
    receiving_targets integer,
    fumbles integer,
    fumbles_lost integer,
    fumbles_recovered integer,
    total_tackles integer,
    solo_tackles integer,
    sacks numeric,
    tackles_for_loss numeric,
    passes_defended integer,
    qb_hits integer,
    defensive_touchdowns integer,
    defensive_interceptions integer,
    interception_yards integer,
    interception_touchdowns integer,
    kick_returns integer,
    kick_return_yards integer,
    yards_per_kick_return numeric,
    long_kick_return integer,
    kick_return_touchdowns integer,
    punt_returns integer,
    punt_return_yards integer,
    yards_per_punt_return numeric,
    long_punt_return integer,
    punt_return_touchdowns integer,
    field_goals_made_attempted text,
    field_goal_pct numeric,
    long_field_goal_made integer,
    extra_points_made_attempted text,
    total_kicking_points integer,
    punts integer,
    punt_yards integer,
    gross_avg_punt_yards numeric,
    touchbacks integer,
    punts_inside_20 integer,
    long_punt integer,
    forced_fumbles integer
);


--
-- Name: nfl_players; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nfl_players (
    player_id text NOT NULL,
    team_id text,
    player_name text,
    first_name text,
    last_name text,
    jersey text,
    "position" text,
    position_name text,
    position_group text,
    status text,
    experience_years integer,
    height_inches numeric,
    weight_lbs numeric,
    college text,
    headshot text
);


--
-- Name: nfl_team_game_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nfl_team_game_stats (
    game_id text NOT NULL,
    team_id text NOT NULL,
    team_name text,
    home_away text,
    first_downs integer,
    third_down_eff text,
    fourth_down_eff text,
    total_plays integer,
    total_yards integer,
    yards_per_play numeric,
    total_drives integer,
    passing_yards integer,
    completions_attempts text,
    yards_per_pass numeric,
    interceptions integer,
    sacks_yards_lost text,
    rushing_yards integer,
    rushing_attempts integer,
    yards_per_rush numeric,
    red_zone_eff text,
    penalties_yards text,
    turnovers integer,
    fumbles_lost integer,
    defensive_touchdowns integer,
    possession_time text
);


--
-- Name: nfl_team_standings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nfl_team_standings (
    season integer NOT NULL,
    team_id text NOT NULL,
    team_name text,
    conference text,
    overall_record text,
    home_record text,
    road_record text,
    division_record text,
    conference_record text,
    streak text,
    conference_seed integer,
    points_for integer,
    points_against integer,
    point_differential integer
);


--
-- Name: nfl_weather_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nfl_weather_snapshots (
    weather_snapshot_id bigint NOT NULL,
    game_id text NOT NULL,
    forecast_time timestamp with time zone,
    temperature_f numeric,
    apparent_temperature_f numeric,
    precipitation_probability numeric,
    precipitation_inches numeric,
    relative_humidity numeric,
    wind_speed_mph numeric,
    wind_gust_mph numeric,
    wind_direction_degrees numeric,
    weather_code integer,
    captured_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: nfl_weather_snapshots_weather_snapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.nfl_weather_snapshots_weather_snapshot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: nfl_weather_snapshots_weather_snapshot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.nfl_weather_snapshots_weather_snapshot_id_seq OWNED BY public.nfl_weather_snapshots.weather_snapshot_id;


--
-- Name: nfl_betting_snapshots snapshot_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_betting_snapshots ALTER COLUMN snapshot_id SET DEFAULT nextval('public.nfl_betting_snapshots_snapshot_id_seq'::regclass);


--
-- Name: nfl_injury_snapshots snapshot_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_injury_snapshots ALTER COLUMN snapshot_id SET DEFAULT nextval('public.nfl_injury_snapshots_snapshot_id_seq'::regclass);


--
-- Name: nfl_weather_snapshots weather_snapshot_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_weather_snapshots ALTER COLUMN weather_snapshot_id SET DEFAULT nextval('public.nfl_weather_snapshots_weather_snapshot_id_seq'::regclass);


--
-- Name: nfl_betting_snapshots nfl_betting_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_betting_snapshots
    ADD CONSTRAINT nfl_betting_snapshots_pkey PRIMARY KEY (snapshot_id);


--
-- Name: nfl_depth_chart nfl_depth_chart_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_depth_chart
    ADD CONSTRAINT nfl_depth_chart_pkey PRIMARY KEY (team_id, position_slot, player_id);


--
-- Name: nfl_games nfl_games_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_games
    ADD CONSTRAINT nfl_games_pkey PRIMARY KEY (game_id);


--
-- Name: nfl_injuries nfl_injuries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_injuries
    ADD CONSTRAINT nfl_injuries_pkey PRIMARY KEY (game_id, team_id, player_id, captured_at);


--
-- Name: nfl_injury_snapshots nfl_injury_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_injury_snapshots
    ADD CONSTRAINT nfl_injury_snapshots_pkey PRIMARY KEY (snapshot_id);


--
-- Name: nfl_player_game_stats nfl_player_game_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_player_game_stats
    ADD CONSTRAINT nfl_player_game_stats_pkey PRIMARY KEY (game_id, player_id);


--
-- Name: nfl_players nfl_players_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_players
    ADD CONSTRAINT nfl_players_pkey PRIMARY KEY (player_id);


--
-- Name: nfl_team_game_stats nfl_team_game_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_team_game_stats
    ADD CONSTRAINT nfl_team_game_stats_pkey PRIMARY KEY (game_id, team_id);


--
-- Name: nfl_team_standings nfl_team_standings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_team_standings
    ADD CONSTRAINT nfl_team_standings_pkey PRIMARY KEY (season, team_id);


--
-- Name: nfl_weather_snapshots nfl_weather_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_weather_snapshots
    ADD CONSTRAINT nfl_weather_snapshots_pkey PRIMARY KEY (weather_snapshot_id);


--
-- Name: idx_betting_game_captured; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_betting_game_captured ON public.nfl_betting_snapshots USING btree (game_id, captured_at DESC);


--
-- Name: nfl_injuries nfl_injuries_snapshot_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_injuries
    ADD CONSTRAINT nfl_injuries_snapshot_fk FOREIGN KEY (snapshot_id) REFERENCES public.nfl_injury_snapshots(snapshot_id);


--
-- Name: nfl_weather_snapshots nfl_weather_game_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nfl_weather_snapshots
    ADD CONSTRAINT nfl_weather_game_fk FOREIGN KEY (game_id) REFERENCES public.nfl_games(game_id);


--
-- PostgreSQL database dump complete
--

\unrestrict SseWkT1U5wleYFqVUKgIngzytXkG8xC4NSOiahdAG6sh1b9zw6d0Ucca3MLYPhM

