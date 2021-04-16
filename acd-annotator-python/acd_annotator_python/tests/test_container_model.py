# ***************************************************************** #
#                                                                   #
# (C) Copyright IBM Corp. 2021                                      #
#                                                                   #
# SPDX-License-Identifier: Apache-2.0                               #
#                                                                   #
# ***************************************************************** #

import sys
import pytest
from pydantic import ValidationError

from acd_annotator_python import container_utils


def test_validate_container_group():
    container_group_dict = {}
    container_utils.from_dict(container_group_dict)

    container_group_dict = {'unstructured': []}
    container_utils.from_dict(container_group_dict)

    container_group_dict = {'unstructured': [{'text': 'abc'}]}
    container_utils.from_dict(container_group_dict)

    container_group_dict = {'unstructured': [{'text': 'abc', 'data': {}}]}
    container_utils.from_dict(container_group_dict)

    container_group_dict = {'unstructured': [{'text': 'abc', 'data': {'concepts': []}}]}
    container_utils.from_dict(container_group_dict)

    container_group_dict = {'unstructured': [{'text': 'abc', 'data': {
        'concepts': [],
        'sections': [],
    }}]}
    container_utils.from_dict(container_group_dict)

    # unknown entries in data are ok
    container_group_dict = {'unstructured': [{'text': 'abc', 'data': {
        'concepts': [],
        'sections': [],
        'bogus': [],
    }}]}
    container_group = container_utils.from_dict(container_group_dict)
    # make sure when we serialize things back out that the unknown entries are preserved
    container_group_dict_result = container_utils.to_dict(container_group)  # (sdk validation fails)
    assert container_group_dict == container_group_dict_result, \
        "ContainerGroup.from_dict -> ContainerGroup.to_dict was lossy (dropped unstructured.data.bogus)"


def test_validate_container_group_errors():
    container_group_dict = {'bogus'}  # this is a set, not a dict
    with pytest.raises(TypeError):
        container_utils.from_dict(container_group_dict)

    # this isn't even well-formed json, but still should fail
    container_group_dict = {'unstructured'}
    with pytest.raises(TypeError):  # this is a set, not a dict
        container_utils.from_dict(container_group_dict)

    # unstructured should be list; not dict
    container_group_dict = {'unstructured': {"data": 1}}
    with pytest.raises(ValidationError):
        container_utils.from_dict(container_group_dict)

    # text must be str
    container_group_dict = {'unstructured': [{'text': 123, 'data': {}}]}
    with pytest.raises(ValidationError):
        container_utils.from_dict(container_group_dict)

    # can't have data without text
    container_group_dict = {'unstructured': [{'data': {}}]}
    with pytest.raises(ValidationError):
        container_utils.from_dict(container_group_dict)

    # (sdk validation fails)
    # data must be dict, not list. Note: this test is broken if 'data': [] because
    # pydantic automatically upcasts an empty list to an empty object for some reason.
    # not ideal, but also not the biggest deal.
    container_group_dict = {'unstructured': [{'text': 'abc', 'data': [{}]}]}
    with pytest.raises(ValidationError):
        container_utils.from_dict(container_group_dict)

    # concepts must be list; not dict
    container_group_dict = {'unstructured': [{'text': 'abc', 'data': {
        'concepts': {},
    }}]}
    with pytest.raises(ValidationError):
        container_utils.from_dict(container_group_dict)

    # concepts must have begin/end
    container_group_dict = {'unstructured': [{'text': 'abc', 'data': {
        'concepts': [{'cui': 'C001', 'type': 'plant'}],
    }}]}
    with pytest.raises(ValidationError):
        container_utils.from_dict(container_group_dict)

    # concept end must be greater than begin
    container_group_dict = {'unstructured': [{'text': 'abc', 'data': {
        'concepts': [{'begin': 0, 'end': 0, 'coveredText': 'a'}],
    }}]}
    with pytest.raises(ValidationError):
        container_utils.from_dict(container_group_dict)

    # no negative spans
    container_group_dict = {'unstructured': [{'text': 'abc', 'data': {
        'concepts': [{'begin': -3, 'end': 0, 'coveredText': 'a'}],
    }}]}
    with pytest.raises(ValidationError):
        container_utils.from_dict(container_group_dict)


