"""Load the known-good fixture, optionally with one seeded defect applied.

Every seeded case is exactly one mutation away from the clean site, so a test
that fails tells you which rule moved rather than which fixture drifted.
"""

import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _read(name):
    with open(os.path.join(HERE, name), "r") as handle:
        return json.load(handle)


def known_good():
    """``(structure, localization, off_page_blocks)`` -- expected to be clean."""
    return (
        _read("known_good_site.json"),
        _read("known_good_localization.json"),
        _read("known_good_off_page_blocks.json"),
    )


def find_block(structure, block_id):
    for page in structure["pages"]:
        for block in page["blocks"]:
            if block["_id"] == block_id:
                return block
    raise KeyError(block_id)


def seeded(defect):
    """The known-good site with one defect applied."""
    structure, localization, off_page = known_good()
    structure = copy.deepcopy(structure)

    if defect == "values-as-string":
        find_block(structure, "b-faq")["values"] = '{"title": {"id": "L:faq-title"}}'
    elif defect == "federated-type-changed":
        find_block(structure, "b-fed")["values"]["internalBlockValues"]["title"] = 42
    elif defect == "missing-localization-entry":
        del localization["pages"]["p-home"]["texts"]["L:a2"]
    elif defect == "unknown-remote-block":
        find_block(structure, "b-fed")["values"]["blockId"] = "sb-not-a-real-block"
    elif defect == "dangling-site-block-id":
        structure["blocks"].append("b-deleted-long-ago")
    elif defect == "duplicate-header":
        header = copy.deepcopy(find_block(structure, "b-header"))
        header["_id"] = "b-header-2"
        structure["pages"][0]["blocks"].append(header)
        structure["blocks"].append("b-header-2")
    elif defect == "gallery-slide-missing-media":
        find_block(structure, "b-gallery")["values"]["slides"][0]["image"].pop("img")
    elif defect == "footer-social-empty-url":
        off_page = copy.deepcopy(off_page)
        off_page["b-common-layout"]["components"][0]["value"][1]["enable"] = True
    elif defect == "broken-page-action":
        find_block(structure, "b-cta")["values"]["button"]["action"]["pageId"] = "p-gone"
    elif defect == "store-section-no-group":
        find_block(structure, "b-store")["components"][0]["storeItemsGroup"] = ""
    else:
        raise ValueError(defect)

    return structure, localization, off_page
