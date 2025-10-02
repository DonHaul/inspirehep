from hooks.inspirehep.inspire_http_hook import InspireHttpHook
from inspire_utils.dedupers import dedupe_list
from inspire_utils.record import get_value
from invenio_classifier.reader import KeywordToken


def get_decision(decisions, action):
    for decision in decisions:
        if decision["action"] == action:
            return decision
    return None


def normalize_collaborations(workflow_data):
    inspire_http_hook = InspireHttpHook()

    collaborations = get_value(workflow_data, "collaborations", [])

    if not collaborations:
        return

    response = inspire_http_hook.call_api(
        endpoint="api/curation/literature/collaborations-normalization",
        method="GET",
        json={"collaborations": collaborations},
    )
    response.raise_for_status()
    obj_accelerator_experiments = workflow_data.get("accelerator_experiments", [])
    json_response = response.json()

    normalized_accelerator_experiments = json_response["accelerator_experiments"]

    if normalized_accelerator_experiments or obj_accelerator_experiments:
        accelerator_experiments = dedupe_list(
            obj_accelerator_experiments + normalized_accelerator_experiments
        )
        normalized_collaborations = json_response["normalized_collaborations"]

        return accelerator_experiments, normalized_collaborations


def clean_instances_from_data(output):
    """Check if specific keys are of KeywordToken and replace them with their id."""
    new_output = {}
    for output_key in output:
        keywords = output[output_key]
        for key in keywords:
            if isinstance(key, KeywordToken):
                keywords[key.id] = keywords.pop(key)
        new_output[output_key] = keywords
    return new_output