UNSTRUCTURED_DATA_TYPES = ['AllergyMedicationInd', 'AllergyInd', 'attributeValues',
                           'BathingAssistanceInd', 'IcaCancerDiagnosisInd', 'concepts', 'conceptValues',
                           'DressingAssistanceInd', 'EatingAssistanceInd', 'EjectionFractionInd', 'hypotheticalSpans',
                           'LabValueInd', 'MedicationInd', 'EmailAddressInd', 'LocationInd', 'PersonInd',
                           'US_PhoneNumberInd', 'MedicalInstitutionInd', 'OrganizationInd', 'negatedSpans',
                           'ProcedureInd', 'SeeingAssistanceInd', 'SmokingInd', 'SymptomDiseaseInd',
                           'ToiletingAssistanceInd', 'WalkingAssistanceInd', 'sections', 'nluEntities', 'relations',
                           'spellingCorrections', 'spellCorrectedText', 'temporalSpans']


def build_annotation(extra_fields=None):
    """return a valid annotation. All annotations minimally require begin/end/coveredText,
    plus whatever information is passed in extra_fields
    """
    if extra_fields is None:
        extra_fields = {}
    ann = {'begin': 0, 'end': 1}  # coveredText isn't actually required
    ann.update(extra_fields)
    return ann


def test_validate_unstructured_data():
    # tests for data.concepts, data.sections, etc.
    for data_type in UNSTRUCTURED_DATA_TYPES:
        valid_anns = []
        # negatedSpans requirements
        if data_type == 'negatedSpans':
            valid_anns.append(build_annotation({
                'trigger': build_annotation()
            }))
        # sections requirements
        elif data_type == 'sections':
            valid_anns.append(build_annotation({
                'type': 'plant'
            }))
        # nluEntities requirements
        elif data_type == 'nluEntities':
            valid_anns.append(build_annotation({
                'type': 'plant',
                'source': 'annotator2',
                'relevance': 0.3,
            }))
            valid_anns.append(build_annotation({
                'type': 'plant',
                'source': 'annotator2',
                'relevance': 0,  # (sdk validation fails)
            }))
        # relations requirements
        elif data_type == 'relations':
            valid_anns.append(build_annotation({
                'type': 'plant',
                'source': 'annotator2',
                'score': 0.3,
                'nodes': [],
            }))
            valid_anns.append(build_annotation({
                'type': 'plant',
                'source': 'annotator2',
                'score': 0,  # (sdk validation fails)
                'nodes': [],
            }))
        # spellCorrectedText requirements
        elif data_type == 'spellCorrectedText':
            valid_anns.append(build_annotation({
                'correctedText': 'cba',
            }))
        # temporalSpans requirements
        elif data_type == 'temporalSpans':
            valid_anns.append(build_annotation({
                'temporalType': {'overlapsScore': 0.8},
            }))
        else:
            valid_anns = [build_annotation()]

        # make sure all the valid annotations pass validation
        for valid_ann in valid_anns:
            container_group_dict = {'unstructured': [{'text': 'abc', 'data': {
                data_type: [valid_ann],
            }}]}
            print('testing valid annotation:', valid_ann)  # this only gets shown when test fails
            container_utils.from_dict(container_group_dict)

        # make sure that if we add an extra, unknown field to a valid entity, that it
        # 1. passes validation   and 2. preserves the information and returns it again
        # if data_type == 'spellCorrectedText':
        #     continue  # (sdk validation fails)
        for valid_ann in valid_anns:
            valid_ann['bogus'] = {'a': {'aa': 1}, 'b': [1, 2, 3], 'c': 4}
            container_group_dict = {'unstructured': [{'text': 'abc', 'data': {
                data_type: [valid_ann],
            }}]}
            container_group = container_utils.from_dict(container_group_dict)
            # make sure when we serialize things back out that the unknown entries are preserved
            container_group_dict_result = container_utils.to_dict(container_group)
            error_msg = f'Concept.from_dict -> Concept.to_dict was lossy ' \
                        f'(dropped unstructured.data.bogus) for entity "{data_type}"'
            assert container_group_dict == container_group_dict_result, error_msg


