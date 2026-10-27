"""Retain the existing read-wrapper contract tests, narrowed to the approved user scope."""

from unittest.mock import patch
from cli_anything.aidee.core import (
    recording,
    summary,
    group,
    membership,
    user,
    redemption,
)
import pytest


@pytest.mark.parametrize(
    "module,name,args,path",
    [
        (recording, "get", ["RC001"], "/recordings/RC001"),
        (
            summary,
            "get",
            ["2102281458272997376"],
            "/recordings/summaries/2102281458272997376",
        ),
        (
            summary,
            "list_by_recording",
            ["RC001"],
            "/recordings/summaries/recording/RC001",
        ),
        (group, "list_all", [], "/recording-groups/user/all"),
        (group, "tree", [], "/recording-groups/tree/all"),
        (membership, "plans", [], "/memberships/plans"),
        (membership, "order", ["o1"], "/memberships/orders/o1"),
        (user, "info", [], "/users/information"),
        (user, "membership_current", [], "/users/membership/current"),
    ],
)
def test_existing_read_wrapper_contract(module, name, args, path):
    with patch.object(module, "api_request") as request:
        getattr(module, name)("http://test", "tok", *args)
        assert request.call_args.args == ("GET", path, "http://test", "tok")


def test_personal_page_query_uses_actual_limit_contract():
    with patch.object(recording, "api_request") as request:
        recording.list_recordings("http://test", "tok", page=2, size=10)
        assert request.call_args.kwargs["params"] == {"page": 2, "limit": 10}


def test_redemption_personal_records():
    with patch.object(redemption, "api_request") as request:
        redemption.list_records("http://test", "tok", redeem_source="aideeApp")
        assert request.call_args.kwargs["params"] == {"redeemSource": "aideeApp"}


def test_path_segments_are_not_an_api_escape():
    with patch.object(recording, "api_request") as request:
        from cli_anything.aidee.errors import CLIError

        with pytest.raises(CLIError):
            recording.get("http://test", "tok", "../admin")
        request.assert_not_called()
