#!/usr/bin/env python3
# python3.7+

"""
Script I wrote for some client automation. Had a folder with a series of files
that had the format "pipeline.service.<service_name>.yml"

This would get the list of filenames, and generate a pipeline based off it,
templating out with the data blob defaulted in the class
"""

import argparse
import json
import logging
import os
from pathlib import Path
import requests

BUILDKITE_URL = "https://api.buildkite.com"
API_KEY = os.environ.get("BUILDKITE_API_KEY")


def get_files(path):
    return sorted(Path(path).glob("*.yml"))


class Pipeline:
    endpoint = "v2/organizations/an-org/pipelines"

    def __init__(self, path):
        self.filename = path.name
        self.name = path.name.split(".")[-2]
        self.headers = {"Authorization": f"Bearer {API_KEY}"}
        self.data = {
            "description": f"Auto-generated pipeline for deploying {self.name} infrastructure",
            "default_branch": "master",
            "name": f"DevOps - Deploy - {self.name}",
            "repository": "git@github.com:an-org/a_repo.git",
            "steps": [
                {
                    "type": "script",
                    "name": ":pipeline: Uploading Pipeline",
                    "command": f"buildkite-agent pipeline upload .buildkite/this/{self.filename}",
                }
            ],
        }
        self.slug = self._gen_slug()
        self.responses = []

    def _gen_slug(self):
        return self.data["name"].lower().replace(" ", "")

    def _exists(self):
        r = requests.get(
            f"{BUILDKITE_URL}/{self.endpoint}/{self.slug}", headers=self.headers
        )
        # Only expecting 404 and 200
        if r.status_code != 404:
            r.raise_for_status()

        self.responses.append(("GET", r.status_code))
        return r.status_code == 200

    def _create(self):
        r = requests.post(
            f"{BUILDKITE_URL}/{self.endpoint}",
            data=json.dumps(self.data),
            headers=self.headers,
        )
        r.raise_for_status()
        self.responses.append(("POST", r.status_code))

    def _update(self):
        r = requests.patch(
            f"{BUILDKITE_URL}/{self.endpoint}/{self.slug}",
            data=json.dumps(self.data),
            headers=self.headers,
        )
        r.raise_for_status()
        self.responses.append(("PATCH", r.status_code))

    def _delete(self):
        r = requests.delete(
            f"{BUILDKITE_URL}/{self.endpoint}/{self.slug}", headers=self.headers
        )
        r.raise_for_status()
        return r.status_code

    def review(self):
        if not self._exists():
            self._create()
        else:
            self._update()

        return self.responses


def generate_pipelines(path):
    results = []

    for file in get_files(path):
        logging.info("Processing %s", file)
        plan = Pipeline(file)
        results.append(plan.review())

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Programmatically generate buildkite pipelines based on files found in the specified directory"
    )
    parser.add_argument("directory", help="the path to a directory of pipeline files")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    generate_pipelines(args.directory)