def test_validate_unstructured_data_errors():
    # invalid begin/end/type tests for data.concepts, data.sections, etc.
    # bad/incomplete annotations should fail anywhere they are put
    for data_type in UNSTRUCTURED_DATA_TYPES:
        # spellCorrectedText doesn't use begin/end, so these tests don't apply
        if data_type == 'spellCorrectedText':
            continue
        # # (sdk validation fails)
        # if data_type == 'spellingCorrections':
        #     continue
        invalid_anns = [
            {'end': 1, 'coveredText': 'a'},  # no begin
            {'begin': 0, 'coveredText': 'a'},  # no end
            {'begin': 0, 'end': 0, 'coveredText': 'a'},  # begin==end.  (sdk validation fails)
            {'begin': 0, 'end': 1, 'coveredText': 'abc'},  # span length problem.  (sdk validation fails)
            {'begin': -3, 'end': 0, 'coveredText': 'a'},  # negatives  (sdk validation fails)
            {'begin': 'a', 'end': 1, 'coveredText': 'a'},  # bad begin value  (sdk validation fails)
            {'begin': 0, 'end': 'a', 'coveredText': 'a'},  # bad end value  (sdk validation fails)
            {'begin': 0, 'end': 1, 'coveredText': []},  # bad coveredText value  (sdk validation fails)
            {'begin': 0, 'end': 1, 'coveredText': 'a', 'type': []},  # bad optional type value  (sdk validation fails)
            {'begin': 0, 'end': 1, 'coveredText': 'a', 'type': 2},  # bad optional type value  (sdk validation fails)
            {'begin': 0, 'end': 1, 'coveredText': 'a', 'id': 2},  # id should be string
            {'begin': 0, 'end': 1, 'coveredText': 'a', 'uid': '2'},  # uid should be int
            {'begin': 0, 'end': 1, 'coveredText': 'a', 'mergeid': '2'},  # mergeid should be int
        ]

        # make sure all the invalid annotations fail validation
        for invalid_ann in invalid_anns:
            container_group_dict = {'unstructured': [{'text': 'abc', 'data': {
                data_type: [invalid_ann],
            }}]}
            # print('testing invalid annotation:', invalid_ann)  # this only gets shown when test fails
            with pytest.raises(ValidationError):
                container_utils.from_dict(container_group_dict)
                # pytest doesn't print WHICH input failed to produce an error, so we need
                # to do it ourselves to make it a little easier to track down what went (failed to go) wrong.
                print('DID NOT RAISE Exception for invalid annotation: {} in "{}"'.format(invalid_ann, data_type),
                      file=sys.stderr)

    # Targeted negative tests for data.concepts, data.sections, etc.
    for data_type in UNSTRUCTURED_DATA_TYPES:
        invalid_anns = []
        # nluEntities requirements
        if data_type == 'nluEntities':
            invalid_anns.append(build_annotation({
                'type': 'plant',
                'source': 'annotator2',
                'relevance': '-1.3a',  # invalid value
            }))
        # relations requirements
        elif data_type == 'relations':
            invalid_anns.append(build_annotation({
                'type': 'plant',
                'source': 'annotator2',
                'score': [],  # invalid value
                'nodes': [],
            }))
        # negatedSpans requirements
        elif data_type == 'negatedSpans':
            invalid_anns.append(build_annotation({'trigger': "abc"}))  # (sdk validation fails)
        # sections requirements
        elif data_type == 'sections':
            invalid_anns.append(build_annotation({'type': 1}))  # (sdk validation fails)
        # spellCorrectedText requirements
        elif data_type == 'spellCorrectedText':
            invalid_anns.append(build_annotation({'correctedText': 1}))  # bad type (sdk validation fails)
            invalid_anns.append(build_annotation({'correctedText': []}))  # bad type
            invalid_anns.append(build_annotation({'correctedText': {}}))  # bad type
        # temporalSpans requirements
        elif data_type == 'temporalSpans':
            invalid_anns.append(build_annotation({'temporalType': 3}))  # bad type (sdk validation fails)
            invalid_anns.append(build_annotation({'temporalType': 'date'}))  # bad type
            invalid_anns.append(build_annotation({'temporalType': [{}]}))  # bad type  (sdk validation fails)
            # invalid_anns.append(build_annotation({'temporalType': []}))  # bad type  TODO pydantic coerces this

        # make sure all the invalid annotations fail validation
        for invalid_ann in invalid_anns:
            container_group_dict = {'unstructured': [{'text': 'abc', 'data': {
                data_type: [invalid_ann],
            }}]}
            with pytest.raises(ValidationError):
                container_utils.from_dict(container_group_dict)
                # pytest doesn't print WHICH input failed to produce an error, so we need
                # to do it ourselves to make it a little easier to track down what went (failed to go) wrong.
                print('DID NOT RAISE Exception for invalid annotation: {} in "{}"'.format(invalid_ann, data_type),
                      file=sys.stderr)


