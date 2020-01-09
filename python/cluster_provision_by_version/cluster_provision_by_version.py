#!/usr/bin/env python3
# python3.7+

# Script for dynamically fetching service versions from a web versiondashboard
# and then injecting them into the buildkite pipeline. This is to replace
# hardcoded versions in the pipeline env vars.


import argparse
import subprocess
import requests

# update as required
ENDPOINTS = {
    "nonprod": "aaaaaaaaaa",
    "cde_nonprod": "bb222bbbbb",
    "prod": "ccc33ccccc",
    "cde_prod": "4ddddddd44",
}


def get_service_request(endpoint, env, key):
    """
    Calls the relevant AWS Apigateway endpoint with the required api key
    and passes the environment to get a response from the dashboard service

    Returns the request object
    """

    url = f"https://{endpoint}.execute-api.ap-southeast-2.amazonaws.com/live"
    data = {"env": f"{env}"}
    headers = {"content-Type": "x-www-form-urlencoded", "x-api-key": f"{key}"}

    r = requests.post(url, json=data, headers=headers)
    r.raise_for_status()
    return r


def store_versions(request):
    """
    Takes a requests object and extracts the version number for each service.
    Then calls the buildkite agent and stores it in metadata under two key names:
    <service_name>_version: x.x.x
    <service_name>_cf_friendly_version: x-x-x

    eg:
    device-service_version: 1.2.0
    device-service_cf_friendly_version: 1-2-0
    """

    services = {
        item["name"]: item["instances"][0]["healthz"]["version"].replace("v", "")
        for item in request.json()
    }

    for service, version in services.items():
        print(f"Setting {service}_version={version}")
        subprocess.run(
            ["buildkite-agent", "meta-data", "set", f"{service}_version", version],
            check=True,
        )
        print(f"Setting {service}_cf_friendly_version={version.replace('.', '-')}")
        subprocess.run(
            [
                "buildkite-agent",
                "meta-data",
                "set",
                f"{service}_cf_friendly_version",
                f"{version.replace('.', '-')}",
            ],
            check=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dynamically fetch service versions from the Dashboard Lambda"
    )
    parser.add_argument("account", choices=ENDPOINTS.keys(), help="account to target")
    parser.add_argument(
        "env",
        choices=["dev", "qa", "sb", "prod"],
        help="environment to get version information about",
    )
    parser.add_argument(
        "key",
        help="apigateway auth key that matches the specified account and environment",
    )
    args = parser.parse_args()

    # This is where the stuff is happening
    request = get_service_request(ENDPOINTS[args.account], args.env, args.key)
    store_versions(request)
