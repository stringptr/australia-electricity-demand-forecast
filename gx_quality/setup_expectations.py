import os

import great_expectations as gx

from gx_quality.context import DATABASE_URL, get_context

VALID_REGIONS = ["NSW1", "QLD1", "SA1", "TAS1", "VIC1"]
ROW_COUNT_MAX = 10_000_000
DATASOURCE_NAME = "electricity_db"

TABLE_SPECS = {
    "bronze.demand": ("demand", "bronze"),
    "bronze.weather": ("weather", "bronze"),
    "silver.demand_5min": ("demand_5min", "silver"),
    "silver.weather_hourly": ("weather_hourly", "silver"),
    "silver.features_ml": ("features_ml", "silver"),
    "silver.predictions": ("predictions", "silver"),
}


def _get_datasource():
    context = get_context()
    try:
        return context.data_sources.add_postgres(
            name=DATASOURCE_NAME,
            connection_string=DATABASE_URL,
        )
    except Exception:
        return context.data_sources.get(DATASOURCE_NAME)


def _build_batch_request(table_name, schema_name):
    ds = _get_datasource()
    asset_name = f"{schema_name}_{table_name}"
    try:
        asset = ds.add_table_asset(
            name=asset_name,
            table_name=table_name,
            schema_name=schema_name,
        )
    except ValueError:
        asset = ds.get_asset(asset_name)
    return asset_name, asset.build_batch_request()


def _define_bronze_demand():
    asset_name, br = _build_batch_request("demand", "bronze")
    v = get_context().get_validator(batch_request=br)
    v.expect_table_row_count_to_be_between(min_value=1, max_value=ROW_COUNT_MAX)
    v.expect_column_values_to_not_be_null("time")
    v.expect_column_values_to_not_be_null("region_id")
    v.expect_column_values_to_be_in_set("region_id", VALID_REGIONS)
    v.expect_column_values_to_be_between(
        "demand_mw", min_value=0, max_value=20000, mostly=0.9
    )
    v.save_expectation_suite(
        "bronze.demand", discard_failed_expectations=False
    )
    return asset_name


def _define_bronze_weather():
    asset_name, br = _build_batch_request("weather", "bronze")
    v = get_context().get_validator(batch_request=br)
    v.expect_table_row_count_to_be_between(min_value=1, max_value=ROW_COUNT_MAX)
    v.expect_column_values_to_not_be_null("time")
    v.expect_column_values_to_not_be_null("region_id")
    v.expect_column_values_to_not_be_null("temperature_2m")
    v.expect_column_values_to_be_in_set("region_id", VALID_REGIONS)
    v.expect_column_values_to_be_between("temperature_2m", -10, 55, mostly=0.95)
    v.expect_column_values_to_be_between(
        "relative_humidity_2m", 0, 100, mostly=0.95
    )
    v.expect_column_values_to_be_between("precipitation", 0, 500, mostly=0.95)
    v.expect_column_values_to_be_between("cloud_cover", 0, 100, mostly=0.95)
    v.expect_column_values_to_be_between("wind_speed_10m", 0, 200, mostly=0.95)
    v.expect_column_values_to_be_between(
        "shortwave_radiation", 0, 1500, mostly=0.95
    )
    v.save_expectation_suite(
        "bronze.weather", discard_failed_expectations=False
    )
    return asset_name


def _define_silver_demand_5min():
    asset_name, br = _build_batch_request("demand_5min", "silver")
    v = get_context().get_validator(batch_request=br)
    v.expect_table_row_count_to_be_between(min_value=1, max_value=ROW_COUNT_MAX)
    v.expect_column_values_to_not_be_null("time")
    v.expect_column_values_to_not_be_null("region_id")
    v.expect_column_values_to_not_be_null("demand_mw")
    v.expect_column_values_to_be_in_set("region_id", VALID_REGIONS)
    v.expect_column_values_to_be_between(
        "demand_mw", min_value=0, max_value=20000, mostly=0.95
    )
    v.expect_compound_columns_to_be_unique(["time", "region_id"])
    v.save_expectation_suite(
        "silver.demand_5min", discard_failed_expectations=False
    )
    return asset_name


