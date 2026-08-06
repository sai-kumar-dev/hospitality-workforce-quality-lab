"""Schemathesis checks against the generated local OpenAPI document."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import schemathesis
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from shiftbridge_qa.api import ShiftBridgeClient
from shiftbridge_qa.utilities import selected_contract_profile

if TYPE_CHECKING:
    from shiftbridge_qa.config import QASettings

pytestmark = pytest.mark.contract
PROFILE = selected_contract_profile()


@pytest.fixture(scope="module")
def openapi_schema(live_api: None, qa_settings: QASettings) -> object:
    return schemathesis.openapi.from_url(f"{qa_settings.api_base_url}/openapi.json")


def test_generated_openapi_exposes_expected_public_operations(
    openapi_schema: object,
) -> None:
    schema = openapi_schema

    assert schema["/health/live"]["GET"]  # type: ignore[index]
    assert schema["/api/auth/login"]["POST"]  # type: ignore[index]
    assert schema["/api/jobs"]["GET"]  # type: ignore[index]
    assert schema["/api/jobs/{job_id}/applications"]["POST"]  # type: ignore[index]


@settings(
    max_examples=PROFILE.max_examples,
    deadline=PROFILE.deadline_ms,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(data=st.data())
def test_schemathesis_generated_health_responses_conform_to_schema(
    data: st.DataObject,
    openapi_schema: object,
    qa_settings: QASettings,
) -> None:
    operation = openapi_schema["/health/live"]["GET"]  # type: ignore[index]
    case = data.draw(operation.as_strategy())

    response = case.call(base_url=qa_settings.api_base_url)

    case.validate_response(response)
    assert response.status_code == 200


@settings(
    max_examples=PROFILE.max_examples,
    deadline=PROFILE.deadline_ms,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(data=st.data())
def test_generated_malformed_registration_requests_never_produce_unhandled_500s(
    data: st.DataObject,
    openapi_schema: object,
    qa_settings: QASettings,
) -> None:
    operation = openapi_schema["/api/auth/register"]["POST"]  # type: ignore[index]
    case = data.draw(operation.as_strategy(generation_mode=schemathesis.GenerationMode.NEGATIVE))

    response = case.call(base_url=qa_settings.api_base_url)

    assert response.status_code < 500
    case.validate_response(response)


def test_documented_status_codes_cover_required_job_outcomes(
    api_client: ShiftBridgeClient,
) -> None:
    schema = ShiftBridgeClient.json_object(api_client.request("GET", "/openapi.json"))
    paths = schema["paths"]
    assert isinstance(paths, dict)
    jobs = paths["/api/jobs"]
    assert isinstance(jobs, dict)
    create = jobs["post"]
    assert isinstance(create, dict)
    responses = create["responses"]
    assert isinstance(responses, dict)

    assert {"201", "401", "403", "422"} <= set(responses)


def test_openapi_represents_cookie_or_bearer_authentication(
    api_client: ShiftBridgeClient,
) -> None:
    schema = ShiftBridgeClient.json_object(api_client.request("GET", "/openapi.json"))
    components = schema["components"]
    assert isinstance(components, dict)
    schemes = components["securitySchemes"]
    assert isinstance(schemes, dict)
    serialized = str(schemes).lower()

    assert "cookie" in serialized
    assert "bearer" in serialized
