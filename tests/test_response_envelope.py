from beep.api.response_envelope import unwrap_v1_envelope


def test_unwrap_v1_envelope_extracts_data():
    body = {"status": "success", "data": {"collections": [{"id": "c1"}]}}
    assert unwrap_v1_envelope(body) == {"collections": [{"id": "c1"}]}


def test_unwrap_v1_envelope_passthrough_legacy():
    body = {"success": True, "collections": []}
    assert unwrap_v1_envelope(body) == body
