import os
import logging

import httpx

logger = logging.getLogger(__name__)

DAGSTER_GRAPHQL_URL = os.getenv(
    "DAGSTER_GRAPHQL_URL",
    "http://dagster-webserver:3000/graphql",
)

MUTATION = """
mutation LaunchRunForAssets {
  launchRun(
    executionParams: {
      selector: {
        repositoryLocationName: "user_code"
        repositoryName: "__repository__"
        jobName: "__ASSET_JOB"
        assetSelection: [
          {path: ["silver", "demand_5min"]},
          {path: ["silver", "weather_hourly"]},
          {path: ["silver", "features_ml"]}
        ]
      }
    }
  ) {
    __typename
    ... on LaunchRunSuccess {
      run {
        runId
      }
    }
    ... on Error {
      message
    }
  }
}
"""


def trigger_silver_assets():
    try:
        resp = httpx.post(DAGSTER_GRAPHQL_URL, json={"query": MUTATION}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            logger.warning("Dagster GraphQL errors: %s", data["errors"])
        else:
            result = data.get("data", {}).get("launchRun", {})
            if result.get("__typename") == "LaunchRunSuccess":
                run_id = result.get("run", {}).get("runId", "unknown")
                logger.info("Silver run launched: %s", run_id)
            else:
                logger.warning("Dagster launch failed: %s", result.get("message"))
    except httpx.RequestError as e:
        logger.warning("Cannot reach Dagster: %s", e)