# this one is a bit spooky. technically it's ok because coveredText isn't required
# and covered_text is a new field. But maybe in future we want to disallow alternative
# cases for fields that would be easy mistakes to make.
# def test_concept1():
#     """test for Concept"""
#     with pytest.raises(ValidationError):
#         # should be coveredText
#         container_utils.acd_datamodel.Concept(begin=1, end=2, covered_text='abcd')  # (sdk validation fails)


def test_section1():
    """test for Section"""
    # does not need coveredText
    container_utils.acd_datamodel.Section(begin=1, end=2)


def test_edit_concepts():
    """
    We need validation to happen at runtime each time the container model is edited,
    not just when parsing json. We've set that option in our BaseModelACD, testing here.
    """
    example_container = {
        "unstructured": [
            {
                "text": "The patient reports severe bowel discomfort for the last week.",
                "data": {
                    "concepts": [
                        {
                            "cui": "C1096594",
                            "preferredName": "bowel discomfort",
                            "semanticType": "sosy",
                            "source": "umls",
                            "sourceVersion": "2020AA",
                            "type": "umls.SignOrSymptom",
                            "begin": 27,
                            "end": 43,
                            "coveredText": "bowel discomfort",
                            "vocabs": "CHV"
                        }
                    ]
                }
            }
        ]
    }
    # load in a valid base container, and then make sure a number of invalid edits all break
    container_group = container_utils.acd_datamodel.ContainerGroup(**example_container)
    concept = container_group.unstructured[0].data.concepts[0]
    with pytest.raises(ValidationError):
        concept.begin = "b"
    with pytest.raises(ValidationError):
        concept.begin = "3"  # StrictInt doesn't allow string coercion
    with pytest.raises(ValidationError):
        concept.begin = -3
    with pytest.raises(ValidationError):
        concept.begin = 0  # end-begin vs len(coveredText) mismatch
    with pytest.raises(ValidationError):
        concept.begin = 43  # end must be strictly greater than beginning
    del concept.coveredText  # coveredText is optional
    concept.begin = 0  # there's no longer a length mismatch since no coveredText to compare with
    with pytest.raises(ValidationError):
        concept.coveredText = "a"  # length mismatch
    with pytest.raises(ValidationError):
        concept.cui = 1  # should be string


def test_edit_unstructured_container():
    """
    We need validation to happen at runtime each time the container model is edited,
    not just when parsing json. We've set that option in our BaseModelACD, testing here.
    """
    example_container = {
        "unstructured": [
            {
                "text": "The patient reports severe bowel discomfort for the last week.",
                "data": {
                    "concepts": []
                }
            }
        ]
    }
    # load in a valid base container, and then make sure a number of invalid edits all break
    container_group = container_utils.acd_datamodel.ContainerGroup(**example_container)

    with pytest.raises(ValidationError):
        container_group.unstructured[0].text = {}  # bad type
    with pytest.raises(ValidationError):
        container_group.unstructured[0].text = None  # required
    # with pytest.raises(ValidationError):
    #     del container_group.unstructured[0].text  # required  TODO fails to throw an error
    with pytest.raises(ValidationError):
        container_utils.acd_datamodel.UnstructuredContainer()  # can't create one of these wout text
    container_utils.acd_datamodel.UnstructuredContainer(text='a')
    # with pytest.raises(ValidationError):
    #     container_utils.acd_datamodel.UnstructuredContainer(text='a', data='')  # TODO empty string is coerced
    with pytest.raises(ValidationError):
        container_utils.acd_datamodel.UnstructuredContainer(text='a', data='a')

    with pytest.raises(ValidationError):
        container_group.unstructured[0].data = [{}]  # bad type
    container_group.unstructured[0].data = None  # not required
    del container_group.unstructured[0].data  # not required


def test_edit_structured_container():
    """
    structured containers are still a work in process. Very preliminary sanity test
    """
    example_container = {
        "structured": [
            {
                "data": {
                    "concepts": [],
                    "bogus": {"a": 1}
                }
            }
        ]
    }
    # load in a valid base container, and then make sure a number of invalid edits all break
    container_utils.acd_datamodel.ContainerGroup(**example_container)


# # enable to debug
# if __name__ == '__main__':
#     test_edit_unstructured_container()
