#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE dagster_db;
    CREATE DATABASE mlflow_db;

    \c electricity;

    CREATE SCHEMA IF NOT EXISTS bronze;
    CREATE SCHEMA IF NOT EXISTS silver;

    -- Bronze tables are created/managed by DLT at runtime.
    -- Weather still uses raw_payload JSONB.
    -- Demand now uses flat columns (time, region_id, demand_mw).

    -- Silver: clean, typed, no NULLs on key columns
    CREATE TABLE IF NOT EXISTS silver.demand_hourly (
        time TIMESTAMPTZ NOT NULL,
        region_id VARCHAR(10) NOT NULL,
        demand_mw NUMERIC NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (time, region_id)
    );

    CREATE TABLE IF NOT EXISTS silver.demand_5min (
        time TIMESTAMPTZ NOT NULL,
        region_id VARCHAR(10) NOT NULL,
        demand_mw NUMERIC NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (time, region_id)
    );

    CREATE TABLE IF NOT EXISTS silver.weather_hourly (
        time TIMESTAMPTZ NOT NULL,
        region_id VARCHAR(10) NOT NULL,
        temperature_2m NUMERIC NOT NULL,
        relative_humidity_2m NUMERIC NOT NULL,
        precipitation NUMERIC NOT NULL DEFAULT 0,
        cloud_cover NUMERIC NOT NULL DEFAULT 0,
        wind_speed_10m NUMERIC NOT NULL,
        shortwave_radiation NUMERIC NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (time, region_id)
    );

    CREATE TABLE IF NOT EXISTS silver.features_ml (
        time TIMESTAMPTZ NOT NULL,
        region_id VARCHAR(10) NOT NULL,
        demand_mw NUMERIC NOT NULL,
        temperature_2m NUMERIC,
        relative_humidity_2m NUMERIC,
        precipitation NUMERIC,
        cloud_cover NUMERIC,
        wind_speed_10m NUMERIC,
        shortwave_radiation NUMERIC,
        hour INT NOT NULL,
        day_of_week INT NOT NULL,
        is_weekend BOOLEAN NOT NULL,
        month INT NOT NULL,
        season INT NOT NULL,
        season_name VARCHAR(10) NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (time, region_id)
    );
EOSQL
