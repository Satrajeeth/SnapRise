--
-- PostgreSQL database dump
--

\restrict CvXUHWzysP76HMZ6qHY1bvN0OaQMaotIkO9JjHG0CPAgXLP0Bpl2OaILMxOegvJ

-- Dumped from database version 16.12 (Debian 16.12-1.pgdg13+1)
-- Dumped by pg_dump version 16.12 (Homebrew)

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

CREATE EXTENSION IF NOT EXISTS "pgcrypto";


CREATE INDEX ix_otp_challenges_lookup
ON otp_challenges (tenant_id, email, purpose);

CREATE INDEX ix_otp_challenges_expires
ON otp_challenges (expires_at);

CREATE INDEX ix_otp_delivery_attempts_challenge
ON otp_delivery_attempts (challenge_id);

CREATE INDEX ix_otp_retry_jobs_challenge
ON otp_retry_jobs (challenge_id);
--
-- Name: otp_challenges; Type: TABLE; Schema: public; Owner: app
--

CREATE TABLE public.otp_challenges (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    email text NOT NULL,
    purpose text NOT NULL,
    otp_hash text NOT NULL,
    salt text NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    status text NOT NULL,
    attempt_count integer DEFAULT 0,
    next_allowed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    verified_at timestamp without time zone
);


ALTER TABLE public.otp_challenges OWNER TO app;

--
-- Name: otp_delivery_attempts; Type: TABLE; Schema: public; Owner: app
--

CREATE TABLE public.otp_delivery_attempts (
    id uuid NOT NULL,
    challenge_id uuid NOT NULL,
    provider_id text NOT NULL,
    tier text NOT NULL,
    results text NOT NULL,
    error_type text,
    latency_ms integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.otp_delivery_attempts OWNER TO app;

--
-- Name: otp_retry_jobs; Type: TABLE; Schema: public; Owner: app
--

CREATE TABLE public.otp_retry_jobs (
    id uuid NOT NULL,
    challenge_id uuid NOT NULL,
    status text NOT NULL,
    attempt_count integer DEFAULT 0,
    next_retry_at timestamp without time zone NOT NULL,
    last_error text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.otp_retry_jobs OWNER TO app;

--
-- Name: provider_config; Type: TABLE; Schema: public; Owner: app
--

CREATE TABLE public.provider_config (
    provider_id uuid NOT NULL,
    tier text NOT NULL,
    enabled boolean NOT NULL,
    weight numeric(5,2) NOT NULL,
    priority integer NOT NULL,
    daily_limit integer NOT NULL,
    monthly_limit integer NOT NULL,
    settings_json jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_daily_limit CHECK ((daily_limit >= 0)),
    CONSTRAINT chk_monthly_limit CHECK ((monthly_limit >= 0)),
    CONSTRAINT chk_priority_positive CHECK ((priority >= 0)),
    CONSTRAINT chk_weight_positive CHECK ((weight > (0)::numeric))
);


ALTER TABLE public.provider_config OWNER TO app;

--
-- Name: user; Type: TABLE; Schema: public; Owner: app
--

CREATE TABLE public."user" (
    id uuid NOT NULL,
    email character varying(320) NOT NULL,
    hashed_password character varying(1024) NOT NULL,
    is_active boolean NOT NULL,
    is_superuser boolean NOT NULL,
    is_verified boolean NOT NULL
);


ALTER TABLE public."user" OWNER TO app;

--
-- Name: otp_challenges otp_challenges_pkey; Type: CONSTRAINT; Schema: public; Owner: app
--

ALTER TABLE ONLY public.otp_challenges
    ADD CONSTRAINT otp_challenges_pkey PRIMARY KEY (id);


--
-- Name: otp_delivery_attempts otp_delivery_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: app
--

ALTER TABLE ONLY public.otp_delivery_attempts
    ADD CONSTRAINT otp_delivery_attempts_pkey PRIMARY KEY (id);


--
-- Name: otp_retry_jobs otp_retry_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: app
--

ALTER TABLE ONLY public.otp_retry_jobs
    ADD CONSTRAINT otp_retry_jobs_pkey PRIMARY KEY (id);


--
-- Name: provider_config provider_config_pkey; Type: CONSTRAINT; Schema: public; Owner: app
--

ALTER TABLE ONLY public.provider_config
    ADD CONSTRAINT provider_config_pkey PRIMARY KEY (provider_id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: app
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: ix_user_email; Type: INDEX; Schema: public; Owner: app
--

CREATE UNIQUE INDEX ix_user_email ON public."user" USING btree (email);


--
-- Name: otp_delivery_attempts fk_challenge; Type: FK CONSTRAINT; Schema: public; Owner: app
--

ALTER TABLE ONLY public.otp_delivery_attempts
    ADD CONSTRAINT fk_challenge FOREIGN KEY (challenge_id) REFERENCES public.otp_challenges(id) ON DELETE CASCADE;


--
-- Name: otp_retry_jobs fk_retry_challenge; Type: FK CONSTRAINT; Schema: public; Owner: app
--

ALTER TABLE ONLY public.otp_retry_jobs
    ADD CONSTRAINT fk_retry_challenge FOREIGN KEY (challenge_id) REFERENCES public.otp_challenges(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict CvXUHWzysP76HMZ6qHY1bvN0OaQMaotIkO9JjHG0CPAgXLP0Bpl2OaILMxOegvJ