def _define_silver_weather_hourly():
    asset_name, br = _build_batch_request("weather_hourly", "silver")
    v = get_context().get_validator(batch_request=br)
    v.expect_table_row_count_to_be_between(min_value=1, max_value=ROW_COUNT_MAX)
    v.expect_column_values_to_not_be_null("time")
    v.expect_column_values_to_not_be_null("region_id")
    v.expect_column_values_to_not_be_null("temperature_2m")
    v.expect_column_values_to_be_in_set("region_id", VALID_REGIONS)
    v.expect_column_values_to_be_between("temperature_2m", -10, 55, mostly=0.95)
    v.expect_column_values_to_be_between(
        "relative_humidity_2m", 0, 100, mostly=0.95
    )
    v.expect_column_values_to_be_between("precipitation", 0, 500, mostly=0.95)
    v.expect_column_values_to_be_between("cloud_cover", 0, 100, mostly=0.95)
    v.expect_column_values_to_be_between("wind_speed_10m", 0, 200, mostly=0.95)
    v.expect_column_values_to_be_between(
        "shortwave_radiation", 0, 1500, mostly=0.95
    )
    v.expect_compound_columns_to_be_unique(["time", "region_id"])
    v.save_expectation_suite(
        "silver.weather_hourly", discard_failed_expectations=False
    )
    return asset_name


def _define_silver_features_ml():
    asset_name, br = _build_batch_request("features_ml", "silver")
    v = get_context().get_validator(batch_request=br)
    v.expect_table_row_count_to_be_between(min_value=1, max_value=ROW_COUNT_MAX)
    v.expect_column_values_to_not_be_null("time")
    v.expect_column_values_to_not_be_null("region_id")
    v.expect_column_values_to_not_be_null("demand_mw")
    v.expect_column_values_to_not_be_null("hour")
    v.expect_column_values_to_not_be_null("day_of_week")
    v.expect_column_values_to_not_be_null("is_weekend")
    v.expect_column_values_to_not_be_null("month")
    v.expect_column_values_to_not_be_null("season")
    v.expect_column_values_to_be_in_set("region_id", VALID_REGIONS)
    v.expect_column_values_to_be_between(
        "demand_mw", min_value=0, max_value=20000, mostly=0.95
    )
    v.expect_column_values_to_be_between("hour", 0, 23)
    v.expect_column_values_to_be_between("day_of_week", 0, 6)
    v.expect_column_values_to_be_between("month", 1, 12)
    v.expect_column_values_to_be_between("season", 1, 4)
    v.expect_compound_columns_to_be_unique(["time", "region_id"])
    v.save_expectation_suite(
        "silver.features_ml", discard_failed_expectations=False
    )
    return asset_name


def _define_silver_predictions():
    asset_name, br = _build_batch_request("predictions", "silver")
    v = get_context().get_validator(batch_request=br)
    v.expect_table_row_count_to_be_between(min_value=5, max_value=1000000)
    v.expect_column_values_to_not_be_null("created_at")
    v.expect_column_values_to_not_be_null("region_id")
    v.expect_column_values_to_be_in_set("region_id", VALID_REGIONS)
    for h in range(1, 25):
        col = f"horizon_h{h:02d}"
        v.expect_column_values_to_not_be_null(col)
        v.expect_column_values_to_be_between(col, 0, 25000, mostly=0.95)
    v.save_expectation_suite(
        "silver.predictions", discard_failed_expectations=False
    )
    return asset_name


SUITE_BUILDERS = {
    "bronze.demand": _define_bronze_demand,
    "bronze.weather": _define_bronze_weather,
    "silver.demand_5min": _define_silver_demand_5min,
    "silver.weather_hourly": _define_silver_weather_hourly,
    "silver.features_ml": _define_silver_features_ml,
    "silver.predictions": _define_silver_predictions,
}

CHECKPOINT_GROUPS = {
    "bronze_validation": ["bronze.demand", "bronze.weather"],
    "silver_validation": ["silver.demand_5min", "silver.weather_hourly"],
    "features_validation": ["silver.features_ml"],
    "predictions_validation": ["silver.predictions"],
}


def setup_suites():
    asset_names = {}
    for suite_name, builder in SUITE_BUILDERS.items():
        asset_names[suite_name] = builder()
    return asset_names


def setup_checkpoints(asset_names: dict[str, str]):
    context = get_context()
    ds = _get_datasource()
    for cp_name, suite_names in CHECKPOINT_GROUPS.items():
        validations = []
        for sn in suite_names:
            table_name, schema_name = TABLE_SPECS[sn]
            try:
                asset = ds.add_table_asset(
                    name=asset_names[sn],
                    table_name=table_name,
                    schema_name=schema_name,
                )
            except ValueError:
                asset = ds.get_asset(asset_names[sn])
            validations.append(
                {
                    "batch_request": asset.build_batch_request(),
                    "expectation_suite_name": sn,
                }
            )
        context.checkpoints.add_or_update(cp_name, validations)


def setup_all():
    asset_names = setup_suites()
    setup_checkpoints(asset_names)
    print("Great Expectations suites and checkpoints created.")
