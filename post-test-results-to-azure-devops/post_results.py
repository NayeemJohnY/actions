import json
import logging
from datetime import datetime, timezone

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

API_VERSION = "api-version=7.1"
RUN_URI = "/_apis/test/runs"
RESULTS_URI = RUN_URI + "/{run_id}/results"
TEST_PLANS_URI = "/_apis/testplan/plans"
TEST_SUITES_URI = TEST_PLANS_URI + "/{plan_id}/suites"
TEST_POINTS_URI = "/_apis/test/Plans/{plan_id}/Suites/{suite_id}/points"


class AzureDevOpsClient:

    is_failure = False

    def __init__(self, org_url: str, project: str, token: str):
        self.org_url = org_url
        self.project = project
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth("", token)
        self.session.hooks["response"].append(self.log_response)
        self.ado_uri = org_url.rstrip("/") + "/" + project.lstrip("/")

    def build_url(self, path: str, **kwargs):
        formatted_path = path.format(**kwargs) if kwargs else path
        return self.ado_uri + formatted_path + "?" + API_VERSION

    def log_response(self, response: requests.Response, *args, **kwargs):
        """Log details of the request and response."""
        logger.debug("Request Headers: %s", response.request.headers)
        logger.debug("Request Body: %s", response.request.body)
        logger.info(
            "%s : %s -> %s",
            response.request.method,
            response.request.url,
            response.status_code,
        )
        logger.debug("Response Headers: %s", response.headers)
        logger.debug("Response Body: %s", response.text)
        return response

    def get_test_plan_id(self, test_plan_name):
        response = self.session.get(self.build_url(TEST_PLANS_URI))
        response.raise_for_status()
        ado_response = response.json()
        for plan in ado_response["value"]:
            if plan["name"] == test_plan_name:
                return plan["id"]
        raise ValueError(f"Test plan '{test_plan_name}' not found")

    def get_test_suite_id(self, test_plan_id, test_suite_name):
        response = self.session.get(
            self.build_url(TEST_SUITES_URI, plan_id=test_plan_id)
        )
        response.raise_for_status()
        ado_response = response.json()
        for suite in ado_response["value"]:
            if suite["name"] == test_suite_name:
                return suite["id"]
        raise ValueError(
            f"Test suite '{test_suite_name}' not found in plan {test_plan_id}"
        )

    def get_test_points(self, test_plan_id, test_suite_id):
        response = self.session.get(
            self.build_url(
                TEST_POINTS_URI, plan_id=test_plan_id, suite_id=test_suite_id
            )
        )
        response.raise_for_status()
        ado_response = response.json()
        test_points = ado_response["value"]
        return [value["id"] for value in test_points]

    def create_test_run(
        self, test_plan_name, test_suite_name, test_plan_id, test_point_ids
    ):
        payload = {
            "name": f"Automation Test Run - {test_suite_name}",
            "plan": {"id": test_plan_id},
            "pointIds": test_point_ids,
            "automated": True,
            "comment": f"Automation Test Run Execution:\n"
            + f"- TestPlanName : {test_plan_name}\n"
            + f"- TestSuiteName : {test_suite_name}\n"
            + f"- Timestamp : {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        }
        response = self.session.post(self.build_url(RUN_URI), json=payload)
        response.raise_for_status()
        ado_response = response.json()
        run_id = ado_response["id"]
        logger.info("Test Run created Successfully in ADO. Run ID: %s", run_id)
        return run_id

    def process_test_results(self, run_id, test_results):
        test_results_payload = []
        response = self.session.get(self.build_url(RESULTS_URI, run_id=run_id))
        response.raise_for_status()
        ado_response = response.json()
        test_points_results = ado_response["value"]
        for point_result in test_points_results:
            result = test_results.get(
                point_result["testCase"]["id"], {"outcome": "NotExecuted"}
            )
            result.update(
                {
                    "id": point_result["id"],
                    "state": "Completed",
                    "priority": result.get("priority", 2),
                }
            )
            if result["outcome"] != "Passed":
                result["failureType"] = result.get("failureType", "New Issue")
                self.is_failure = True
            test_results_payload.append(result)
        return test_results_payload

    def post_test_results(self, run_id, test_results_payload):
        response = self.session.patch(
            self.build_url(RESULTS_URI, run_id=run_id), json=test_results_payload
        )
        if response.status_code != 200:
            raise ValueError(
                "Unexpected Response while posting test results to ADO: "
                + f"status_code: {response.status_code} response_text: {response.text}"
            )
        logger.info("Test Results Posted Successfully to ADO Run ID: %s", run_id)

    def complete_test_run(self, run_id):
        state = "NeedsInvestigation" if self.is_failure else "Completed"
        response = self.session.patch(
            self.build_url(RUN_URI + f"/{run_id}"),
            json={
                "state": state,
                "completedDate": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            },
        )
        if response.status_code != 200:
            raise ValueError(
                "Unexpected Response while completing the test run in ADO: "
                + f"status_code: {response.status_code} response_text: {response.text}"
            )
        logger.info("Test Run for Run ID: %s marked '%s' in ADO", run_id, state)


def main(args):
    try:
        with open(args.test_result_json, "r", encoding="utf-8") as f:
            test_results_json = json.load(f)

        test_plan_name = test_results_json["testPlanName"]
        test_suite_name = test_results_json["testSuiteName"]
        test_results = test_results_json["testResults"]

        ado_client = AzureDevOpsClient(args.org_url, args.project, args.token)
        test_plan_id = ado_client.get_test_plan_id(test_plan_name)
        test_suite_id = ado_client.get_test_suite_id(test_plan_id, test_suite_name)
        test_points = ado_client.get_test_points(test_plan_id, test_suite_id)
        run_id = ado_client.create_test_run(
            test_plan_name, test_suite_name, test_plan_id, test_points
        )
        test_results_payload = ado_client.process_test_results(run_id, test_results)
        ado_client.post_test_results(run_id, test_results_payload)
        ado_client.complete_test_run(run_id)

    except FileNotFoundError:
        logger.error("Test results file not found: %s", args.test_result_json)
        raise
    except KeyError as e:
        logger.error("Missing required field in test results JSON: %s", e)
        raise
    except Exception as e:
        logger.error("Error posting test results to Azure DevOps: %s", e)
        raise


if __name__ == "__main__":
    import argparse

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(threadName)s] [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Post test results to Azure DevOps Test Plans"
    )
    parser.add_argument(
        "--token", required=True, help="Azure DevOps Personal Access Token"
    )
    parser.add_argument(
        "--org-url",
        required=True,
        help="Azure DevOps organization URL (e.g., https://dev.azure.com/org)",
    )
    parser.add_argument("--project", required=True, help="Azure DevOps project name")
    parser.add_argument(
        "--test-result-json", required=True, help="Path to test results JSON file"
    )
    main(parser.parse_args())
