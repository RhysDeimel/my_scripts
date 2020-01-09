import generate_pipelines as gp
import socket
import threading
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import pytest
import requests


def gen_expected(name, filename):
    return {
        "description": f"Auto-generated pipeline for deploying {name} infrastructure",
        "default_branch": "master",
        "name": f"DevOps - Deploy - {name}",
        "repository": "git@github.com:an_org/a_repo.git",
        "steps": [
            {
                "type": "script",
                "name": ":pipeline: Uploading Pipeline",
                "command": f"buildkite-agent pipeline upload .buildkite/this/{filename}",
            }
        ],
    }


class MockServerRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, code):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        if (
            self.path
            == "/v2/organizations/an-org/pipelines/devops-deploy-not-a-pipeline"
        ):
            self._set_headers(404)
        elif (
            self.path
            == "/v2/organizations/an-org/pipelines/devops-deploy-should-raise-exception"
        ):
            self._set_headers(503)
        else:
            self._set_headers(200)

        return

    def do_POST(self):
        self._set_headers(201)
        # read the data param that requests sends
        print(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
        return

    def do_PATCH(self):
        self._set_headers(200)
        print(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
        return

    def do_DELETE(self):
        self._set_headers(204)
        return


def get_free_port():
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(("localhost", 0))
    address, port = s.getsockname()
    s.close()
    return port


@pytest.fixture(scope="function")
def mock_server():
    port = get_free_port()
    gp.BUILDKITE_URL = f"http://localhost:{port}"

    mock_server = HTTPServer(("localhost", port), MockServerRequestHandler)
    mock_server_thread = threading.Thread(target=mock_server.serve_forever, daemon=True)
    yield mock_server_thread

    mock_server.shutdown()
    gp.BUILDKITE_URL = "https://api.buildkite.com"


class TestUnit:
    def test_get_files_returns_single_file(self, tmp_path):
        fp = tmp_path / "pipeline.service.test.yml"
        fp.write_text("")  # so file is created

        result = list(gp.get_files(tmp_path))
        assert len(result) == 1
        assert result[0].name == "pipeline.service.test.yml"

    def test_get_files_returns_multiple_files(self, tmp_path):
        fp = tmp_path / "pipeline.service.test0.yml"
        fp.write_text("")
        fp = tmp_path / "pipeline.service.test1.yml"
        fp.write_text("")

        result = list(gp.get_files(tmp_path))
        assert len(result) == 2
        assert result[0].name == "pipeline.service.test0.yml"
        assert result[1].name == "pipeline.service.test1.yml"

    def test_pipeline_class_init(self, tmp_path):
        fp = tmp_path / "pipeline.service.test.yml"
        result = gp.Pipeline(fp)

        assert result.filename == "pipeline.service.test.yml"
        assert result.name == "test"
        assert result.slug == "devops-deploy-test"

    def test_pipeline_class_gen_slug(self, tmp_path):
        fp = tmp_path / "pipeline.service.not-a-pipeline.yml"
        pipeline = gp.Pipeline(fp)

        assert pipeline.slug == "devops-deploy-not-a-pipeline"

    def test_pipeline_class_checks_for_pipeline_existence(self, tmp_path, mock_server):
        fp = tmp_path / "pipeline.service.is-a-pipeline.yml"

        mock_server.start()

        pipeline = gp.Pipeline(fp)
        pipeline._exists()
        assert pipeline.responses == [("GET", 200)]

    def test_pipeline_class_will_raise_error_on_existence_check(
        self, tmp_path, mock_server
    ):
        fp = tmp_path / "pipeline.should-raise-exception.yml"

        mock_server.start()

        pipeline = gp.Pipeline(fp)

        with pytest.raises(requests.HTTPError):
            pipeline._exists()

    def test_pipeline_class_creates_buildkite_pipeline(
        self, tmp_path, capsys, mock_server
    ):
        fp = tmp_path / "pipeline.service.is-a-pipeline.yml"

        mock_server.start()

        pipeline = gp.Pipeline(fp)
        pipeline._create()
        captured = capsys.readouterr()

        result = pipeline.responses
        assert result == [("POST", 201)]
        assert json.loads(captured.out) == gen_expected(
            "is-a-pipeline", "pipeline.service.is-a-pipeline.yml"
        )

    def test_pipeline_class_will_update_existing(self, tmp_path, capsys, mock_server):
        fp = tmp_path / "pipeline.service.is-a-pipeline.yml"

        mock_server.start()

        pipeline = gp.Pipeline(fp)
        pipeline._update()
        captured = capsys.readouterr()

        result = pipeline.responses
        assert result == [("PATCH", 200)]
        assert json.loads(captured.out) == gen_expected(
            "is-a-pipeline", "pipeline.service.is-a-pipeline.yml"
        )

    def test_pipeline_class_will_delete(self, tmp_path, mock_server):
        fp = tmp_path / "pipeline.service.is-a-pipeline.yml"

        mock_server.start()

        pipeline = gp.Pipeline(fp)

        assert pipeline._delete() == 204


class TestFunctional:
    def test_will_create_pipeline_given_file(self, tmp_path, capsys, mock_server):
        fp = tmp_path / "pipeline.service.not-a-pipeline.yml"
        fp.write_text("")  # so file is created

        mock_server.start()

        result = gp.generate_pipelines(tmp_path)
        captured = capsys.readouterr()

        # should have a 404 returned on first get
        assert result == [[("GET", 404), ("POST", 201)]]
        # check data param is being sent to server
        assert json.loads(captured.out) == gen_expected(
            "not-a-pipeline", "pipeline.service.not-a-pipeline.yml"
        )

    def test_will_update_pipeline_given_file(self, tmp_path, capsys, mock_server):
        fp = tmp_path / "pipeline.service.is-a-pipeline.yml"
        fp.write_text("")  # so file is created

        mock_server.start()

        result = gp.generate_pipelines(tmp_path)
        captured = capsys.readouterr()

        # should have a 200 returned on get
        assert result == [[("GET", 200), ("PATCH", 200)]]
        assert json.loads(captured.out) == gen_expected(
            "is-a-pipeline", "pipeline.service.is-a-pipeline.yml"
        )

    def test_will_create_multiple_pipelines(self, tmp_path, capsys, mock_server):
        fp_1 = tmp_path / "pipeline.service.is-a-pipeline.yml"
        fp_2 = tmp_path / "pipeline.service.is-another-pipeline.yml"
        fp_1.write_text("")
        fp_2.write_text("")

        mock_server.start()

        result = gp.generate_pipelines(tmp_path)
        captured = capsys.readouterr()
        resp = captured.out.split("\n")

        # should have a 200 returned on get
        assert result == [
            [("GET", 200), ("PATCH", 200)],
            [("GET", 200), ("PATCH", 200)],
        ]
        assert json.loads(resp[0]) == gen_expected(
            "is-a-pipeline", "pipeline.service.is-a-pipeline.yml"
        )
        assert json.loads(resp[1]) == gen_expected(
            "is-another-pipeline", "pipeline.service.is-another-pipeline.yml"
        )


class TestIntegration:
    """
    Calls Buildkite API. Will test for presence of API key
    """

    def test_class_can_get_existing_pipeline(self, tmp_path):
        fp = tmp_path / "pipeline.service.a_repo.yml"

        pipeline = gp.Pipeline(fp)
        assert pipeline._exists() is True

    def test_class_can_create_pipeline(self, tmp_path):
        fp = tmp_path / "pipeline.service.test-pipeline.yml"

        pipeline = gp.Pipeline(fp)
        try:
            pipeline._create()
            assert pipeline.responses == [("POST", 201)]
        finally:
            pipeline._delete()

    def test_class_can_update_pipeline(self, tmp_path):
        fp = tmp_path / "pipeline.service.test-pipeline.yml"

        pipeline = gp.Pipeline(fp)
        try:
            pipeline._create()  # setup
            pipeline._update()
            assert pipeline.responses == [("POST", 201), ("PATCH", 200)]
        finally:
            pipeline._delete()
